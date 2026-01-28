from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.assessment import AssessmentTask


def get_all_users(session: Session) -> List[User]:
    """
    Retrieve all users with their wallet, transactions and tasks.
    """
    try:
        statement = (
            select(User)
            .options(
                selectinload(User.wallet),
                selectinload(User.transactions),
                selectinload(User.tasks),
            )
        )
        users = session.exec(statement).all()
        return users
    except Exception:
        raise


def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """
    Get user by ID (with wallet/transactions/tasks).
    """
    try:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.wallet),
                selectinload(User.transactions),
                selectinload(User.tasks),
            )
        )
        user = session.exec(statement).first()
        return user
    except Exception:
        raise


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    """
    Get user by email (with wallet/transactions/tasks).
    """
    try:
        statement = (
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.wallet),
                selectinload(User.transactions),
                selectinload(User.tasks),
            )
        )
        user = session.exec(statement).first()
        return user
    except Exception:
        raise


def create_user(user: User, session: Session) -> User:
    """
    Create new user.
    """
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except Exception:
        session.rollback()
        raise


def delete_user(user_id: int, session: Session) -> bool:
    """
    Delete user by ID.
    """
    try:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        raise
