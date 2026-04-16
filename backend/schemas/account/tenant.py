from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None


class TenantCreate(TenantBase):
    admin_user_ids: Optional[List[UUID]] = None


class TenantUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class TenantRead(TenantBase):
    id: UUID
    admin_user_ids: Optional[List[UUID]] = None
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
