from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from models.transaction import Transaction


def get_transaction_by_id(tx_id: int, session: Session) -> Optional[Transaction]:
    """
    Get transaction by ID with related user and task.
    """
    try:
        statement = (
            select(Transaction)
            .where(Transaction.id == tx_id)
            .options(
                selectinload(Transaction.user),
                selectinload(Transaction.task),
            )
        )
        tx = session.exec(statement).first()
        return tx
    except Exception:
        raise


def get_user_transactions(user_id: int, session: Session) -> List[Transaction]:
    """
    Get all transactions for a specific user.
    """
    try:
        statement = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(
                selectinload(Transaction.user),
                selectinload(Transaction.task),
            )
            .order_by(Transaction.created_at.desc())
        )
        transactions = session.exec(statement).all()
        return transactions
    except Exception:
        raise


def get_all_transactions(session: Session) -> List[Transaction]:
    """
    Get all transactions in the system.
    """
    try:
        statement = (
            select(Transaction)
            .options(
                selectinload(Transaction.user),
                selectinload(Transaction.task),
            )
            .order_by(Transaction.created_at.desc())
        )
        transactions = session.exec(statement).all()
        return transactions
    except Exception:
        raise


def create_transaction(tx: Transaction, session: Session) -> Transaction:
    """
    Create new transaction.
    """
    try:
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return tx
    except Exception:
        session.rollback()
        raise


def delete_transaction(tx_id: int, session: Session) -> bool:
    """
    Delete transaction by ID.
    Usually not used in business logic.
    """
    try:
        tx = session.get(Transaction, tx_id)
        if not tx:
            return False

        session.delete(tx)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise