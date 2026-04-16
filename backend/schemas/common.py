from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class BaseConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDTimestampModel(BaseConfig):
    id: Optional[UUID]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PaginatedMeta(BaseConfig):
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginatedLinks(BaseConfig):
    self: str
    next: Optional[str]
    prev: Optional[str]


class PaginatedResponse(BaseConfig, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PaginatedMeta
    links: PaginatedLinks
