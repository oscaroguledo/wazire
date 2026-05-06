from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_name(v: Optional[str]) -> Optional[str]:
    if v is not None:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Tenant name must be at least 2 characters")
        if len(v) > 200:
            raise ValueError("Tenant name must not exceed 200 characters")
    return v


def _validate_domain(v: Optional[str]) -> Optional[str]:
    if v is not None:
        v = v.strip().lower()
        if len(v) > 255:
            raise ValueError("Domain must not exceed 255 characters")
    return v


class TenantCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    admin_user_ids: Optional[list[UUID]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by: UUID

    @field_validator("name")
    @classmethod
    def validate_name(cls, v): return _validate_name(v)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v): return _validate_domain(v)


class TenantUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    updated_by: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v): return _validate_name(v)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v): return _validate_domain(v)


class TenantDelete(BaseModel):
    id: UUID
    updated_by: UUID


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
