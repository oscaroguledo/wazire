"""Kafka event handlers for exam status updates, queued emails, and force-submission."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select

from core.database import get_db
from core.utils.logger import logger
from models.academic.exam import Exam, ExamStatus
from models.academic.course import Course
from tasks.submission import emit_refresh_dashboard, emit_grade_attempt


async def _update_exam_statuses() -> Dict[str, int]:
    """Update exam statuses using async DB session."""
    db_gen = get_db()
    db = await db_gen.__anext__()
    now = datetime.now(timezone.utc)
    activated = completed = skipped = 0

    try:
        result = await db.execute(select(Exam).where(Exam.start_time.is_not(None)))
        exams = result.scalars().all()

        for exam in exams:
            if not exam.duration:
                skipped += 1
                continue

            start = exam.start_time
            if start.tzinfo is None:
                # Reject naive timestamps — log and skip rather than silently
                # patching with replace(tzinfo=utc), which would misinterpret
                # a local-time value as UTC (Req 2.34).
                logger.error(
                    "Exam %s has a naive start_time (%s) — skipping status update. "
                    "Fix the record by supplying a timezone-aware datetime.",
                    exam.id, start,
                )
                skipped += 1
                continue

            end = start + timedelta(hours=float(exam.duration))
            prev = exam.status

            if prev == "not_started":
                if start <= now < end:
                    exam.status = "in_progress"
                    activated += 1
                elif now >= end:
                    exam.status = "finished"
                    completed += 1
            elif prev == "in_progress" and now >= end:
                exam.status = "finished"
                completed += 1

        await db.commit()
        logger.info(
            "Exam status update: activated=%d completed=%d skipped=%d",
            activated, completed, skipped,
        )
        return {"activated": activated, "completed": completed, "skipped": skipped}

    except Exception:
        await db.rollback()
        logger.exception("Exam status update failed — rolled back")
        raise
    finally:
        await db_gen.aclose()


async def handle_update_exam_status(data: Dict[str, Any]) -> None:
    """Run exam status updates."""
    try:
        await _update_exam_statuses()
    except Exception:
        logger.exception("UPDATE_EXAM_STATUS handler failed")
        raise


async def handle_send_queued_emails(data: Dict[str, Any]) -> None:
    """Process queued outbound emails."""
    # TODO: query DB for queued emails and dispatch via handle_send_email
    logger.info("SEND_QUEUED_EMAILS: no queued emails to process (stub)")


async def handle_force_submit_exam(data: Dict[str, Any]) -> None:
    """Auto-submit students who have not submitted before exam expiry.

    For each enrolled student without an existing Submission record:
      1. Create Submission(status='submitted', submitted_at=exam.end_time)
      2. Create SubmissionAttempt
      3. Emit GRADE_SUBMISSION_ATTEMPT so grading proceeds via the existing flow

    Students who already have a Submission are skipped (idempotent).

    Expected data keys: exam_id, tenant_id
    """
    exam_id_raw = data.get("exam_id")
    tenant_id_raw = data.get("tenant_id")

    if not exam_id_raw:
        logger.warning("FORCE_SUBMIT_EXAM: missing exam_id — data=%s", data)
        return

    from uuid import UUID
    try:
        exam_id = UUID(str(exam_id_raw))
        tenant_id = UUID(str(tenant_id_raw)) if tenant_id_raw else None
    except (ValueError, AttributeError) as exc:
        logger.error("FORCE_SUBMIT_EXAM: invalid UUID — %s", exc)
        return

    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        from models.academic.enrollment import Enrollment, EnrollmentStatus
        from models.academic.submission import Submission, SubmissionAttempt, SubmissionStatus
        from core.utils.kafka import producer_service

        # Fetch the exam to get end_time and tenant_id
        exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
        exam = exam_result.scalar_one_or_none()
        if not exam:
            logger.warning("FORCE_SUBMIT_EXAM: exam %s not found", exam_id)
            return

        # Determine the authoritative submission timestamp
        submitted_at = exam.end_time or datetime.now(timezone.utc)

        # Find all active enrollments for courses linked to this exam
        # Enrollments are per-course; we need to find the course_id from the exam
        if not exam.course_id:
            logger.warning("FORCE_SUBMIT_EXAM: exam %s has no course_id — cannot find enrollments", exam_id)
            return

        enrollments_result = await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == exam.course_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        enrollments = enrollments_result.scalars().all()

        if not enrollments:
            logger.info("FORCE_SUBMIT_EXAM: no active enrollments for exam %s", exam_id)
            return

        # Find students who already have a Submission for this exam
        enrolled_student_ids = [e.student_id for e in enrollments]
        existing_submissions_result = await db.execute(
            select(Submission.student_id).where(
                Submission.exam_id == exam_id,
                Submission.student_id.in_(enrolled_student_ids),
            )
        )
        already_submitted = {row[0] for row in existing_submissions_result.all()}

        unsubmitted = [e for e in enrollments if e.student_id not in already_submitted]
        if not unsubmitted:
            logger.info("FORCE_SUBMIT_EXAM: all students already submitted for exam %s", exam_id)
            return

        logger.info(
            "FORCE_SUBMIT_EXAM: auto-submitting %d students for exam %s",
            len(unsubmitted), exam_id,
        )

        effective_tenant_id = tenant_id or exam.tenant_id

        for enrollment in unsubmitted:
            # Create Submission
            submission = Submission(
                student_id=enrollment.student_id,
                exam_id=exam_id,
                tenant_id=effective_tenant_id,
                semester_id=enrollment.semester_id,
                status=SubmissionStatus.SUBMITTED,
                submitted_at=submitted_at,
                attempts=1,
            )
            db.add(submission)
            await db.flush()  # get submission.id

            # Create SubmissionAttempt
            attempt = SubmissionAttempt(submission_id=submission.id)
            db.add(attempt)
            await db.flush()  # get attempt.id

            # Emit GRADE_SUBMISSION_ATTEMPT via task helper (ensures partition key handling)
            await emit_grade_attempt(str(attempt.id), str(exam_id), tenant_id=str(effective_tenant_id) if effective_tenant_id else None)

            # Track for dashboard refresh after commit
            # (we emit after commit to ensure reads see committed state)
            # Collecting is done below
        
        # Commit all created submissions/attempts
        await db.commit()

        # Refresh dashboards for affected students and lecturer
        try:
            lecturer_id = exam.course_id and (await db.execute(select(Course).where(Course.id == exam.course_id))).scalar_one_or_none()
        except Exception:
            lecturer_id = None
        for enrollment in unsubmitted:
            try:
                await emit_refresh_dashboard(str(enrollment.student_id), tenant_id=str(effective_tenant_id) if effective_tenant_id else None)
            except Exception:
                logger.exception("FORCE_SUBMIT_EXAM: failed to emit refresh for student %s", enrollment.student_id)
        if exam and exam.course_id:
            # Emit for lecturer if available
            course_result = await db.execute(select(Course).where(Course.id == exam.course_id))
            course = course_result.scalar_one_or_none()
            if course and course.lecturer_id:
                try:
                    await emit_refresh_dashboard(str(course.lecturer_id), tenant_id=str(effective_tenant_id) if effective_tenant_id else None)
                except Exception:
                    logger.exception("FORCE_SUBMIT_EXAM: failed to emit refresh for lecturer %s", course.lecturer_id)
        logger.info(
            "FORCE_SUBMIT_EXAM: committed %d auto-submissions for exam %s",
            len(unsubmitted), exam_id,
        )

    except Exception:
        await db.rollback()
        logger.exception("FORCE_SUBMIT_EXAM failed (exam=%s)", exam_id_raw)
        raise
    finally:
        await db_gen.aclose()


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "UPDATE_EXAM_STATUS": handle_update_exam_status,
    "SEND_QUEUED_EMAILS": handle_send_queued_emails,
    "FORCE_SUBMIT_EXAM": handle_force_submit_exam,
}
