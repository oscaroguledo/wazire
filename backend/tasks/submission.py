from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery.utils.log import get_task_logger

from celery_app import celery_app
from core.database import get_sync_db
from sqlalchemy import select
from sqlalchemy.orm import Session
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
    db_gen = get_sync_db()
    db = next(db_gen)
    try:
        asyncio.run(_grade_attempt_sync(attempt_id=attempt_id, exam_id=exam_id, db=db))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
    logger.info("Graded attempt=%s exam=%s", attempt_id, exam_id)
    return {"graded": True, "attempt_id": attempt_id, "exam_id": exam_id}


async def _grade_attempt_sync(attempt_id: str, exam_id: str, db: Session) -> None:
    """Synchronous wrapper for async grading using sync DB session."""
    # Use sync DB session for queries, but asyncio.run for async service calls
    attempt = db.execute(
        select(SubmissionAttempt).where(SubmissionAttempt.id == uuid.UUID(attempt_id))
    ).scalar_one_or_none()
    if not attempt:
        return

    # Get submission to retrieve student_id
    submission = db.execute(
        select(Submission).where(Submission.id == attempt.submission_id)
    ).scalar_one_or_none()
    if not submission:
        return

    # We need to use async services, so we'll get an async session just for the service calls
    from core.database import get_db
    db_gen = get_db()
    async_db = await db_gen.__anext__()
    try:
        service = SubmissionService(async_db)
        sa_service = StudentAnswerService(async_db)

        # Gather answers from StudentAnswer rows for grading
        answers_map = await sa_service.answers_map_for_student_exam(submission.student_id, uuid.UUID(exam_id))
        score, graded_answers = await service._grade_answers(uuid.UUID(exam_id), answers_map)

        # Update attempt using sync session
        attempt.score = score
        attempt.graded_at = datetime.now(timezone.utc)
        db.add(attempt)

        # Update parent submission using sync session
        submission.latest_score = score
        submission.graded_at = datetime.now(timezone.utc)
        db.add(submission)

        db.commit()

        # Refresh dashboards after grading
        user_ids_to_refresh = [str(submission.student_id)]
        exam = db.execute(select(Exam).where(Exam.id == uuid.UUID(exam_id))).scalar_one_or_none()
        if exam and exam.course_id:
            course = db.execute(select(Course).where(Course.id == exam.course_id)).scalar_one_or_none()
            if course and course.lecturer_id:
                user_ids_to_refresh.append(str(course.lecturer_id))

        # Refresh dashboards via Celery
        for uid in user_ids_to_refresh:
            refresh_dashboard_task.delay(uid)
    finally:
        await db_gen.aclose()


@celery_app.task(name="tasks.submission.refresh_dashboard_task")
def refresh_dashboard_task(user_id: str) -> Dict[str, Any]:
    """Refresh a single user's dashboard asynchronously."""
    db_gen = get_sync_db()
    db = next(db_gen)
    try:
        asyncio.run(_refresh_dashboard_sync(user_id=user_id, db=db))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
    logger.info("Dashboard refreshed for user=%s", user_id)
    return {"refreshed": True, "user_id": user_id}


async def _refresh_dashboard_sync(user_id: str, db: Session) -> None:
    """Synchronous wrapper for async dashboard refresh using sync DB session."""
    # Get user to determine role using sync session
    user = db.execute(select(User).where(User.id == uuid.UUID(user_id))).scalar_one_or_none()
    if not user:
        logger.warning(f"[DASHBOARD] User not found for dashboard refresh: {user_id}")
        return

    # Use async session for service calls
    from core.database import get_db
    db_gen = get_db()
    async_db = await db_gen.__anext__()
    try:
        service = DashboardService(async_db)

        # Refresh based on role
        if user.role == UserRole.LECTURER:
            await service.get_or_create_lecturer_dashboard(uuid.UUID(user_id))
        elif user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            await service.get_or_create_admin_dashboard(uuid.UUID(user_id), user.tenant_id)
        elif user.role == UserRole.STUDENT:
            await service.get_or_create_student_dashboard(uuid.UUID(user_id))
    finally:
        await db_gen.aclose()
