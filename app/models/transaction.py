from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constants import TX_TYPES

@dataclass(frozen=True)
class Transaction:
    """
    Транзакция - запись истории операций по балансу.

    Attributes:
        id (int): идентификатор транзакции
        user_id (int): идентификатор пользователя
        tx_type (str): тип операции (TOPUP / CHARGE)
        amount (int): сумма в кредитах
        task_id (Optional[int]): ссылка на задачу (для CHARGE)
        created_at (datetime): дата/время транзакции (UTC)
    """
    id: int
    user_id: int
    tx_type: str
    amount: int
    task_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.tx_type not in TX_TYPES:
            raise ValueError(f"Некорректный тип транзакции: {self.tx_type}")
        if self.amount <= 0:
            raise ValueError("Сумма транзакции должна быть > 0")
