from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from constants import TX_TYPES

if TYPE_CHECKING:
    from models.user import User
    from models.assessment import AssessmentTask


class Transaction(SQLModel, table=True):
    """
    Транзакция — запись истории операций по балансу.

    Attributes:
        id (int): Primary key
        user_id (int): идентификатор пользователя (FK → users.id)
        tx_type (str): тип операции (TOPUP / CHARGE)
        amount (int): сумма в кредитах (> 0)
        task_id (Optional[int]): ссылка на задачу (для CHARGE)
        created_at (datetime): дата/время транзакции (UTC)
        user (Optional[User]): пользователь — владелец транзакции
    """

    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    tx_type: str = Field(index=True, max_length=16)
    amount: int = Field(gt=0)
    task_id: Optional[int] = Field(default=None, foreign_key="assessment_tasks.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships 
    user: "User" = Relationship(  # type: ignore
    back_populates="transactions",
    sa_relationship_kwargs={"lazy": "selectin"},
)

    task: Optional["AssessmentTask"] = Relationship(  # type: ignore
    sa_relationship_kwargs={"lazy": "selectin"},
)

    def __str__(self) -> str:
        return f"Tx(id={self.id}, user_id={self.user_id}, type={self.tx_type}, amount={self.amount}, task_id={self.task_id})"

    def validate_tx_type(self) -> bool:
        """
        Validate transaction type.

        Raises:
            ValueError: if tx_type is invalid
        """
        if self.tx_type not in TX_TYPES:
            raise ValueError(f"Некорректный тип транзакции: {self.tx_type}")
        return True

    @property
    def is_charge(self) -> bool:
        return self.tx_type == "CHARGE"

    @property
    def signed_amount(self) -> int:
        return -self.amount if self.tx_type == "CHARGE" else self.amount

    class Config:
        """Model configuration"""
        validate_assignment = True
        arbitrary_types_allowed = True



'''
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
'''
