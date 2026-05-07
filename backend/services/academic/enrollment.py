from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, desc, asc, select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone

from schemas.academic.enrollment import (
    EnrollmentCreate, EnrollmentUpdate,
    EnrollmentListParams, EnrollmentStatus, Semester
)
from models.account.users import User, UserRole
from models.academic.enrollment import Enrollment as EnrollmentModel
from models.academic.course import Course as CourseModel

class EnrollmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def list(self, params: EnrollmentListParams, tenant_id: Optional[uuid.UUID] = None) -> Tuple[List[EnrollmentModel], int]:
        """List enrollments with filtering and pagination.

        Builds a reusable filters list (used for both count and data queries)
        and normalizes schema inputs (ids, enums) similar to Tenant/User services.
        """
        from sqlalchemy.orm import aliased

        lecturer_alias = aliased(User)

        # Build reusable filters
        filters = []

        # Tenant scope
        if tenant_id:
            filters.append(CourseModel.tenant_id == tenant_id)

        # Normalize and apply IDs
        if params.student_id:
            try:
                sid = uuid.UUID(str(params.student_id))
                filters.append(EnrollmentModel.student_id == sid)
            except Exception:
                raise ValueError("Invalid student_id")

        if params.course_id:
            try:
                cid = uuid.UUID(str(params.course_id))
                filters.append(EnrollmentModel.course_id == cid)
            except Exception:
                raise ValueError("Invalid course_id")

        if params.lecturer_id:
            filters.append(CourseModel.lecturer_id == params.lecturer_id)

        # Status (enum or string)
        if params.status:
            status_val = params.status.value if hasattr(params.status, "value") else str(params.status)
            filters.append(EnrollmentModel.status == status_val)

        # Semester (normalize to lowercase string)
        if params.semester:
            sem = params.semester.value if hasattr(params.semester, "value") else str(params.semester)
            filters.append(EnrollmentModel.semester == sem.lower())

        # Year filtering based on created_at
        if params.year:
            start_of_year = datetime(params.year, 1, 1, tzinfo=timezone.utc)
            end_of_year = datetime(params.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            filters.append(EnrollmentModel.created_at >= start_of_year)
            filters.append(EnrollmentModel.created_at <= end_of_year)

        # Search across student and course fields
        if params.search:
            search_term = f"%{params.search}%"
            filters.append(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    CourseModel.name.ilike(search_term),
                    CourseModel.course_code.ilike(search_term),
                )
            )

        # Efficient count using same filters
        count_stmt = select(func.count(EnrollmentModel.id)).select_from(
            select(EnrollmentModel)
            .join(User, EnrollmentModel.student_id == User.id)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
            .outerjoin(lecturer_alias, CourseModel.lecturer_id == lecturer_alias.id)
            .where(*filters)
            .subquery()
        )
        total = int((await self.db.execute(count_stmt)).scalar_one())

        # Data query
        offset_val = (params.page - 1) * params.per_page
        stmt = (
            select(EnrollmentModel)
            .join(User, EnrollmentModel.student_id == User.id)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
            .outerjoin(lecturer_alias, CourseModel.lecturer_id == lecturer_alias.id)
            .options(
                selectinload(EnrollmentModel.student),
                selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer),
            )
            .where(*filters)
            .order_by(desc(EnrollmentModel.created_at))
            .offset(offset_val)
            .limit(params.per_page)
        )

        result = await self.db.execute(stmt)
        enrollments = result.scalars().all()

        return enrollments, total

    async def get(self, enrollment_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """Get enrollment by ID."""

        from sqlalchemy.orm import aliased
        lecturer_alias = aliased(User)

        stmt = (
            select(EnrollmentModel)
            .join(User, EnrollmentModel.student_id == User.id)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
            .outerjoin(lecturer_alias, CourseModel.lecturer_id == lecturer_alias.id)
            .options(
                selectinload(EnrollmentModel.student),
                selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer)
            )
            .filter(EnrollmentModel.id == enrollment_id)
        )

        # Apply tenant filtering
        if tenant_id:
            stmt = stmt.filter(CourseModel.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        enrollment = result.scalar_one_or_none()
        
        if not enrollment:
            raise ValueError("Enrollment not found")
        
        return enrollment

    

    async def create(self, enrollment_data: EnrollmentCreate, current_user: User, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """Enroll student in course."""
        try:
            student_uuid = uuid.UUID(str(enrollment_data.student_id))
            course_uuid = uuid.UUID(str(enrollment_data.course_id))
        except Exception:
            raise ValueError("Invalid student ID or course ID format")

        # Check if course exists (with tenant filtering)
        course_stmt = select(CourseModel).filter(CourseModel.id == course_uuid)
        if tenant_id:
            course_stmt = course_stmt.filter(CourseModel.tenant_id == tenant_id)
        course_result = await self.db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if not course:
            raise ValueError("Course not found")

        # Check if student exists and has student role (with tenant filtering)
        student_stmt = select(User).filter(User.id == student_uuid)
        if tenant_id:
            student_stmt = student_stmt.filter(User.tenant_id == tenant_id)
        student_result = await self.db.execute(student_stmt)
        student = student_result.scalar_one_or_none()
        if not student:
            raise ValueError("Student not found")
        if student.role != UserRole.STUDENT:
            raise ValueError("User is not a student")

        # Lecturer can only enroll students in their own courses
        if current_user.role == UserRole.LECTURER and str(course.lecturer_id) != str(current_user.id):
            raise ValueError("Can only enroll students in your own courses")
        
        # Check if already enrolled
        existing_stmt = (
            select(EnrollmentModel)
            .filter(
                and_(
                    EnrollmentModel.student_id == student_uuid,
                    EnrollmentModel.course_id == course_uuid
                )
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_enrollment = existing_result.scalar_one_or_none()
        
        if existing_enrollment:
            if existing_enrollment.status == EnrollmentStatus.DROPPED:
                # Reactivate dropped enrollment
                existing_enrollment.status = EnrollmentStatus.ACTIVE
                await self.db.commit()
                await self.db.refresh(existing_enrollment)
                # Eager load relationships before returning
                enrollment_with_rels = await self.get(existing_enrollment.id)
                return enrollment_with_rels
            else:
                raise ValueError("Student is already enrolled in this course")
        
        # Create new enrollment
        enrollment = EnrollmentModel(
            student_id=student_uuid,
            course_id=course_uuid,
            semester=enrollment_data.semester,
            status=EnrollmentStatus.ACTIVE
        )
        
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
        
        # Eager load relationships before returning
        enrollment_with_rels = await self.get(enrollment.id)
        return enrollment_with_rels

    async def update(self, enrollment_id: uuid.UUID, enrollment_data: EnrollmentUpdate, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """Update enrollment."""
        stmt = select(EnrollmentModel).options(
            selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer)
        ).filter(EnrollmentModel.id == enrollment_id)
        if tenant_id:
            stmt = stmt.join(CourseModel, EnrollmentModel.course_id == CourseModel.id).filter(CourseModel.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Enrollment not found")
        
        if enrollment_data.status is not None:
            enrollment.status = enrollment_data.status
        
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def remove(self, enrollment_id: uuid.UUID, current_user: User, tenant_id: Optional[uuid.UUID] = None) -> None:
        """Remove student enrollment."""
        stmt = (
            select(EnrollmentModel)
            .options(
                selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer)
            )
            .filter(EnrollmentModel.id == enrollment_id)
        )
        if tenant_id:
            stmt = stmt.filter(CourseModel.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Enrollment not found")
        
        # Check permissions
        if current_user.role == UserRole.LECTURER and str(enrollment.course.lecturer_id) != str(current_user.id):
            raise ValueError("Can only remove students from your own courses")
        
        await self.db.delete(enrollment)
        await self.db.commit()

    async def bulk_create(self, enrollments_data: List[EnrollmentCreate], current_user: User, tenant_id: Optional[uuid.UUID] = None) -> List[EnrollmentModel]:
        """Bulk enroll students."""
        results = []

        for enrollment_data in enrollments_data:
            try:
                enrollment = await self.create(enrollment_data, current_user, tenant_id=tenant_id)
                results.append(enrollment)
            except ValueError as e:
                # Log error but continue with other enrollments
                print(f"Failed to enroll student {enrollment_data.student_id} in course {enrollment_data.course_id}: {str(e)}")
                continue

        return results

    async def check(self, student_id: uuid.UUID, course_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """Check if student is enrolled in course."""
        # Use async-compatible query with eager loading
        stmt = (
            select(EnrollmentModel)
            .options(
                selectinload(EnrollmentModel.student),
                selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer)
            )
            .join(User, EnrollmentModel.student_id == User.id)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
            .filter(
                and_(
                    EnrollmentModel.student_id == student_id,
                    EnrollmentModel.course_id == course_id,
                    EnrollmentModel.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED, EnrollmentStatus.PENDING])
                )
            )
        )
        if tenant_id:
            stmt = stmt.filter(CourseModel.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        enrollment = result.scalar_one_or_none()
        
        if not enrollment:
            raise ValueError("Not enrolled")
        
        return enrollment
