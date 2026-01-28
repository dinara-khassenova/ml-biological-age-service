from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.database import get_session
from services.auth import RegAuthService
from schemas.auth import RegisterIn, LoginIn, UserOut, LoginOut


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


@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, session: Session = Depends(get_session)) -> LoginOut:
    service = RegAuthService(session)
    try:
        user = service.login(email=payload.email, password=payload.password)
        if user.id is None:
            raise RuntimeError("User.id is None")
        return LoginOut(user_id=user.id, role=user.role)
    except Exception as ex:
        raise HTTPException(status_code=403, detail=str(ex))
