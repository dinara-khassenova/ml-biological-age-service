from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database.database import get_session
from services.billing import BillingService
from services.task import TaskService
from services.crud.task import get_user_tasks
from models.assessment import AssessmentTask

from schemas.task import PredictIn, TaskOut, TaskHistoryOut, TaskDraftIn

router = APIRouter()


@router.post("", response_model=TaskOut)
def create_task(payload: TaskDraftIn, session: Session = Depends(get_session)) -> TaskOut:
    '''
    Создание черновика задачи
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    task = AssessmentTask(user_id=payload.user_id, model_id=payload.model_id, answers=payload.answers)
    task = service.create_draft(task)
    return TaskOut.model_validate(task)


@router.post("/{task_id}/run", response_model=TaskOut)
def run_task(task_id: int, session: Session = Depends(get_session)) -> TaskOut:
    '''
    Запуск существующей задачи
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    try:
        task = service.run_task_by_id(task_id)
        return TaskOut.model_validate(task)
    except ValueError as ex:
        msg = str(ex)
        if "не найдена" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post("/predict", response_model=TaskOut)
def predict(payload: PredictIn, session: Session = Depends(get_session)) -> TaskOut:
    '''
    Predict как shortcut "create + run", нужен для быстрого использования API, 
    а draft-задачи (create task) — для более гибкого и расширяемого сценария 
    редактирование, повторный запуск и т.д)
    '''
    billing = BillingService(session)
    service = TaskService(session, billing)

    task = AssessmentTask(user_id=payload.user_id, model_id=payload.model_id, answers=payload.answers)
    task = service.run_task(task)
    return TaskOut.model_validate(task)


@router.get("/history", response_model=list[TaskHistoryOut])
def history(user_id: int, session: Session = Depends(get_session)) -> list[TaskHistoryOut]:
    tasks = get_user_tasks(user_id, session)
    return [TaskHistoryOut.model_validate(t) for t in tasks if t.id is not None]




