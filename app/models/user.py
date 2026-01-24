from dataclasses import dataclass
from typing import Optional

from constants import USER_ROLES
from models.wallet import Wallet

@dataclass
class User:
    """
    Пользователь ML сервиса.

    Attributes:
        id (int): уникальный идентификатор пользователя
        email (str): email пользователя
        password (str): пароль пользователя (упрощенно для задания)
        role (str): USER / ADMIN
        wallet (Optional[Wallet]): кошелек пользователя ML сервиса
    """
    id: int
    email: str
    password: str
    role: str = "USER"
    wallet: Optional[Wallet] = None

    def __post_init__(self) -> None:
        self._validate_email()

        if self.role not in USER_ROLES:
            raise ValueError("Некорректная роль")

        if self.wallet is not None and self.wallet.user_id != self.id:
            raise ValueError("wallet.user_id должен совпадать с user.id")

    def _validate_email(self) -> None:
        """Минимальная валидация email (упрощённо, без regex как в лекции)."""
        if "@" not in self.email or "." not in self.email:
            raise ValueError("Некорректный email")
