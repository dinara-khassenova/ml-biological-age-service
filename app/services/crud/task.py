from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from models.assessment import AssessmentTask


def get_task_by_id(task_id: int, session: Session) -> Optional[AssessmentTask]:
    """
    Get task by ID (with user).
    """
    statement = (
        select(AssessmentTask)
        .where(AssessmentTask.id == task_id)
        .options(selectinload(AssessmentTask.user))
    )
    return session.exec(statement).first()


def get_task_by_external_id(external_id: str, session: Session) -> Optional[AssessmentTask]:
    statement = (
        select(AssessmentTask)
        .where(AssessmentTask.external_id == external_id)
        .options(selectinload(AssessmentTask.user))
    )
    return session.exec(statement).first()


def get_user_tasks(user_id: int, session: Session) -> List[AssessmentTask]:
    """
    Get tasks for a user.
    """
    statement = (
        select(AssessmentTask)
        .where(AssessmentTask.user_id == user_id)
        .order_by(AssessmentTask.created_at.desc())
        .options(selectinload(AssessmentTask.user))
    )
    return session.exec(statement).all()


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
    Delete task by ID.
    """
    try:
        task = session.get(AssessmentTask, task_id)
        if task is None:
            return False
        session.delete(task)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
