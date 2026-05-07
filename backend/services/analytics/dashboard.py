from __future__ import annotations

import uuid
import logging
from typing import Optional
import time

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard
from models.account.users import User, UserRole
from models.academic.course import Course
from models.academic.exam import Exam
from models.academic.submission import Submission
from schemas.analytics.dashboard import (
    LecturerDashboardRead,
    AdminDashboardRead,
    StudentDashboardRead,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboard analytics.

    Read methods (get_*) are used by API GET handlers — they never write.
    Upsert methods (upsert_*) are used exclusively by the REFRESH_DASHBOARD
    Kafka worker handler to maintain OLAP/OLTP separation.

    The legacy get_or_create_* methods are retained as thin wrappers so that
    the existing REFRESH_DASHBOARD worker handler continues to work unchanged
    (Preservation Req 3.22, 3.39).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # READ-ONLY helpers (used by API routes — no DB writes)
    # =========================================================================

    async def get_lecturer_dashboard(
        self, lecturer_id: uuid.UUID
    ) -> Optional[LecturerDashboard]:
        """Return the lecturer dashboard row, or None if it does not exist."""
        stmt = select(LecturerDashboard).where(
            LecturerDashboard.lecturer_id == lecturer_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admin_dashboard(
        self, tenant_id: uuid.UUID
    ) -> Optional[AdminDashboard]:
        """Return the admin dashboard row for a tenant, or None."""
        stmt = select(AdminDashboard).where(AdminDashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_student_dashboard(
        self, student_id: uuid.UUID
    ) -> Optional[StudentDashboard]:
        """Return the student dashboard row, or None if it does not exist."""
        stmt = select(StudentDashboard).where(
            StudentDashboard.student_id == student_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # WRITE helpers (used only by the REFRESH_DASHBOARD worker handler)
    # =========================================================================

    async def upsert_lecturer_dashboard(
        self, lecturer_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> LecturerDashboard:
        """Get or create a lecturer dashboard row (worker use only)."""
        dashboard = await self.get_lecturer_dashboard(lecturer_id)
        if not dashboard:
            dashboard = LecturerDashboard(
                lecturer_id=lecturer_id,
                tenant_id=tenant_id,
                total_courses=0,
                total_exams=0,
                total_students=0,
                pending_submissions=0,
                graded_submissions=0,
                active_courses=0,
            )
            self.db.add(dashboard)
            await self.db.flush()
        return dashboard

    async def upsert_admin_dashboard(
        self, tenant_id: uuid.UUID
    ) -> AdminDashboard:
        """Get or create an admin dashboard row keyed by tenant_id (worker use only)."""
        dashboard = await self.get_admin_dashboard(tenant_id)
        if not dashboard:
            dashboard = AdminDashboard(
                tenant_id=tenant_id,
                total_users=0,
                total_lecturers=0,
                total_students=0,
                total_courses=0,
                total_exams=0,
                total_submissions=0,
                graded_submissions=0,
                pending_submissions=0,
            )
            self.db.add(dashboard)
            await self.db.flush()
        return dashboard

    async def upsert_student_dashboard(
        self, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> StudentDashboard:
        """Get or create a student dashboard row (worker use only)."""
        dashboard = await self.get_student_dashboard(student_id)
        if not dashboard:
            dashboard = StudentDashboard(
                student_id=student_id,
                tenant_id=tenant_id,
                total_courses=0,
                active_courses=0,
                completed_courses=0,
                total_exams=0,
                total_submissions=0,
                graded_submissions=0,
                pending_submissions=0,
                missed_exams=0,
                upcoming_exams=0,
            )
            self.db.add(dashboard)
            await self.db.flush()
        return dashboard

    # =========================================================================
    # Legacy aliases — preserve existing REFRESH_DASHBOARD worker handler
    # (Req 3.22, 3.39)
    # =========================================================================

    async def get_or_create_lecturer_dashboard(
        self, lecturer_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> LecturerDashboard:
        """Backward-compatible alias used by the REFRESH_DASHBOARD handler."""
        if tenant_id is None:
            # Attempt to resolve tenant_id from the user record
            from sqlalchemy import select as _select
            from models.account.users import User as _User
            row = (
                await self.db.execute(
                    _select(_User.tenant_id).where(_User.id == lecturer_id)
                )
            ).scalar_one_or_none()
            tenant_id = row or uuid.UUID(int=0)
        return await self.upsert_lecturer_dashboard(lecturer_id, tenant_id)

    async def get_or_create_admin_dashboard(
        self,
        admin_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> AdminDashboard:
        """Backward-compatible alias — queries by tenant_id, not admin_id."""
        if tenant_id is None:
            from sqlalchemy import select as _select
            from models.account.users import User as _User
            row = (
                await self.db.execute(
                    _select(_User.tenant_id).where(_User.id == admin_id)
                )
            ).scalar_one_or_none()
            tenant_id = row or uuid.UUID(int=0)
        return await self.upsert_admin_dashboard(tenant_id)

    async def get_or_create_student_dashboard(
        self, student_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> StudentDashboard:
        """Backward-compatible alias used by the REFRESH_DASHBOARD handler."""
        if tenant_id is None:
            from sqlalchemy import select as _select
            from models.account.users import User as _User
            row = (
                await self.db.execute(
                    _select(_User.tenant_id).where(_User.id == student_id)
                )
            ).scalar_one_or_none()
            tenant_id = row or uuid.UUID(int=0)
        return await self.upsert_student_dashboard(student_id, tenant_id)

    # =========================================================================
    # Aggregation (used by /stats/tenant and REFRESH_DASHBOARD worker)
    # =========================================================================

    async def compute_admin_stats(self, tenant_id: uuid.UUID) -> dict:
        """Compute aggregate statistics for a tenant (read-only queries)."""
        try:
            total_users = (
                await self.db.execute(
                    select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
                )
            ).scalar() or 0

            total_lecturers = (
                await self.db.execute(
                    select(func.count()).select_from(User).where(
                        User.tenant_id == tenant_id, User.role == UserRole.LECTURER
                    )
                )
            ).scalar() or 0

            total_students = (
                await self.db.execute(
                    select(func.count()).select_from(User).where(
                        User.tenant_id == tenant_id, User.role == UserRole.STUDENT
                    )
                )
            ).scalar() or 0

            total_courses = (
                await self.db.execute(
                    select(func.count()).select_from(Course).where(
                        Course.tenant_id == tenant_id
                    )
                )
            ).scalar() or 0

            total_exams = (
                await self.db.execute(
                    select(func.count()).select_from(Exam).where(
                        Exam.tenant_id == tenant_id
                    )
                )
            ).scalar() or 0

            total_submissions = (
                await self.db.execute(
                    select(func.count())
                    .select_from(Submission)
                    .join(Exam, Submission.exam_id == Exam.id)
                    .where(Exam.tenant_id == tenant_id)
                )
            ).scalar() or 0

            graded_submissions = (
                await self.db.execute(
                    select(func.count())
                    .select_from(Submission)
                    .join(Exam, Submission.exam_id == Exam.id)
                    .where(Exam.tenant_id == tenant_id, Submission.graded_at.isnot(None))
                )
            ).scalar() or 0

            pending_submissions = (
                await self.db.execute(
                    select(func.count())
                    .select_from(Submission)
                    .join(Exam, Submission.exam_id == Exam.id)
                    .where(Exam.tenant_id == tenant_id, Submission.graded_at.is_(None))
                )
            ).scalar() or 0

            return {
                "total_users": total_users,
                "total_lecturers": total_lecturers,
                "total_students": total_students,
                "total_courses": total_courses,
                "total_exams": total_exams,
                "total_submissions": total_submissions,
                "graded_submissions": graded_submissions,
                "pending_submissions": pending_submissions,
            }
        except Exception as e:
            logger.error(
                "[DASHBOARD] Error computing admin stats for tenant %s: %s", tenant_id, e
            )
            raise
