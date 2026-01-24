from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.user import User

class Wallet(SQLModel, table=True):
    """
    Кошелёк пользователя (баланс в кредитах).

    Attributes:
        user_id (int): идентификатор пользователя (PK, FK → users.id)
        balance (int): текущий баланс
        user (Optional[User]): владелец кошелька (1:1)
    """

    __tablename__ = "wallets"
    
    user_id: int = Field(primary_key=True, foreign_key="users.id")
    balance: int = Field(default=0, ge=0)

    # Relationship 
    user: "User" = Relationship(  # type: ignore
    back_populates="wallet",
    sa_relationship_kwargs={"lazy": "selectin"},
)

    def __str__(self) -> str:
        return f"Wallet(user_id={self.user_id}, balance={self.balance})"
    
    
    def validate_balance(self) -> bool:
        """
        Validate that balance is non-negative.

        Raises:
            ValueError: if balance < 0
        """
        if self.balance < 0:
            raise ValueError("Баланс не может быть отрицательным")
        return True

    def can_pay(self, amount: int) -> bool:
        """
        Check if wallet has enough balance.

        Raises:
            ValueError: if amount < 0
        """
        if amount < 0:
            raise ValueError("Сумма не может быть отрицательной")
        return self.balance >= amount

    class Config:
        """Model configuration """
        validate_assignment = True
        arbitrary_types_allowed = True


'''
@dataclass
class Wallet:
    """
    Кошелек пользователя (баланс в кредитах).

    Attributes:
        user_id (int): идентификатор пользователя
        balance (int): текущий баланс
    """
    user_id: int
    balance: int = 0

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("Баланс не может быть отрицательным")

    def topup(self, amount: int) -> None:
        """Пополнение баланса на amount кредитов."""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть > 0")
        self.balance += amount

    def can_pay(self, amount: int) -> bool:
        """Проверка достаточности средств."""
        if amount < 0:
            raise ValueError("Цена не может быть отрицательной")
        return self.balance >= amount

    def charge(self, amount: int) -> None:
        """
        Списание средств.

        Требование по ТЗ:
        списание должно происходить только после успешного выполнения запроса.
        Это правило реализуется на уровне сервиса,
        а Wallet отвечает только за корректное списание.
        """
        if amount <= 0:
            raise ValueError("Сумма списания должна быть > 0")
        if not self.can_pay(amount):
            raise ValueError("Недостаточно средств")
        self.balance -= amount
'''