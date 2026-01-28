from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from models.assessment import AssessmentTask
from models.user import User
from models.ml_model import MLModel


def get_task_by_id(task_id: int, session: Session) -> Optional[AssessmentTask]:
    """
    Get task by ID (with user).
    """
    try:
        statement = (
            select(AssessmentTask)
            .where(AssessmentTask.id == task_id)
            .options(selectinload(AssessmentTask.user))
        )
        task = session.exec(statement).first()
        return task
    except Exception:
        raise


def get_user_tasks(user_id: int, session: Session) -> List[AssessmentTask]:
    """
    Get tasks for a user.
    """
    try:
        statement = (
            select(AssessmentTask)
            .where(AssessmentTask.user_id == user_id)
            .options(selectinload(AssessmentTask.user))
            .order_by(AssessmentTask.created_at.desc())
        )
        tasks = session.exec(statement).all()
        return tasks
    except Exception:
        raise


def create_task(task: AssessmentTask, session: Session) -> AssessmentTask:
    """
    Create new task.
    """
    try:
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    except Exception:
        session.rollback()
        raise


def update_task(task: AssessmentTask, session: Session) -> AssessmentTask:
    """
    Update task.
    """
    try:
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    except Exception:
        session.rollback()
        raise


def delete_task(task_id: int, session: Session) -> bool:
    """
    Delete task by ID (обычно не нужно, но как в лекции CRUD).
    """
    try:
        task = session.get(AssessmentTask, task_id)
        if task:
            session.delete(task)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        raise
