from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database.database import get_session
from services.billing import BillingService
from schemas.wallet import BalanceOut, TopUpIn, TopUpOut
from routes.deps import get_current_user
from models.user import User

router = APIRouter()


@router.get("/balance", response_model=BalanceOut)
def get_balance(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BalanceOut:
    """
    No user_id param; user is identified by Bearer JWT.
    """
    billing = BillingService(session)
    try:
        balance = billing.balance(current_user.id)
        return BalanceOut(balance=balance)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/topup", response_model=TopUpOut)
def topup(
    payload: TopUpIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TopUpOut:
    """
    No user_id param; user is identified by Bearer JWT.
    """
    billing = BillingService(session)
    try:
        tx = billing.topup(current_user.id, payload.amount)
        if tx.id is None:
            raise RuntimeError("Transaction.id is None")
        return TopUpOut(transaction_id=tx.id, amount=tx.amount, tx_type=tx.tx_type)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))
