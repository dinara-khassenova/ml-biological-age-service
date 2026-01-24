from models.user import User
from models.transaction import Transaction
from repository import Repository
from typing import List

from services.billing import BillingService

class AdminService:
    """
    Админ — это роль пользователя (не отдельный класс).
    """
    def __init__(self, repo: Repository, billing: BillingService):
        self.repo = repo
        self.billing = billing

    def _require_admin(self, admin_user_id: int) -> User:
        admin = self.repo.get_user(admin_user_id)
        if admin.role != "ADMIN":
            raise PermissionError("Нужен ADMIN")
        return admin

    def topup_user(self, admin_user_id: int, target_user_id: int, amount: int) -> Transaction:
        self._require_admin(admin_user_id)
        return self.billing.topup(target_user_id, amount)

    def all_transactions(self, admin_user_id: int) -> List[Transaction]:
        self._require_admin(admin_user_id)
        return self.repo.all_transactions()
    