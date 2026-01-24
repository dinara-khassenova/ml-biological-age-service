from typing import Dict, List, Optional
from models.user import User
from models.assessment import AssessmentTask
from models.transaction import Transaction

# ===================== Repository (in-memory для пункта 1 задания) =====================

class Repository:
    """
    In-memory репозиторий для этапа 1.
    На этапе 2 будет разбиение на отдельные репозитории и/или БД/ORM.
    """
    
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._tasks: Dict[int, AssessmentTask] = {}
        self._transactions: List[Transaction] = []
        self._tx_id: int = 1

    # --- users ---
    def add_user(self, user: User) -> None:
        if user.id in self._users:
            raise ValueError("User с таким id уже существует")
        if any(u.email == user.email for u in self._users.values()):
            raise ValueError("Email уже используется")
        self._users[user.id] = user

    def get_user(self, user_id: int) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise ValueError("Пользователь не найден")
        return user

    def find_user_by_email(self, email: str) -> Optional[User]:
        for u in self._users.values():
            if u.email == email:
                return u
        return None

    # --- tasks ---
    def add_task(self, task: AssessmentTask) -> None:
        if task.id in self._tasks:
            raise ValueError("Task с таким id уже существует")
        self._tasks[task.id] = task

    def update_task(self, task: AssessmentTask) -> None:
        if task.id not in self._tasks:
            raise ValueError("Task не найден")
        self._tasks[task.id] = task

    def user_tasks(self, user_id: int) -> List[AssessmentTask]:
        return [t for t in self._tasks.values() if t.user_id == user_id]

    # --- transactions ---
    def create_transaction(
        self,
        user_id: int,
        tx_type: str,
        amount: int,
        task_id: Optional[int] = None,
    ) -> Transaction:
        tx = Transaction(
            id=self._tx_id,
            user_id=user_id,
            tx_type=tx_type,
            amount=amount,
            task_id=task_id,
        )
        self._tx_id += 1
        self._transactions.append(tx)
        return tx

    def user_transactions(self, user_id: int) -> List[Transaction]:
        return [t for t in self._transactions if t.user_id == user_id]

    def all_transactions(self) -> List[Transaction]:
        return list(self._transactions)
