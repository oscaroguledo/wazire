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

    async def list_enrollments(self, params: EnrollmentListParams, tenant_id: Optional[uuid.UUID] = None) -> Tuple[List[EnrollmentModel], int]:
        """
        List enrollments with filtering and pagination.
        """
        # Build base query with joins using select for async compatibility
        from sqlalchemy.orm import aliased

        lecturer_alias = aliased(User)

        # Use select statement for async compatibility
        stmt = (
            select(EnrollmentModel)
            .join(User, EnrollmentModel.student_id == User.id)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
            .outerjoin(lecturer_alias, CourseModel.lecturer_id == lecturer_alias.id)
            .options(
                selectinload(EnrollmentModel.student),
                selectinload(EnrollmentModel.course).selectinload(CourseModel.lecturer)
            )
        )

        # Apply tenant filtering
        if tenant_id:
            stmt = stmt.filter(CourseModel.tenant_id == tenant_id)

        # Apply filters
        if params.student_id:
            stmt = stmt.filter(EnrollmentModel.student_id == uuid.UUID(params.student_id))

        if params.course_id:
            stmt = stmt.filter(EnrollmentModel.course_id == uuid.UUID(params.course_id))

        if params.lecturer_id:
            stmt = stmt.filter(CourseModel.lecturer_id == params.lecturer_id)
        
        if params.status:
            stmt = stmt.filter(EnrollmentModel.status == params.status)
        
        if params.semester:
            # Compare as lowercase string since DB stores lowercase values
            stmt = stmt.filter(EnrollmentModel.semester == params.semester.lower())
        
        if params.year:
            # Filter by year based on created_at timestamp
            start_of_year = datetime(params.year, 1, 1, tzinfo=timezone.utc)
            end_of_year = datetime(params.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            stmt = stmt.filter(
                and_(
                    EnrollmentModel.created_at >= start_of_year,
                    EnrollmentModel.created_at <= end_of_year
                )
            )
        
        if params.search:
            search_term = f"%{params.search}%"
            stmt = stmt.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    CourseModel.name.ilike(search_term),
                    CourseModel.course_code.ilike(search_term)
                )
            )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (params.page - 1) * params.per_page
        paginated_stmt = (
            stmt.offset(offset)
            .limit(params.per_page)
            .order_by(desc(EnrollmentModel.created_at))
        )
        
        result = await self.db.execute(paginated_stmt)
        enrollments = result.scalars().all()
        
        return enrollments, total

    async def get_enrollment(self, enrollment_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """
        Get a specific enrollment by ID.
        """

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

    async def enroll_student(self, enrollment_data: EnrollmentCreate, current_user: User, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """
        Enroll a student in a course.
        """
        try:
            student_uuid = uuid.UUID(enrollment_data.student_id)
            course_uuid = uuid.UUID(enrollment_data.course_id)
        except ValueError:
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
                enrollment_with_rels = await self.get_enrollment(str(existing_enrollment.id))
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
        enrollment_with_rels = await self.get_enrollment(enrollment.id)
        return enrollment_with_rels

    async def update_enrollment(self, enrollment_id: uuid.UUID, enrollment_data: EnrollmentUpdate, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """
        Update an enrollment.
        """
        stmt = select(EnrollmentModel).filter(EnrollmentModel.id == enrollment_id)
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
        
        # Eager load relationships before returning
        enrollment_with_rels = await self.get_enrollment(enrollment.id)
        return enrollment_with_rels

    async def remove_enrollment(self, enrollment_id: uuid.UUID, current_user: User, tenant_id: Optional[uuid.UUID] = None) -> None:
        """
        Remove an enrollment (drop student from course).
        """
        from sqlalchemy.orm import aliased
        lecturer_alias = aliased(User)

        stmt = (
            select(EnrollmentModel)
            .join(CourseModel, EnrollmentModel.course_id == CourseModel.id)
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

    async def bulk_enroll(self, enrollments_data: List[EnrollmentCreate], current_user: User, tenant_id: Optional[uuid.UUID] = None) -> List[EnrollmentModel]:
        """
        Bulk enroll multiple students in courses.
        """
        results = []

        for enrollment_data in enrollments_data:
            try:
                enrollment = await self.enroll_student(enrollment_data, current_user, tenant_id=tenant_id)
                results.append(enrollment)
            except ValueError as e:
                # Log error but continue with other enrollments
                print(f"Failed to enroll student {enrollment_data.student_id} in course {enrollment_data.course_id}: {str(e)}")
                continue

        return results

    async def check_enrollment(self, student_id: uuid.UUID, course_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> EnrollmentModel:
        """
        Check if a student is enrolled in a course.
        """
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

    async def get_enrollment_statistics(self, course_id: Optional[str] = None, student_id: Optional[str] = None, lecturer_id: Optional[uuid.UUID] = None, tenant_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Get enrollment statistics for a course or student.
        """
        # Build base query
        base_stmt = select(EnrollmentModel).join(CourseModel, EnrollmentModel.course_id == CourseModel.id)

        if tenant_id:
            base_stmt = base_stmt.filter(CourseModel.tenant_id == tenant_id)

        if course_id:
            try:
                course_uuid = uuid.UUID(course_id)
                base_stmt = base_stmt.filter(EnrollmentModel.course_id == course_uuid)
            except ValueError:
                raise ValueError("Invalid course ID format")

        if student_id:
            try:
                student_uuid = uuid.UUID(student_id)
                base_stmt = base_stmt.filter(EnrollmentModel.student_id == student_uuid)
            except ValueError:
                raise ValueError("Invalid student ID format")

        if lecturer_id:
            base_stmt = base_stmt.filter(CourseModel.lecturer_id == lecturer_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Get active count
        active_stmt = base_stmt.filter(EnrollmentModel.status == EnrollmentStatus.ACTIVE)
        active_count_stmt = select(func.count()).select_from(active_stmt.subquery())
        active_result = await self.db.execute(active_count_stmt)
        active = active_result.scalar() or 0
        
        # Get completed count
        completed_stmt = base_stmt.filter(EnrollmentModel.status == EnrollmentStatus.COMPLETED)
        completed_count_stmt = select(func.count()).select_from(completed_stmt.subquery())
        completed_result = await self.db.execute(completed_count_stmt)
        completed = completed_result.scalar() or 0
        
        # Get dropped count
        dropped_stmt = base_stmt.filter(EnrollmentModel.status == EnrollmentStatus.DROPPED)
        dropped_count_stmt = select(func.count()).select_from(dropped_stmt.subquery())
        dropped_result = await self.db.execute(dropped_count_stmt)
        dropped = dropped_result.scalar() or 0
        
        # Get pending count
        pending_stmt = base_stmt.filter(EnrollmentModel.status == EnrollmentStatus.PENDING)
        pending_count_stmt = select(func.count()).select_from(pending_stmt.subquery())
        pending_result = await self.db.execute(pending_count_stmt)
        pending = pending_result.scalar() or 0
        
        return {
            "total_enrolled": total,
            "active_enrolled": active,
            "completed_enrolled": completed,
            "dropped_enrolled": dropped,
            "pending_enrolled": pending
        }
