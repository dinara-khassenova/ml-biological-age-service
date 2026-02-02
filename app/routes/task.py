from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database.database import get_session
from services.billing import BillingService
from services.task import TaskService
from models.assessment import AssessmentTask
from models.enum import UserRole
from models.user import User
from routes.deps import get_current_user
from services.crud import task as task_crud

from schemas.task import PredictIn, TaskOut, TaskHistoryOut, TaskDraftIn

router = APIRouter()


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskDraftIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    '''
    Task draft.
    User_id is NOT accepted from client; taken from JWT.
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    task = AssessmentTask(user_id=current_user.id, model_id=payload.model_id, answers=payload.answers)
    task = service.create_draft(task)
    return TaskOut.model_validate(task)


@router.get("/history", response_model=list[TaskHistoryOut])
def history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[TaskHistoryOut]:
    
    tasks = task_crud.get_user_tasks(current_user.id, session)
    return [TaskHistoryOut.model_validate(t) for t in tasks if t.id is not None]


@router.post("/predict", response_model=TaskOut)
def predict(
    payload: PredictIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    '''
    Predict как shortcut "create + run", нужен для быстрого использования API, 
    а draft-задачи (create task) — для более гибкого и расширяемого сценария 
    редактирование, повторный запуск и т.д)
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    task = AssessmentTask(user_id=current_user.id, model_id=payload.model_id, answers=payload.answers)
    task = service.run_task(task)
    return TaskOut.model_validate(task)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Missing endpoint - get task by id
    + owner-check (or admin).
    """
    task = task_crud.get_task_by_id(task_id, session)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужой задаче")

    return TaskOut.model_validate(task)


@router.post("/{task_id}/run", response_model=TaskOut)
def run_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    '''
    Запуск существующей задачи
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    try:
        task = service.run_task_by_id(
            task_id=task_id,
            current_user_id=current_user.id,
            is_admin=(current_user.role == UserRole.ADMIN),
        )
        return TaskOut.model_validate(task)
    
    except PermissionError as ex:
        raise HTTPException(status_code=403, detail=str(ex))
    
    except ValueError as ex:
        msg = str(ex)
        if "не найдена" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)










