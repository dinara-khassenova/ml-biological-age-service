from models.transaction import Transaction
from models.wallet import Wallet
from repository import Repository

class BillingService:
    """
    Баланс + транзакции (история).
    Правило: любые изменения баланса сопровождаются Transaction.
    """
    def __init__(self, repo: Repository):
        self.repo = repo

    def _require_wallet(self, user_id: int) -> Wallet:
        user = self.repo.get_user(user_id)
        if user.wallet is None:
            raise ValueError("У пользователя нет кошелька")
        if user.wallet.user_id != user.id:
            raise ValueError("Несогласованность: wallet.user_id != user.id")
        return user.wallet

    def balance(self, user_id: int) -> int:
        return self._require_wallet(user_id).balance

    def can_pay(self, user_id: int, amount: int) -> bool:
        return self._require_wallet(user_id).can_pay(amount)

    def topup(self, user_id: int, amount: int) -> Transaction:
        wallet = self._require_wallet(user_id)
        wallet.topup(amount)
        return self.repo.create_transaction(user_id=user_id, tx_type="TOPUP", amount=amount)

    def charge_after_success(self, user_id: int, amount: int, task_id: int) -> Transaction:
        """
        Ключевое бизнес-правило:
        списание вызывается сервисом только ПОСЛЕ успешного predict().
        """
        wallet = self._require_wallet(user_id)
        wallet.charge(amount)
        return self.repo.create_transaction(user_id=user_id, tx_type="CHARGE", amount=amount, task_id=task_id)