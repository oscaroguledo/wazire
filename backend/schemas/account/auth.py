from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .users import UserRead


class AuthLogin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthRefresh(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    refresh_token: str


class AuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: UserRead
    tokens: AuthTokens


class TokenPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    email: str
    role: str
    tenant_id: Optional[str] = None
    token_type: str
