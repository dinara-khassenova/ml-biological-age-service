from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.database import get_session
from services.auth import RegAuthService
from schemas.auth import RegisterIn, LoginIn, UserOut, TokenOut
from services.security import create_access_token
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, session: Session = Depends(get_session)) -> UserOut:
    service = RegAuthService(session)
    try:
        user = service.register(email=payload.email, password=payload.password, role=payload.role)
        if user.id is None:
            raise RuntimeError("User.id is None after register")
        return UserOut(id=user.id, email=user.email, role=user.role)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenOut:
    service = RegAuthService(session)
    try:
        user = service.login(email=form.username, password=form.password)
        if user.id is None:
            raise RuntimeError("User.id is None")

        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenOut(access_token=token)

    except Exception as ex:
        raise HTTPException(status_code=403, detail=str(ex))
