from __future__ import annotations

from sqlmodel import Session

from models.transaction import Transaction
from models.wallet import Wallet
from models.enum import TransactionType

from services.crud import wallet as wallet_crud
from services.crud import transaction as tx_crud


class BillingService:
    """
    Баланс + транзакции (история).
    Правило: любые изменения баланса сопровождаются Transaction.
    """

    def __init__(self, session: Session):
        self.session = session

    def _require_wallet(self, user_id: int) -> Wallet:
        wallet = wallet_crud.get_wallet_by_user_id(user_id, self.session)
        if wallet is None:
            raise ValueError("У пользователя нет кошелька")
        return wallet
        
    def balance(self, user_id: int) -> int:
        wallet = self._require_wallet(user_id)
        if hasattr(wallet, "validate_balance"):
            wallet.validate_balance()
        return wallet.balance

    def can_pay(self, user_id: int, amount: int) -> bool:
        wallet = self._require_wallet(user_id)
        return wallet.can_pay(amount)

    def topup(self, user_id: int, amount: int) -> Transaction:
        wallet = self._require_wallet(user_id)
        
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть > 0")

        wallet.balance += amount
        wallet_crud.update_wallet(wallet, self.session)

        tx = Transaction(user_id=user_id, tx_type=TransactionType.TOPUP, amount=amount)
        return tx_crud.create_transaction(tx, self.session)

    def charge_after_success(self, user_id: int, amount: int, task_id: int) -> Transaction:
        """
        Ключевое бизнес-правило:
        списание вызывается сервисом только ПОСЛЕ успешного predict().
        """
        wallet = self._require_wallet(user_id)

        if amount <= 0:
            raise ValueError("Сумма списания должна быть > 0")

        if not wallet.can_pay(amount):
            raise ValueError("Недостаточно средств")

        wallet.balance -= amount
        wallet_crud.update_wallet(wallet, self.session)

        tx = Transaction(  
            user_id=user_id,
            tx_type=TransactionType.CHARGE,
            amount=amount,
            task_id=task_id,
        )
        
        return tx_crud.create_transaction(tx, self.session)




'''
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
'''