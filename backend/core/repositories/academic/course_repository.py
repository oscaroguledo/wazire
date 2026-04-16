from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.course import Course
from core.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    """Repository for Course entity operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Course, db)
    
    async def get_by_lecturer(
        self, 
        lecturer_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Course]:
        """Get courses by lecturer ID with pagination."""
        stmt = select(Course).where(
            Course.lecturer_id == lecturer_id
        ).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_tenant(
        self, 
        tenant_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Course]:
        """Get courses by tenant ID with pagination."""
        stmt = select(Course).where(
            Course.tenant_id == tenant_id
        ).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_code(self, code: str, tenant_id: UUID) -> Optional[Course]:
        """Get a course by code and tenant ID."""
        stmt = select(Course).where(
            and_(Course.code == code, Course.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
