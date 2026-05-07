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

    async def upsert_metrics(
        self,
        user_id: uuid.UUID,
        role: str,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Compute fresh aggregate metrics and persist via INSERT ... ON CONFLICT DO UPDATE.

        This is the primary write path for the REFRESH_DASHBOARD Kafka worker handler.
        It computes live metrics from OLTP tables and upserts the corresponding
        analytics dashboard row, covering all three dashboard types:
        - admin/superadmin → AdminDashboard (keyed by tenant_id)
        - lecturer         → LecturerDashboard (keyed by lecturer_id)
        - student          → StudentDashboard (keyed by student_id)

        Preservation: existing admin and student dashboard refresh logic unchanged (3.80).
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from models.academic.enrollment import Enrollment, EnrollmentStatus as EnrollStatus

        if role in ("admin", "superadmin"):
            if tenant_id is None:
                row = (
                    await self.db.execute(
                        select(User.tenant_id).where(User.id == user_id)
                    )
                ).scalar_one_or_none()
                tenant_id = row or uuid.UUID(int=0)

            stats = await self.compute_admin_stats(tenant_id)

            stmt = (
                pg_insert(AdminDashboard)
                .values(
                    tenant_id=tenant_id,
                    total_users=stats["total_users"],
                    total_lecturers=stats["total_lecturers"],
                    total_students=stats["total_students"],
                    total_courses=stats["total_courses"],
                    total_exams=stats["total_exams"],
                    total_submissions=stats["total_submissions"],
                    graded_submissions=stats["graded_submissions"],
                    pending_submissions=stats["pending_submissions"],
                )
                .on_conflict_do_update(
                    index_elements=["tenant_id"],
                    set_={
                        "total_users": stats["total_users"],
                        "total_lecturers": stats["total_lecturers"],
                        "total_students": stats["total_students"],
                        "total_courses": stats["total_courses"],
                        "total_exams": stats["total_exams"],
                        "total_submissions": stats["total_submissions"],
                        "graded_submissions": stats["graded_submissions"],
                        "pending_submissions": stats["pending_submissions"],
                    },
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

        elif role == "lecturer":
            if tenant_id is None:
                row = (
                    await self.db.execute(
                        select(User.tenant_id).where(User.id == user_id)
                    )
                ).scalar_one_or_none()
                tenant_id = row or uuid.UUID(int=0)

            lecturer_stats = await self._compute_lecturer_stats(user_id, tenant_id)

            # LecturerDashboard has no unique constraint on lecturer_id in the model,
            # so we use get-or-create + update pattern
            dashboard = await self.get_lecturer_dashboard(user_id)
            if dashboard is None:
                dashboard = LecturerDashboard(
                    lecturer_id=user_id,
                    tenant_id=tenant_id,
                    total_courses=lecturer_stats["total_courses"],
                    active_courses=lecturer_stats["active_courses"],
                    total_students=lecturer_stats["total_students"],
                    total_exams=lecturer_stats["total_exams"],
                    pending_submissions=lecturer_stats["pending_submissions"],
                    graded_submissions=lecturer_stats["graded_submissions"],
                )
                self.db.add(dashboard)
            else:
                dashboard.total_courses = lecturer_stats["total_courses"]
                dashboard.active_courses = lecturer_stats["active_courses"]
                dashboard.total_students = lecturer_stats["total_students"]
                dashboard.total_exams = lecturer_stats["total_exams"]
                dashboard.pending_submissions = lecturer_stats["pending_submissions"]
                dashboard.graded_submissions = lecturer_stats["graded_submissions"]
                self.db.add(dashboard)
            await self.db.commit()

        elif role == "student":
            if tenant_id is None:
                row = (
                    await self.db.execute(
                        select(User.tenant_id).where(User.id == user_id)
                    )
                ).scalar_one_or_none()
                tenant_id = row or uuid.UUID(int=0)

            student_stats = await self._compute_student_stats(user_id, tenant_id)

            stmt = (
                pg_insert(StudentDashboard)
                .values(
                    student_id=user_id,
                    tenant_id=tenant_id,
                    total_courses=student_stats["total_courses"],
                    active_courses=student_stats["active_courses"],
                    completed_courses=student_stats["completed_courses"],
                    total_exams=student_stats["total_exams"],
                    upcoming_exams=student_stats["upcoming_exams"],
                    missed_exams=student_stats["missed_exams"],
                    total_submissions=student_stats["total_submissions"],
                    graded_submissions=student_stats["graded_submissions"],
                    pending_submissions=student_stats["pending_submissions"],
                )
                .on_conflict_do_update(
                    index_elements=["student_id"],
                    set_={
                        "total_courses": student_stats["total_courses"],
                        "active_courses": student_stats["active_courses"],
                        "completed_courses": student_stats["completed_courses"],
                        "total_exams": student_stats["total_exams"],
                        "upcoming_exams": student_stats["upcoming_exams"],
                        "missed_exams": student_stats["missed_exams"],
                        "total_submissions": student_stats["total_submissions"],
                        "graded_submissions": student_stats["graded_submissions"],
                        "pending_submissions": student_stats["pending_submissions"],
                    },
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

    async def _compute_lecturer_stats(
        self, lecturer_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict:
        """Compute aggregate metrics for a lecturer's dashboard."""
        from models.academic.enrollment import Enrollment, EnrollmentStatus as EnrollStatus
        from datetime import timezone as _tz

        total_courses = (
            await self.db.execute(
                select(func.count()).select_from(Course).where(
                    Course.lecturer_id == lecturer_id,
                    Course.tenant_id == tenant_id,
                )
            )
        ).scalar() or 0

        # Active courses: courses with at least one active enrollment
        active_courses_subq = (
            select(func.count(Enrollment.course_id.distinct()))
            .join(Course, Course.id == Enrollment.course_id)
            .where(
                Course.lecturer_id == lecturer_id,
                Course.tenant_id == tenant_id,
                Enrollment.status == EnrollStatus.ACTIVE,
            )
        )
        active_courses = (await self.db.execute(active_courses_subq)).scalar() or 0

        # Total unique students enrolled in lecturer's courses
        total_students = (
            await self.db.execute(
                select(func.count(Enrollment.student_id.distinct()))
                .join(Course, Course.id == Enrollment.course_id)
                .where(
                    Course.lecturer_id == lecturer_id,
                    Course.tenant_id == tenant_id,
                )
            )
        ).scalar() or 0

        total_exams = (
            await self.db.execute(
                select(func.count()).select_from(Exam).where(
                    Exam.course_id.in_(
                        select(Course.id).where(
                            Course.lecturer_id == lecturer_id,
                            Course.tenant_id == tenant_id,
                        )
                    )
                )
            )
        ).scalar() or 0

        graded_submissions = (
            await self.db.execute(
                select(func.count())
                .select_from(Submission)
                .join(Exam, Submission.exam_id == Exam.id)
                .join(Course, Exam.course_id == Course.id)
                .where(
                    Course.lecturer_id == lecturer_id,
                    Course.tenant_id == tenant_id,
                    Submission.graded_at.isnot(None),
                )
            )
        ).scalar() or 0

        pending_submissions = (
            await self.db.execute(
                select(func.count())
                .select_from(Submission)
                .join(Exam, Submission.exam_id == Exam.id)
                .join(Course, Exam.course_id == Course.id)
                .where(
                    Course.lecturer_id == lecturer_id,
                    Course.tenant_id == tenant_id,
                    Submission.graded_at.is_(None),
                )
            )
        ).scalar() or 0

        return {
            "total_courses": total_courses,
            "active_courses": active_courses,
            "total_students": total_students,
            "total_exams": total_exams,
            "graded_submissions": graded_submissions,
            "pending_submissions": pending_submissions,
        }

    async def _compute_student_stats(
        self, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict:
        """Compute aggregate metrics for a student's dashboard."""
        from models.academic.enrollment import Enrollment, EnrollmentStatus as EnrollStatus
        from datetime import timezone as _tz, datetime as _dt

        total_courses = (
            await self.db.execute(
                select(func.count()).select_from(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.tenant_id == tenant_id,
                )
            )
        ).scalar() or 0

        active_courses = (
            await self.db.execute(
                select(func.count()).select_from(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.tenant_id == tenant_id,
                    Enrollment.status == EnrollStatus.ACTIVE,
                )
            )
        ).scalar() or 0

        completed_courses = (
            await self.db.execute(
                select(func.count()).select_from(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.tenant_id == tenant_id,
                    Enrollment.status == EnrollStatus.COMPLETED,
                )
            )
        ).scalar() or 0

        # Enrolled course IDs
        enrolled_course_ids_result = await self.db.execute(
            select(Enrollment.course_id).where(
                Enrollment.student_id == student_id,
                Enrollment.tenant_id == tenant_id,
            )
        )
        enrolled_course_ids = [r[0] for r in enrolled_course_ids_result.all()]

        total_exams = 0
        upcoming_exams = 0
        missed_exams = 0
        if enrolled_course_ids:
            now = _dt.now(_tz.utc)

            total_exams = (
                await self.db.execute(
                    select(func.count()).select_from(Exam).where(
                        Exam.course_id.in_(enrolled_course_ids)
                    )
                )
            ).scalar() or 0

            upcoming_exams = (
                await self.db.execute(
                    select(func.count()).select_from(Exam).where(
                        Exam.course_id.in_(enrolled_course_ids),
                        Exam.start_time > now,
                    )
                )
            ).scalar() or 0

            # Missed: exam finished but student has no submission
            finished_exam_ids_result = await self.db.execute(
                select(Exam.id).where(
                    Exam.course_id.in_(enrolled_course_ids),
                    Exam.status == "finished",
                )
            )
            finished_exam_ids = [r[0] for r in finished_exam_ids_result.all()]

            if finished_exam_ids:
                submitted_exam_ids_result = await self.db.execute(
                    select(Submission.exam_id).where(
                        Submission.student_id == student_id,
                        Submission.exam_id.in_(finished_exam_ids),
                    )
                )
                submitted_exam_ids = {r[0] for r in submitted_exam_ids_result.all()}
                missed_exams = len(set(finished_exam_ids) - submitted_exam_ids)

        total_submissions = (
            await self.db.execute(
                select(func.count()).select_from(Submission).where(
                    Submission.student_id == student_id,
                    Submission.tenant_id == tenant_id,
                )
            )
        ).scalar() or 0

        graded_submissions = (
            await self.db.execute(
                select(func.count()).select_from(Submission).where(
                    Submission.student_id == student_id,
                    Submission.tenant_id == tenant_id,
                    Submission.graded_at.isnot(None),
                )
            )
        ).scalar() or 0

        pending_submissions = (
            await self.db.execute(
                select(func.count()).select_from(Submission).where(
                    Submission.student_id == student_id,
                    Submission.tenant_id == tenant_id,
                    Submission.graded_at.is_(None),
                )
            )
        ).scalar() or 0

        return {
            "total_courses": total_courses,
            "active_courses": active_courses,
            "completed_courses": completed_courses,
            "total_exams": total_exams,
            "upcoming_exams": upcoming_exams,
            "missed_exams": missed_exams,
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
            "pending_submissions": pending_submissions,
        }

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
