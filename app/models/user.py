import re
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

from models.enum import UserRole

if TYPE_CHECKING:
    from models.wallet import Wallet
    from models.transaction import Transaction
    from models.assessment import AssessmentTask

class User(SQLModel, table=True):
    """
    Пользователь ML сервиса.

    Attributes:
        id (int): Primary key
        email (str): email пользователя (unique)
        password (str): пароль (упрощенно для задания)
        role (Enum): USER / ADMIN
        created_at (datetime): дата создания аккаунта (UTC)
        wallet (Optional[Wallet]): кошелек (только для USER)
        transactions (List[Transaction]): транзакции пользователя
        tasks (List[AssessmentTask]): история задач пользователя
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(
        ...,
        unique=True,
        index=True,
        min_length=5,
        max_length=255,
    )
    password: str = Field(..., min_length=8, max_length=255)
    role: UserRole = Field(default=UserRole.USER, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # --- Relationships ---
    wallet: Optional["Wallet"] = Relationship(  # type: ignore
    back_populates="user",
    sa_relationship_kwargs={
        "uselist": False,      # 1:1
        "lazy": "selectin",
    },
    )

    transactions: List["Transaction"] = Relationship(  # type: ignore
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )

    tasks: List["AssessmentTask"] = Relationship(  # type: ignore
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )

    def __str__(self) -> str:
        return f"Id: {self.id}. Email: {self.email}. Role: {self.role.value}" 

    def validate_email(self) -> bool:
        """
        Validate email format.

        Returns:
            bool: True if email is valid

        Raises:
            ValueError: If email format is invalid
        """
        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not pattern.match(self.email):
            raise ValueError("Некорректный email")
        return True


    def validate_wallet_consistency(self) -> bool:
        """
        Validate that wallet (if present) belongs to this user.

        Raises:
            ValueError: If wallet.user_id != user.id
        """
        if self.wallet is not None and self.id is not None and self.wallet.user_id != self.id:
            raise ValueError("wallet.user_id должен совпадать с user.id")
        return True

    class Config:
        """Model configuration (как в лекции)"""
        validate_assignment = True
        arbitrary_types_allowed = True
