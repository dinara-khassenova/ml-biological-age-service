from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database.database import get_session
from services.billing import BillingService
from schemas.wallet import BalanceOut, TopUpIn, TopUpOut

router = APIRouter()


@router.get("/balance", response_model=BalanceOut)
def get_balance(user_id: int, session: Session = Depends(get_session)) -> BalanceOut:
    billing = BillingService(session)
    try:
        balance = billing.balance(user_id)
        return BalanceOut(balance=balance)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/topup", response_model=TopUpOut)
def topup(user_id: int, payload: TopUpIn, session: Session = Depends(get_session)) -> TopUpOut:
    billing = BillingService(session)
    try:
        tx = billing.topup(user_id, payload.amount)
        if tx.id is None:
            raise RuntimeError("Transaction.id is None")
        return TopUpOut(transaction_id=tx.id, amount=tx.amount, tx_type=tx.tx_type)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))
