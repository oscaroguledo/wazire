from __future__ import annotations

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.course import Course as CourseModel
from models.academic.exam import Exam as ExamModel
from schemas.academic.course import CourseCreate, CourseUpdate


class CourseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, course_in: CourseCreate, tenant_id: UUID) -> CourseModel:
        course = CourseModel(
            name=course_in.name,
            description=course_in.description,
            course_code=course_in.course_code,
            lecturer_id=course_in.lecturer_id,
            tenant_id=tenant_id,
        )
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        
        # Re-load with relationships for serialization
        stmt = select(CourseModel).options(
            selectinload(CourseModel.lecturer),
        ).where(CourseModel.id == course.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    

    async def get(self, course_id: UUID, tenant_id: UUID) -> Optional[CourseModel]:
        # Get the course with tenant filtering and eager load relationships
        course_stmt = select(CourseModel).options(
            selectinload(CourseModel.lecturer),
        ).where(
            CourseModel.id == course_id,
            CourseModel.tenant_id == tenant_id,
        )
        course = (await self.db.execute(course_stmt)).scalar_one_or_none()
        return course

    async def _get_model(self, course_id: UUID, tenant_id: UUID) -> Optional[CourseModel]:
        """Get CourseModel object for update/delete operations (internal use only)"""
        
        course_stmt = select(CourseModel).where(
            CourseModel.id == course_id,
            CourseModel.tenant_id == tenant_id,
        )
        return (await self.db.execute(course_stmt)).scalar_one_or_none()

    async def update(self, course: CourseModel, course_in: CourseUpdate) -> CourseModel:
        data = course_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(course, field, value)
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        
        # Re-load with relationships for serialization
        stmt = select(CourseModel).options(
            selectinload(CourseModel.lecturer),
        ).where(CourseModel.id == course.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, course: CourseModel) -> None:
        await self.db.delete(course)
        await self.db.commit()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
        lecturer_id: Optional[UUID] = None
    ) -> Tuple[List[CourseModel], int]:
        """List courses with limit/offset pagination. Returns (items, total_count)."""

        # Build base query with eager loading
        base_stmt = select(CourseModel).options(
            selectinload(CourseModel.lecturer),
        )
        if tenant_id:
            base_stmt = base_stmt.where(CourseModel.tenant_id == tenant_id)
        if lecturer_id:
            base_stmt = base_stmt.where(CourseModel.lecturer_id == lecturer_id)

        # Get total count
        count_stmt = select(func.count()).select_from(CourseModel)
        if tenant_id:
            count_stmt = count_stmt.where(CourseModel.tenant_id == tenant_id)
        if lecturer_id:
            count_stmt = count_stmt.where(CourseModel.lecturer_id == lecturer_id)
        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        # Apply pagination
        stmt = base_stmt.order_by(CourseModel.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        return items, total

    async def count(self, tenant_id: Optional[UUID] = None, lecturer_id: Optional[UUID] = None) -> int:
        stmt = select(func.count()).select_from(CourseModel)
        if tenant_id:
            stmt = stmt.where(CourseModel.tenant_id == tenant_id)
        if lecturer_id:
            stmt = stmt.where(CourseModel.lecturer_id == lecturer_id)
        res = await self.db.execute(stmt)
        return int(res.scalar_one())
