from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt  

from database.config import get_settings


def create_access_token(*, subject: str, role: str) -> str:
    """
    Create JWT token to "remember" user between requests.
    subject: user_id as string
    role: "USER" or "ADMIN"
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    expire_minutes = int(settings.JWT_EXPIRE_MINUTES or 60)
    exp = now + timedelta(minutes=expire_minutes)

    payload: Dict[str, Any] = {
        "sub": subject,     
        "role": role,       
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    if not settings.JWT_SECRET_KEY:
        # settings.validate() уже должен это проверять, но оставим защиту
        raise ValueError("JWT_SECRET_KEY is not set")

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT and return payload.
    """
    settings = get_settings()

    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is not set")

    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
