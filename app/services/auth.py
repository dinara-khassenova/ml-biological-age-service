from constants import USER_ROLES
from models.user import User
from models.wallet import Wallet
from repository import Repository

class RegAuthService:
    """
    Упрощенно регистрация/авторизация. 
    """

    def __init__(self, repo: Repository):
        self.repo = repo

    def register(self, user_id: int, email: str, password: str, role: str = "USER") -> User:
        email_norm = email.strip().lower()

        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")
        if role not in USER_ROLES:
            raise ValueError("Некорректная роль")
        
        wallet = Wallet(user_id=user_id) if role == "USER" else None
        user = User(id=user_id, email=email_norm, password=password, role=role, wallet=wallet)

        self.repo.add_user(user)
        return user

    def login(self, email: str, password: str) -> User:
        email_norm = email.strip().lower()
        user = self.repo.find_user_by_email(email_norm)
        if user is None or user.password != password:
            raise ValueError("Неверный email или пароль")
        return user