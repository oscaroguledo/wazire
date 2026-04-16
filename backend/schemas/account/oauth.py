from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OAuthBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    provider: str
    provider_user_id: str


class OAuthCreate(OAuthBase):
    pass


class OAuthRead(OAuthBase):
    id: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
