from dataclasses import dataclass

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
