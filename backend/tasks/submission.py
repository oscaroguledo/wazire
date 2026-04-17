from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery.utils.log import get_task_logger

from celery_app import celery_app
from core.database import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.account.users import User, UserRole
from models.academic.submission import Submission, SubmissionAttempt
from models.academic.exam import Exam
from models.academic.course import Course
from services.analytics.dashboard import DashboardService
from services.academic.submission import SubmissionService
from services.academic.student_answer import StudentAnswerService

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.submission.grade_submission_attempt_task")
def grade_submission_attempt_task(attempt_id: str, exam_id: str) -> Dict[str, Any]:
    """Grade a stored submission attempt asynchronously."""

    async def _run() -> Dict[str, Any]:
        async with get_db() as db:
            await grade_attempt_bg(attempt_id=attempt_id, exam_id=exam_id, db=db)
        return {"graded": True, "attempt_id": attempt_id, "exam_id": exam_id}

    result = asyncio.run(_run())
    logger.info("Graded attempt=%s exam=%s", attempt_id, exam_id)
    return result


@celery_app.task(name="tasks.submission.refresh_dashboard_task")
def refresh_dashboard_task(user_id: str) -> Dict[str, Any]:
    """Refresh a single user's dashboard asynchronously."""
    async def _run_refresh():
        async with get_db() as db:
            await refresh_dashboard_bg(uuid.UUID(user_id), db)

    asyncio.run(_run_refresh())
    logger.info("Dashboard refreshed for user=%s", user_id)
    return {"refreshed": True, "user_id": user_id}


async def refresh_dashboard_bg(user_id: uuid.UUID, db: AsyncSession) -> None:
    """Refresh a single user's dashboard statistics in the background."""
    service = DashboardService(db)

    # Get user to determine role
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        logger.warning(f"[DASHBOARD] User not found for dashboard refresh: {user_id}")
        return

    # Refresh based on role
    if user.role == UserRole.LECTURER:
        await service.get_or_create_lecturer_dashboard(user_id)
    elif user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
        await service.get_or_create_admin_dashboard(user_id, user.tenant_id)
    elif user.role == UserRole.STUDENT:
        await service.get_or_create_student_dashboard(user_id)


async def grade_attempt_bg(
    attempt_id: str,
    exam_id: str,
    db: AsyncSession,
) -> None:
    """Re-grade a submission attempt in the background and persist the result.

    Called after the attempt row is created with score=None so the HTTP
    response returns immediately. Grading runs here, then the attempt and
    parent submission are updated.
    """
    attempt = (await db.execute(
        select(SubmissionAttempt).where(SubmissionAttempt.id == uuid.UUID(attempt_id))
    )).scalar_one_or_none()
    if not attempt:
        return

    service = SubmissionService(db)
    sa_service = StudentAnswerService(db)

    # Get submission to retrieve student_id
    submission = (await db.execute(
        select(Submission).where(Submission.id == attempt.submission_id)
    )).scalar_one_or_none()
    if not submission:
        return

    # Gather answers from StudentAnswer rows for grading
    answers_map = await sa_service.answers_map_for_student_exam(submission.student_id, uuid.UUID(exam_id))
    score, graded_answers = await service._grade_answers(uuid.UUID(exam_id), answers_map)

    # Update attempt
    attempt.score = score
    attempt.graded_at = datetime.now(timezone.utc)
    db.add(attempt)

    # Update parent submission
    submission.latest_score = score
    submission.graded_at = datetime.now(timezone.utc)
    db.add(submission)

    await db.commit()

    # Refresh dashboards after grading
    user_ids_to_refresh = [str(submission.student_id)]
    exam = (await db.execute(select(Exam).where(Exam.id == uuid.UUID(exam_id)))).scalar_one_or_none()
    if exam and exam.course_id:
        course = (await db.execute(select(Course).where(Course.id == exam.course_id))).scalar_one_or_none()
        if course and course.lecturer_id:
            user_ids_to_refresh.append(str(course.lecturer_id))

    # Refresh dashboards via Celery
    for uid in user_ids_to_refresh:
        refresh_dashboard_task.delay(uid)
