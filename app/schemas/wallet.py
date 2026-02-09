from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from models.enum import TransactionType

class BalanceOut(BaseModel):
    balance: int


class TopUpIn(BaseModel):
    amount: int = Field(gt=0)


class TopUpOut(BaseModel):
    transaction_id: int
    amount: int
    tx_type: TransactionType

class TransactionOut(BaseModel):
    id: int
    created_at: datetime
    amount: int
    tx_type: TransactionType

class TransactionHistoryOut(BaseModel):
    items: list[TransactionOut]

