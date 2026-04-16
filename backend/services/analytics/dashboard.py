from __future__ import annotations

import uuid
from typing import Optional, Dict, Any, Union
from datetime import datetime

from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard
from models.account.users import User, UserRole
from models.academic.course import Course
from models.academic.exam import Exam, ExamStatus
from models.academic.submission import Submission, SubmissionAttempt
from models.academic.enrollment import Enrollment
from schemas.analytics.dashboard import (
    LecturerDashboardCreate, LecturerDashboardUpdate, LecturerDashboardResponse,
    AdminDashboardCreate, AdminDashboardUpdate, AdminDashboardResponse,
    StudentDashboardCreate, StudentDashboardUpdate, StudentDashboardResponse,
)


class DashboardService:
    """Service for managing and computing dashboard analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def refresh(self, user_id: uuid.UUID, user_role: str = None, tenant_id: Optional[uuid.UUID] = None) -> None:
        """Refresh dashboard for a user (inline, not background).
        
        Args:
            user_id: The user ID to refresh dashboard for
            user_role: Optional user role to avoid extra database call
            tenant_id: Optional tenant ID for admin/superadmin dashboards
        """
        # If role not provided, fetch it
        if user_role is None:
            from services.account.user import UserService
            from core.utils.token import TokenService
            from core.config import get_settings
            
            settings = get_settings()
            token_service = TokenService(settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else None)
            user_service = UserService(self.db, token_service=token_service)
            user = await user_service.get(user_id)
            
            if not user:
                print(f"[Dashboard] User not found: {user_id}")
                return
            
            user_role = user.role
            if tenant_id is None:
                tenant_id = user.tenant_id
        
        # Normalize role to string
        role_str = str(user_role).lower()
        
        # Refresh based on role
        if role_str == "lecturer":
            await self.refresh_lecturer_dashboard(user_id)
        elif role_str in ("admin", "superadmin"):
            await self.refresh_admin_dashboard(user_id, tenant_id)
        elif role_str == "student":
            await self.refresh_student_dashboard(user_id)
        else:
            print(f"[Dashboard] Unknown user role: {user_role}")
    
    # -------------------------------------------------------------------------
    # Lecturer Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_lecturer_dashboard(self, lecturer_id: uuid.UUID) -> LecturerDashboard:
        """Get existing or create new lecturer dashboard."""
        import time
        start = time.time()
        
        stmt = select(LecturerDashboard).where(LecturerDashboard.lecturer_id == lecturer_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        query_time = (time.time() - start) * 1000
        print(f"[DASHBOARD] Query time: {query_time:.2f}ms")
        
        if not dashboard:
            create_start = time.time()
            dashboard = LecturerDashboard(
                lecturer_id=lecturer_id,
                total_courses=0,
                total_exams=0,
                total_students=0,
                pending_submissions=0,
                graded_submissions=0,
                active_courses=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)
            create_time = (time.time() - create_start) * 1000
            print(f"[DASHBOARD] Create time: {create_time:.2f}ms")
        
        return dashboard
    
    async def get_lecturer_dashboard(self, lecturer_id: uuid.UUID) -> Optional[LecturerDashboardResponse]:
        """Get lecturer dashboard by lecturer ID."""
        dashboard = await self.get_or_create_lecturer_dashboard(lecturer_id)
        return LecturerDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    async def update_lecturer_dashboard(self, lecturer_id: uuid.UUID, data: LecturerDashboardUpdate) -> LecturerDashboardResponse:
        """Update lecturer dashboard with new values."""
        dashboard = await self.get_or_create_lecturer_dashboard(lecturer_id)
        
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            if hasattr(dashboard, field):
                setattr(dashboard, field, value)
        
        await self.db.commit()
        await self.db.refresh(dashboard)
        return LecturerDashboardResponse.model_validate(dashboard)
    
    async def compute_lecturer_stats(self, lecturer_id: uuid.UUID) -> Dict[str, int]:
        """Compute real-time statistics for a lecturer."""
        # Total courses taught by lecturer
        courses_stmt = select(func.count()).select_from(
            select(Course).where(Course.lecturer_id == lecturer_id).subquery()
        )
        courses_result = await self.db.execute(courses_stmt)
        total_courses = courses_result.scalar() or 0
        
        # Total exams across all lecturer's courses
        exams_stmt = (
            select(func.count()).select_from(
                select(Exam)
                .join(Course, Exam.course_id == Course.id)
                .where(Course.lecturer_id == lecturer_id)
                .subquery()
            )
        )
        exams_result = await self.db.execute(exams_stmt)
        total_exams = exams_result.scalar() or 0
        
        # Total unique students enrolled in lecturer's courses
        students_stmt = (
            select(func.count(distinct(Enrollment.student_id)))
            .select_from(Enrollment)
            .join(Course, Enrollment.course_id == Course.id)
            .where(Course.lecturer_id == lecturer_id)
        )
        students_result = await self.db.execute(students_stmt)
        total_students = students_result.scalar() or 0
        
        # Active courses (courses with enrollments or exams)
        active_courses_stmt = (
            select(func.count(distinct(Course.id)))
            .select_from(Course)
            .outerjoin(Enrollment, Course.id == Enrollment.course_id)
            .outerjoin(Exam, Course.id == Exam.course_id)
            .where(
                and_(
                    Course.lecturer_id == lecturer_id,
                    or_(
                        Enrollment.id.isnot(None),
                        Exam.id.isnot(None)
                    )
                )
            )
        )
        active_courses_result = await self.db.execute(active_courses_stmt)
        active_courses = active_courses_result.scalar() or 0
        
        # Submissions for exams in lecturer's courses using SQL aggregates
        submissions_base = (
            select(Submission)
            .join(Exam, Submission.exam_id == Exam.id)
            .join(Course, Exam.course_id == Course.id)
            .where(Course.lecturer_id == lecturer_id)
        )
        
        pending_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(
                and_(Submission.graded_at.is_(None), Submission.attempts_count > 0)
            ).subquery()
        )
        pending_result = await self.db.execute(pending_submissions_stmt)
        pending_submissions = pending_result.scalar() or 0
        
        graded_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(Submission.graded_at.isnot(None)).subquery()
        )
        graded_result = await self.db.execute(graded_submissions_stmt)
        graded_submissions = graded_result.scalar() or 0
        
        return {
            "total_courses": total_courses,
            "total_exams": total_exams,
            "total_students": total_students,
            "active_courses": active_courses,
            "pending_submissions": pending_submissions,
            "graded_submissions": graded_submissions,
        }
    
    async def refresh_lecturer_dashboard(self, lecturer_id: uuid.UUID) -> LecturerDashboardResponse:
        """Refresh all statistics for a lecturer dashboard."""
        stats = await self.compute_lecturer_stats(lecturer_id)
        update_data = LecturerDashboardUpdate(**stats)
        return await self.update_lecturer_dashboard(lecturer_id, update_data)
    
    # -------------------------------------------------------------------------
    # Admin Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_admin_dashboard(self, admin_id: uuid.UUID) -> AdminDashboard:
        """Get existing or create new admin dashboard."""
        stmt = select(AdminDashboard).where(AdminDashboard.admin_id == admin_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        if not dashboard:
            dashboard = AdminDashboard(
                admin_id=admin_id,
                total_users=0,
                total_lecturers=0,
                total_students=0,
                total_courses=0,
                total_exams=0,
                total_submissions=0,
                total_graded_submissions=0,
                total_pending_submissions=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)
        
        return dashboard
    
    async def get_admin_dashboard(self, admin_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[AdminDashboardResponse]:
        """Get admin dashboard by admin ID. Returns cached data without auto-refresh."""
        dashboard = await self.get_or_create_admin_dashboard(admin_id)
        return AdminDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    async def update_admin_dashboard(self, admin_id: uuid.UUID, data: AdminDashboardUpdate) -> AdminDashboardResponse:
        """Update admin dashboard with new values."""
        dashboard = await self.get_or_create_admin_dashboard(admin_id)
        
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            if hasattr(dashboard, field):
                setattr(dashboard, field, value)
        
        await self.db.commit()
        await self.db.refresh(dashboard)
        return AdminDashboardResponse.model_validate(dashboard)
    
    async def compute_admin_stats(self, tenant_id: Optional[uuid.UUID] = None) -> Dict[str, int]:
        """Compute real-time statistics for admin (system-wide or tenant-specific)."""
        # Base user query
        base_user_stmt = select(User)
        if tenant_id:
            base_user_stmt = base_user_stmt.where(User.tenant_id == tenant_id)
        
        # Total users
        total_users_stmt = select(func.count()).select_from(base_user_stmt.subquery())
        total_users_result = await self.db.execute(total_users_stmt)
        total_users = total_users_result.scalar() or 0
        
        # Total lecturers
        lecturers_stmt = select(func.count()).select_from(
            base_user_stmt.where(User.role == UserRole.LECTURER).subquery()
        )
        lecturers_result = await self.db.execute(lecturers_stmt)
        total_lecturers = lecturers_result.scalar() or 0
        
        # Total students
        students_stmt = select(func.count()).select_from(
            base_user_stmt.where(User.role == UserRole.STUDENT).subquery()
        )
        students_result = await self.db.execute(students_stmt)
        total_students = students_result.scalar() or 0
        
        # Total courses
        courses_stmt = select(Course)
        if tenant_id:
            courses_stmt = courses_stmt.where(Course.tenant_id == tenant_id)
        total_courses_stmt = select(func.count()).select_from(courses_stmt.subquery())
        total_courses_result = await self.db.execute(total_courses_stmt)
        total_courses = total_courses_result.scalar() or 0
        
        # Total exams
        exams_stmt = select(Exam)
        if tenant_id:
            exams_stmt = exams_stmt.join(Course).where(Course.tenant_id == tenant_id)
        total_exams_stmt = select(func.count()).select_from(exams_stmt.subquery())
        total_exams_result = await self.db.execute(total_exams_stmt)
        total_exams = total_exams_result.scalar() or 0
        
        # Total submissions with graded/pending counts using SQL aggregates
        submissions_base = select(Submission)
        if tenant_id:
            submissions_base = (
                submissions_base
                .join(Exam, Submission.exam_id == Exam.id)
                .join(Course, Exam.course_id == Course.id)
                .where(Course.tenant_id == tenant_id)
            )
        
        # Use SQL aggregates for efficiency
        total_submissions_stmt = select(func.count()).select_from(submissions_base.subquery())
        total_submissions_result = await self.db.execute(total_submissions_stmt)
        total_submissions = total_submissions_result.scalar() or 0
        
        graded_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(Submission.graded_at.isnot(None)).subquery()
        )
        graded_result = await self.db.execute(graded_submissions_stmt)
        total_graded = graded_result.scalar() or 0
        
        pending_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(
                and_(Submission.graded_at.is_(None), Submission.attempts_count > 0)
            ).subquery()
        )
        pending_result = await self.db.execute(pending_submissions_stmt)
        total_pending = pending_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_lecturers": total_lecturers,
            "total_students": total_students,
            "total_courses": total_courses,
            "total_exams": total_exams,
            "total_submissions": total_submissions,
            "total_graded_submissions": total_graded,
            "total_pending_submissions": total_pending,
        }
    
    async def refresh_admin_dashboard(self, admin_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> AdminDashboardResponse:
        """Refresh all statistics for an admin dashboard."""
        stats = await self.compute_admin_stats(tenant_id)
        update_data = AdminDashboardUpdate(**stats)
        return await self.update_admin_dashboard(admin_id, update_data)
    
    # -------------------------------------------------------------------------
    # Student Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_student_dashboard(self, student_id: uuid.UUID) -> StudentDashboard:
        """Get existing or create new student dashboard."""
        stmt = select(StudentDashboard).where(StudentDashboard.student_id == student_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        if not dashboard:
            dashboard = StudentDashboard(
                student_id=student_id,
                total_courses=0,
                total_exams=0,
                total_submissions=0,
                total_graded_submissions=0,
                total_pending_submissions=0,
                missed_exams=0,
                upcoming_exams=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)

        return dashboard
    
    async def get_student_dashboard(self, student_id: uuid.UUID) -> Optional[StudentDashboardResponse]:
        """Get student dashboard by student ID. Returns cached data without auto-refresh."""
        dashboard = await self.get_or_create_student_dashboard(student_id)
        return StudentDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    async def update_student_dashboard(self, student_id: uuid.UUID, data: StudentDashboardUpdate) -> StudentDashboardResponse:
        """Update student dashboard with new values."""
        dashboard = await self.get_or_create_student_dashboard(student_id)
        
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            if hasattr(dashboard, field):
                setattr(dashboard, field, value)
        
        await self.db.commit()
        await self.db.refresh(dashboard)
        return StudentDashboardResponse.model_validate(dashboard)
    
    async def compute_student_stats(self, student_id: uuid.UUID) -> Dict[str, int]:
        """Compute real-time statistics for a student."""
        # Total enrolled courses
        courses_stmt = (
            select(func.count()).select_from(
                select(Enrollment)
                .where(
                    and_(
                        Enrollment.student_id == student_id,
                        Enrollment.status.in_(["active", "completed"])
                    )
                )
                .subquery()
            )
        )
        courses_result = await self.db.execute(courses_stmt)
        total_courses = courses_result.scalar() or 0

        # Total exams for enrolled courses
        enrolled_courses_stmt = (
            select(Enrollment.course_id)
            .where(Enrollment.student_id == student_id)
        )
        enrolled_courses_result = await self.db.execute(enrolled_courses_stmt)
        enrolled_course_ids = [row[0] for row in enrolled_courses_result.all()]

        total_exams = 0
        if enrolled_course_ids:
            exams_stmt = (
                select(func.count()).select_from(
                    select(Exam)
                    .where(Exam.course_id.in_(enrolled_course_ids))
                    .subquery()
                )
            )
            exams_result = await self.db.execute(exams_stmt)
            total_exams = exams_result.scalar() or 0

        # Student's submissions using SQL aggregates
        submissions_base = select(Submission).where(Submission.student_id == student_id)
        
        total_submissions_stmt = select(func.count()).select_from(submissions_base.subquery())
        total_submissions_result = await self.db.execute(total_submissions_stmt)
        total_submissions = total_submissions_result.scalar() or 0
        
        graded_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(Submission.graded_at.isnot(None)).subquery()
        )
        graded_result = await self.db.execute(graded_submissions_stmt)
        total_graded = graded_result.scalar() or 0
        
        pending_submissions_stmt = select(func.count()).select_from(
            submissions_base.where(
                and_(Submission.graded_at.is_(None), Submission.attempts_count > 0)
            ).subquery()
        )
        pending_result = await self.db.execute(pending_submissions_stmt)
        total_pending = pending_result.scalar() or 0
        
        # Get exam IDs student has submitted
        submitted_exam_ids_stmt = select(Submission.exam_id).where(
            and_(Submission.student_id == student_id, Submission.exam_id.isnot(None))
        ).distinct()
        submitted_exam_ids_result = await self.db.execute(submitted_exam_ids_stmt)
        submitted_exam_ids = {row[0] for row in submitted_exam_ids_result.all()}

        # Missed exams: exams with status FINISHED that student hasn't submitted
        missed_exams = 0
        if enrolled_course_ids:
            missed_exams_stmt = (
                select(func.count())
                .select_from(
                    select(Exam)
                    .where(
                        and_(
                            Exam.course_id.in_(enrolled_course_ids),
                            Exam.status == ExamStatus.FINISHED,
                            ~Exam.id.in_(submitted_exam_ids) if submitted_exam_ids else True
                        )
                    )
                    .subquery()
                )
            )
            missed_exams_result = await self.db.execute(missed_exams_stmt)
            missed_exams = missed_exams_result.scalar() or 0

        # Upcoming exams: exams that are NOT finished and student hasn't submitted
        upcoming_exams = 0
        if enrolled_course_ids:
            upcoming_exams_stmt = (
                select(func.count())
                .select_from(
                    select(Exam)
                    .where(
                        and_(
                            Exam.course_id.in_(enrolled_course_ids),
                            Exam.status != ExamStatus.FINISHED,
                            ~Exam.id.in_(submitted_exam_ids) if submitted_exam_ids else True
                        )
                    )
                    .subquery()
                )
            )
            upcoming_exams_result = await self.db.execute(upcoming_exams_stmt)
            upcoming_exams = upcoming_exams_result.scalar() or 0

        return {
            "total_courses": total_courses,
            "total_exams": total_exams,
            "total_submissions": total_submissions,
            "total_graded_submissions": total_graded,
            "total_pending_submissions": total_pending,
            "missed_exams": missed_exams,
            "upcoming_exams": upcoming_exams,
        }
    
    async def refresh_student_dashboard(self, student_id: uuid.UUID) -> StudentDashboardResponse:
        """Refresh all statistics for a student dashboard."""
        stats = await self.compute_student_stats(student_id)
        update_data = StudentDashboardUpdate(**stats)
        return await self.update_student_dashboard(student_id, update_data)
    
    # -------------------------------------------------------------------------
    # User Dashboard (Unified)
    # -------------------------------------------------------------------------
    
    async def get_user_dashboard(self, user: User) -> Union[LecturerDashboardResponse, AdminDashboardResponse, StudentDashboardResponse]:
        """Get appropriate dashboard for user based on role."""
        if user.role == UserRole.LECTURER:
            return await self.get_lecturer_dashboard(user.id)
        elif user.role == UserRole.ADMIN or user.role == UserRole.SUPERADMIN:
            return await self.get_admin_dashboard(user.id, user.tenant_id)
        elif user.role == UserRole.STUDENT:
            return await self.get_student_dashboard(user.id)
        else:
            raise ValueError(f"Unknown user role: {user.role}")
    
    async def refresh_user_dashboard(self, user: User) -> Union[LecturerDashboardResponse, AdminDashboardResponse, StudentDashboardResponse]:
        """Refresh dashboard for user based on role."""
        if user.role == UserRole.LECTURER:
            return await self.refresh_lecturer_dashboard(user.id)
        elif user.role == UserRole.ADMIN or user.role == UserRole.SUPERADMIN:
            return await self.refresh_admin_dashboard(user.id, user.tenant_id)
        elif user.role == UserRole.STUDENT:
            return await self.refresh_student_dashboard(user.id)
        else:
            raise ValueError(f"Unknown user role: {user.role}")


# ---------------------------------------------------------------------------
# Background task helpers (run by Celery)
# ---------------------------------------------------------------------------

async def refresh_dashboard_bg(user_id: uuid.UUID) -> None:
    """Background task to refresh a user's dashboard.
    
    Usage in routes (prefer Celery):
        from tasks.submission_tasks import refresh_dashboard_task

        @router.post("/some-endpoint")
        async def some_endpoint(...):
            # ... do work ...
            # enqueue refresh to Celery worker
            refresh_dashboard_task.delay(str(user_id))
    """
    from core.database import get_session_factory
    
    AsyncSessionLocal = get_session_factory()
    async with AsyncSessionLocal() as db:
        try:
            service = DashboardService(db)
            
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                await service.refresh_user_dashboard(user)
                print(f"[DASHBOARD BG] Refreshed dashboard for user {user_id}")
        except Exception as e:
            print(f"[DASHBOARD BG] Error refreshing dashboard for user {user_id}: {e}")
            import traceback
            traceback.print_exc()


def refresh_dashboard_bg_sync(user_id: uuid.UUID) -> None:
    """Sync wrapper for refresh_dashboard_bg (kept for compatibility). Prefer Celery tasks."""
    import asyncio
    
    # Create a new event loop and run the async function
    try:
        asyncio.run(refresh_dashboard_bg(user_id))
    except Exception as e:
        print(f"[DASHBOARD BG SYNC] Error: {e}")
        import traceback
        traceback.print_exc()


async def refresh_multiple_dashboards_bg(user_ids: list[uuid.UUID]) -> None:
    """Background task to refresh multiple users' dashboards."""
    for user_id in user_ids:
        await refresh_dashboard_bg(user_id)
