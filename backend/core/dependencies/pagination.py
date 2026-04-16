from __future__ import annotations

from typing import Optional
from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Standard pagination parameters for all list endpoints."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=10, ge=1, le=100, description="Items per page (max 100)")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page number."""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        """Get the limit (same as per_page)."""
        return self.per_page


async def get_pagination(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page (max 100)")
) -> PaginationParams:
    """Dependency for standard pagination parameters."""
    return PaginationParams(page=page, per_page=per_page)


class PaginationResponse(BaseModel):
    """Standard pagination metadata response."""
    
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        page: int,
        per_page: int,
        total: int
    ) -> "PaginationResponse":
        """Create pagination metadata from page, per_page, and total count."""
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        return cls(
            page=page,
            per_page=per_page,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
