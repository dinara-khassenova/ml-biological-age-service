from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.database import get_session
from models.assessment import AssessmentTask
from models.enum import TaskStatus, UserRole
from models.user import User
from mq.publisher import publish_to_queue
from routes.deps import get_current_user
from schemas.task import PredictIn, PredictOut, TaskOut, TaskHistoryOut, TaskDraftIn
from services.billing import BillingService
from services.crud import ml_model as ml_model_crud
from services.crud import task as task_crud
from services.task import TaskService
from ml.runtime_model import RuntimeMLModel

router = APIRouter()


def _errors_to_dict(errors_obj: List[Any]) -> List[dict]:
    errors: List[dict] = []
    for e in errors_obj or []:
        errors.append(
            {
                "field_name": getattr(e, "field_name", "unknown"),
                "message": getattr(e, "message", str(e)),
            }
        )
    return errors


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskDraftIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Task draft.
    User_id is NOT accepted from client; taken from JWT.
    """
    billing = BillingService(session)
    service = TaskService(session, billing)

    task = AssessmentTask(
        user_id=current_user.id,
        model_id=payload.model_id,
        answers=payload.answers,
    )
    task = service.create_draft(task)  # external_id генерится внутри create_draft
    return TaskOut.model_validate(task)


@router.get("/history", response_model=list[TaskHistoryOut])
def history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[TaskHistoryOut]:
    tasks = task_crud.get_user_tasks(current_user.id, session)
    return [TaskHistoryOut.model_validate(t) for t in tasks if t.id is not None]


@router.post("/predict", response_model=PredictOut, status_code=status.HTTP_202_ACCEPTED)
def predict(
    payload: PredictIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PredictOut:
    """
    Логика по ТЗ:
    - создаём draft в БД (чтобы вернуть task_id даже при ошибке)
    - делаем быструю валидацию: если ошибки -> 422 и НЕ отправляем в очередь
    - если ок -> ставим VALIDATED, публикуем в RabbitMQ, возвращаем только task_id
    """
    billing = BillingService(session)
    service = TaskService(session, billing)

    # 1) создать задачу в БД (draft)
    task = AssessmentTask(
        user_id=current_user.id,
        model_id=payload.model_id,
        answers=payload.answers,
    )
    task = service.create_draft(task)

    # 2) быстрая валидация (единая логика: RuntimeMLModel)
    meta = ml_model_crud.get_model_by_id(task.model_id, session)
    if meta is None:
        task.set_error("ML модель не найдена")
        task = task_crud.update_task(task, session)
        raise HTTPException(status_code=404, detail="ML модель не найдена")

    runtime = RuntimeMLModel(meta=meta)
    ok, errors_obj = runtime.validate(task.answers or {})
    errors = _errors_to_dict(errors_obj)

    if errors:
        # оставляем CREATED, чтобы пользователь мог исправить
        task.validation_errors = errors
        task.status = TaskStatus.CREATED  # FIX: явно фиксируем желаемый статус
        task = task_crud.update_task(task, session)
        raise HTTPException(
            status_code=422,
            detail={"task_id": task.external_id, "validation_errors": errors},
        )

    # 3) помечаем VALIDATED и отправляем в очередь
    task.validation_errors = []
    task.status = TaskStatus.VALIDATED
    task = task_crud.update_task(task, session)

    message: Dict[str, Any] = {
        "task_id": task.external_id,
        "features": task.answers or {},
        "model": meta.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    publish_to_queue(message)

    # 4) вернуть только task_id (uuid)
    return PredictOut(task_id=task.external_id)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Get task by external_id (uuid) + owner-check (or admin).
    """
    task = task_crud.get_task_by_external_id(task_id, session)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужой задаче")

    return TaskOut.model_validate(task)


@router.post("/{task_id}/run", response_model=TaskOut)
def run_task(
    task_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Поведение:
    - проверяем доступ
    - если DONE/FAILED -> просто возвращаем
    - валидируем -> если ошибки: оставляем CREATED и возвращаем 422
    - если ок -> VALIDATED + publish в RabbitMQ
    """
    task = task_crud.get_task_by_external_id(task_id, session)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужой задаче")

    if task.status in {TaskStatus.DONE, TaskStatus.FAILED}:
        return TaskOut.model_validate(task)

    meta = ml_model_crud.get_model_by_id(task.model_id, session)
    if meta is None:
        task.set_error("ML модель не найдена")
        task = task_crud.update_task(task, session)
        raise HTTPException(status_code=404, detail="ML модель не найдена")

    runtime = RuntimeMLModel(meta=meta)
    ok, errors_obj = runtime.validate(task.answers or {})
    errors = _errors_to_dict(errors_obj)

    if errors:
        # оставляем CREATED, чтобы пользователь мог исправить
        task.validation_errors = errors
        task.status = TaskStatus.CREATED  # FIX: явно фиксируем желаемый статус
        task = task_crud.update_task(task, session)
        raise HTTPException(
            status_code=422,
            detail={"task_id": task.external_id, "validation_errors": errors},
        )

    task.validation_errors = []
    task.status = TaskStatus.VALIDATED
    task = task_crud.update_task(task, session)

    message: Dict[str, Any] = {
        "task_id": task.external_id,
        "features": task.answers or {},
        "model": meta.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    publish_to_queue(message)

    return TaskOut.model_validate(task)
