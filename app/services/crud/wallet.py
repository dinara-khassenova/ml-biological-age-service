from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from models.wallet import Wallet


def get_wallet_by_user_id(user_id: int, session: Session) -> Optional[Wallet]:
    
    return session.get(Wallet, user_id)


def create_wallet(wallet: Wallet, session: Session) -> Wallet:
    """
    Create wallet.
    """
    try:
        session.add(wallet)
        session.commit()
        session.refresh(wallet)
        return wallet
    except Exception:
        session.rollback()
        raise


def update_wallet(wallet: Wallet, session: Session) -> Wallet:
    """
    Update wallet (balance change etc.).
    """
    try:
        session.add(wallet)
        session.commit()
        session.refresh(wallet)
        return wallet
    except Exception:
        session.rollback()
        raise
