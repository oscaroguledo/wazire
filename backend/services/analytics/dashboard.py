from __future__ import annotations

import uuid
import logging
from typing import Optional, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard
from models.account.users import User, UserRole
from models.academic.course import Course
from models.academic.exam import Exam
from models.academic.submission import Submission
from schemas.analytics.dashboard import (
    LecturerDashboardResponse,
    AdminDashboardResponse,
    StudentDashboardResponse,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboard analytics (auto-updated by database triggers)."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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
        logger.debug(f"[DASHBOARD] Query time: {query_time:.2f}ms")
        
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
            logger.debug(f"[DASHBOARD] Create time: {create_time:.2f}ms")
        
        return dashboard
    
    
    # -------------------------------------------------------------------------
    # Admin Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_admin_dashboard(self, admin_id: uuid.UUID, tenant_id: uuid.UUID = None) -> AdminDashboard:
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
    
    async def compute_admin_stats(self, tenant_id: uuid.UUID) -> dict:
        """Compute aggregate statistics for a tenant."""
        try:
            # Count users by role
            total_users_stmt = select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
            total_lecturers_stmt = select(func.count()).select_from(User).where(
                User.tenant_id == tenant_id, User.role == UserRole.LECTURER
            )
            total_students_stmt = select(func.count()).select_from(User).where(
                User.tenant_id == tenant_id, User.role == UserRole.STUDENT
            )
            
            # Count courses
            total_courses_stmt = select(func.count()).select_from(Course).where(Course.tenant_id == tenant_id)
            
            # Count exams
            total_exams_stmt = select(func.count()).select_from(Exam).where(Exam.tenant_id == tenant_id)
            
            # Count submissions
            total_submissions_stmt = select(func.count()).select_from(Submission).join(
                Exam, Submission.exam_id == Exam.id
            ).where(Exam.tenant_id == tenant_id)
            
            # Count graded submissions
            total_graded_submissions_stmt = select(func.count()).select_from(Submission).join(
                Exam, Submission.exam_id == Exam.id
            ).where(Exam.tenant_id == tenant_id, Submission.graded_at.isnot(None))
            
            # Count pending submissions (not graded)
            total_pending_submissions_stmt = select(func.count()).select_from(Submission).join(
                Exam, Submission.exam_id == Exam.id
            ).where(Exam.tenant_id == tenant_id, Submission.graded_at.is_(None))
            
            # Execute all queries
            total_users = (await self.db.execute(total_users_stmt)).scalar() or 0
            total_lecturers = (await self.db.execute(total_lecturers_stmt)).scalar() or 0
            total_students = (await self.db.execute(total_students_stmt)).scalar() or 0
            total_courses = (await self.db.execute(total_courses_stmt)).scalar() or 0
            total_exams = (await self.db.execute(total_exams_stmt)).scalar() or 0
            total_submissions = (await self.db.execute(total_submissions_stmt)).scalar() or 0
            total_graded_submissions = (await self.db.execute(total_graded_submissions_stmt)).scalar() or 0
            total_pending_submissions = (await self.db.execute(total_pending_submissions_stmt)).scalar() or 0
            
            return {
                "total_users": total_users,
                "total_lecturers": total_lecturers,
                "total_students": total_students,
                "total_courses": total_courses,
                "total_exams": total_exams,
                "total_submissions": total_submissions,
                "total_graded_submissions": total_graded_submissions,
                "total_pending_submissions": total_pending_submissions,
            }
        except Exception as e:
            logger.error(f"[DASHBOARD] Error computing admin stats for tenant {tenant_id}: {e}")
            raise
    
    
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
