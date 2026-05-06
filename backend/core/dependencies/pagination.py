from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import Query


class PaginationParams:
    """Lightweight pagination params object returned by dependency."""

    def __init__(self, page: int = 1, per_page: int = 10):
        if page < 1:
            raise ValueError("page must be >= 1")
        if per_page < 1:
            raise ValueError("per_page must be >= 1")
        self.page = int(page)
        self.per_page = int(per_page)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


async def get_pagination(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page (max 100)")
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


class PaginationResponse:
    """Factory for creating plain-dict pagination metadata for responses."""

    @staticmethod
    def create(page: int, per_page: int, total: int) -> Dict[str, Any]:
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
            "next_page": (page + 1) if page < pages else None,
            "prev_page": (page - 1) if page > 1 else None,
        }
