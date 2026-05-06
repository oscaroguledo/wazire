from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from .users import UserRead


class AuthBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr


class AuthCreate(AuthBase):
    """Login request."""
    password: str


class AuthUpdate(BaseModel):
    """Refresh token request."""
    model_config = ConfigDict(from_attributes=True)
    refresh_token: str


class AuthRead(BaseModel):
    """Successful auth response — tokens + user."""
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
