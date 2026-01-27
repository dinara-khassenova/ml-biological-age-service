from __future__ import annotations

from sqlmodel import Session

from models.enum import UserRole
from models.user import User
from models.wallet import Wallet

from services.crud import user as user_crud


class RegAuthService:
    """
    Упрощенно регистрация/авторизация.
    """

    def __init__(self, session: Session):
        self.session = session

    def register(self, email: str, password: str, role: UserRole = UserRole.USER) -> User:
        email_norm = email.strip().lower()

        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")

        existing = user_crud.get_user_by_email(email_norm, self.session)
        if existing is not None:
            raise ValueError("Пользователь с таким email уже существует")

        try:
            user = User(email=email_norm, password=password, role=role)

            if hasattr(user, "validate_email"):
                user.validate_email()

            # ⬇️ ВАЖНО: НЕ коммитим внутри crud
            self.session.add(user)
            self.session.flush()  # получаем user.id

            if role == UserRole.USER: 
                wallet = Wallet(user_id=user.id, balance=0)
                self.session.add(wallet)

            self.session.commit()
            self.session.refresh(user)
            return user

        except Exception:
            self.session.rollback()
            raise

    def login(self, email: str, password: str) -> User:
        email_norm = email.strip().lower()
        user = user_crud.get_user_by_email(email_norm, self.session)

        if user is None or user.password != password:
            raise ValueError("Неверный email или пароль")

        return user



'''
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
'''