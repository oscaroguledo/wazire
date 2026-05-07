from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.exam import Exam as ExamModel
from models.academic.course import Course as CourseModel
from schemas.academic.exam import ExamCreate, ExamUpdate


class ExamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, exam_in: ExamCreate, tenant_id: UUID) -> ExamModel:
        # If tenant_id not provided but course has one, inherit it
        effective_tenant_id = tenant_id
        if not effective_tenant_id and exam_in.course_id:
            course_stmt = select(CourseModel).options(
                selectinload(CourseModel.lecturer)
            ).where(CourseModel.id == exam_in.course_id)
            course_res = await self.db.execute(course_stmt)
            course = course_res.scalar_one_or_none()
            if course and course.tenant_id:
                effective_tenant_id = course.tenant_id

        # Convert duration_hours and duration_minutes to duration (Decimal)
        duration_hours = exam_in.duration_hours + (exam_in.duration_minutes / 60)
        duration = Decimal(str(duration_hours))

        # Compute end_time if start_time is provided
        end_time = None
        if exam_in.start_time is not None:
            end_time = exam_in.start_time + timedelta(hours=float(duration))

        exam = ExamModel(
            title=exam_in.title,
            description=exam_in.description,
            duration=duration,
            total_marks=exam_in.total_marks,
            passing_marks=exam_in.passing_marks,
            status=exam_in.status or 'not_started',
            start_time=exam_in.start_time,
            end_time=end_time,
            course_id=exam_in.course_id,
            tenant_id=effective_tenant_id,
        )
        self.db.add(exam)
        await self.db.commit()
        await self.db.refresh(exam)
        
        # Re-load with relationships for serialization
        stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer),
            selectinload(ExamModel.submissions),
        ).where(ExamModel.id == exam.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get(self, exam_id: UUID, tenant_id: Optional[UUID]) -> Optional[ExamModel]:
        stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer),
            selectinload(ExamModel.submissions),
        ).where(ExamModel.id == exam_id)
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, exam: ExamModel, exam_in: ExamUpdate) -> ExamModel:
        data = exam_in.model_dump(exclude_unset=True)

        # Handle duration conversion if duration_hours or duration_minutes is provided
        if 'duration_hours' in data or 'duration_minutes' in data:
            duration_hours_val = data.get('duration_hours', 0)
            duration_minutes_val = data.get('duration_minutes', 0)

            # If only one is provided, use the existing value for the other
            if 'duration_hours' not in data:
                # Get existing hours from current duration
                existing_hours = exam.duration
                duration_hours_val = int(existing_hours)
            if 'duration_minutes' not in data:
                # Get existing minutes from current duration
                existing_hours = exam.duration
                duration_minutes_val = int((existing_hours - int(existing_hours)) * Decimal(60))

            # Convert to duration (Decimal)
            total_hours = duration_hours_val + (duration_minutes_val / 60)
            data['duration'] = Decimal(str(total_hours))

            # Remove the separate fields since they don't exist in the model
            data.pop('duration_hours', None)
            data.pop('duration_minutes', None)

        for field, value in data.items():
            setattr(exam, field, value)

        # Recompute end_time whenever start_time or duration changes
        effective_start = exam.start_time
        effective_duration = exam.duration
        if effective_start is not None and effective_duration is not None:
            exam.end_time = effective_start + timedelta(hours=float(effective_duration))

        self.db.add(exam)
        await self.db.commit()
        await self.db.refresh(exam)
        
        # Re-load with relationships for serialization
        stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer),
            selectinload(ExamModel.submissions),
        ).where(ExamModel.id == exam.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, exam: ExamModel) -> None:
        await self.db.delete(exam)
        await self.db.commit()

    async def list(self, limit: int = 50, offset: int = 0, tenant_id: Optional[UUID] = None, lecturer_id: Optional[UUID] = None, student_course_ids: Optional[list] = None, course_id: Optional[UUID] = None, status: Optional[str] = None, year: Optional[int] = None) -> Tuple[List[ExamModel], int]:
        """List exams with limit/offset pagination.
        
        For lecturers, filters exams by course.lecturer_id to show only exams they teach.
        For students, filters exams by course_id in student_course_ids.
        
        Returns:
            Tuple of (exams list, total count)
        """
        stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer),
        ).order_by(ExamModel.created_at.desc()).offset(offset).limit(limit)
        
        # Filter by lecturer using subquery to avoid join issues
        if lecturer_id:
            stmt = stmt.where(ExamModel.course_id == select(CourseModel.id).where(
                CourseModel.id == ExamModel.course_id,
                CourseModel.lecturer_id == lecturer_id
            ).scalar_subquery())
        
        # Filter by student enrolled courses
        if student_course_ids:
            stmt = stmt.where(ExamModel.course_id.in_(student_course_ids))
        
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        if course_id:
            stmt = stmt.where(ExamModel.course_id == course_id)
        if status:
            stmt = stmt.where(ExamModel.status == status)
        if year:
            stmt = stmt.where(func.extract('year', ExamModel.start_time) == year)
        res = await self.db.execute(stmt)
        items = res.scalars().all()
        
        # Get total count
        count_stmt = select(func.count()).select_from(ExamModel)

        # Apply same filters for count
        if lecturer_id:
            count_stmt = count_stmt.where(ExamModel.course_id == select(CourseModel.id).where(
                CourseModel.id == ExamModel.course_id,
                CourseModel.lecturer_id == lecturer_id
            ).scalar_subquery())

        if student_course_ids:
            count_stmt = count_stmt.where(ExamModel.course_id.in_(student_course_ids))

        if tenant_id:
            count_stmt = count_stmt.where(ExamModel.tenant_id == tenant_id)
        if course_id:
            count_stmt = count_stmt.where(ExamModel.course_id == course_id)
        if status:
            count_stmt = count_stmt.where(ExamModel.status == status)
        if year:
            count_stmt = count_stmt.where(func.extract('year', ExamModel.start_time) == year)
        total = int((await self.db.execute(count_stmt)).scalar_one())
        
        return list(items), total

    async def count(self, tenant_id: Optional[UUID] = None, lecturer_id: Optional[UUID] = None, student_course_ids: Optional[list] = None, status: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(ExamModel)
        
        # Filter by lecturer using subquery
        if lecturer_id:
            stmt = stmt.where(ExamModel.course_id == select(CourseModel.id).where(
                CourseModel.id == ExamModel.course_id,
                CourseModel.lecturer_id == lecturer_id
            ).scalar_subquery())
        
        if student_course_ids:
            stmt = stmt.where(ExamModel.course_id.in_(student_course_ids))
        
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(ExamModel.status == status)
        res = await self.db.execute(stmt)
        return int(res.scalar_one())

    async def get_years(self, tenant_id: Optional[UUID] = None) -> List[int]:
        """Get list of unique years from exam start_times."""
        stmt = select(
            func.extract('year', ExamModel.start_time).label('year')
        ).where(
            ExamModel.start_time.isnot(None)
        ).distinct().order_by('year')
        
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        
        res = await self.db.execute(stmt)
        years = [int(row[0]) for row in res.all() if row[0]]
        return years
