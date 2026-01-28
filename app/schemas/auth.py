from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from models.enum import UserRole 

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    role: UserRole = UserRole.USER


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: UserRole


class LoginOut(BaseModel):
    message: str = "ok"
    user_id: int
    role: UserRole

