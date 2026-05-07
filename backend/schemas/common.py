"""Common pagination schemas shared across all API responses."""
from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedLinks(BaseModel):
    """Pagination navigation links."""

    self: str
    next: Optional[str] = None
    prev: Optional[str] = None
    first: str
    last: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: List[T]
    meta: PaginatedMeta
    links: Optional[PaginatedLinks] = None


__all__ = ["PaginatedMeta", "PaginatedLinks", "PaginatedResponse"]
