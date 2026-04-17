from __future__ import annotations

import asyncio
from typing import Any, Dict
from datetime import datetime, timezone, timedelta

from celery.utils.log import get_task_logger

from celery_app import celery_app
from core.database import get_sync_db
from sqlalchemy import select
from models.academic.exam import Exam

logger = get_task_logger(__name__)


def update_exam_statuses() -> Dict[str, int]:
    """Update exam statuses (Celery task) - using synchronous DB session."""
    db_gen = get_sync_db()
    db = next(db_gen)
    try:
        now = datetime.now(timezone.utc)
        activated = 0
        completed = 0
        skipped_no_duration = 0
        timezone_conversions = 0
        total_tenants_processed = 0

        tenant_ids_result = db.execute(
            select(Exam.tenant_id).where(Exam.start_time.is_not(None)).distinct()
        )
        tenant_ids = [row[0] for row in tenant_ids_result.all() if row[0] is not None]

        logger.info(f"[ExamTask] Processing exams for {len(tenant_ids)} tenant(s)")

        for tenant_id in tenant_ids:
            total_tenants_processed += 1
            tenant_activated = 0
            tenant_completed = 0

            tenant_exams_result = db.execute(
                select(Exam).where(
                    Exam.start_time.is_not(None),
                    Exam.tenant_id == tenant_id
                )
            )

            for exam in tenant_exams_result.scalars():
                exam_start = exam.start_time
                if exam_start.tzinfo is None:
                    exam_start = exam_start.replace(tzinfo=timezone.utc)
                    timezone_conversions += 1
                    logger.warning(f"[ExamTask] Warning: Exam {exam.id} had naive datetime, converted to UTC")

                current_status = exam.status

                if not exam.duration:
                    skipped_no_duration += 1
                    logger.warning(f"[ExamTask] Warning: Exam {exam.id} has no duration, skipping status update")
                    continue

                duration_hours = float(exam.duration)
                end_time = exam_start + timedelta(hours=duration_hours)

                if current_status == 'not_started':
                    if now >= exam_start and now < end_time:
                        exam.status = 'in_progress'
                        exam.updated_at = now
                        activated += 1
                        tenant_activated += 1
                        logger.info(f"[ExamTask] Activated exam {exam.id}: start={exam_start}, end={end_time}, now={now}")
                    elif now >= end_time:
                        exam.status = 'finished'
                        exam.updated_at = now
                        completed += 1
                        tenant_completed += 1
                        logger.info(f"[ExamTask] Completed exam {exam.id} (missed start): start={exam_start}, end={end_time}, now={now}")

                elif current_status == 'in_progress':
                    if now >= end_time:
                        exam.status = 'finished'
                        exam.updated_at = now
                        completed += 1
                        tenant_completed += 1
                        logger.info(f"[ExamTask] Completed exam {exam.id}: start={exam_start}, end={end_time}, now={now}")

            db.commit()

            if tenant_activated > 0 or tenant_completed > 0:
                logger.info(f"[ExamTask] Tenant {tenant_id}: Activated {tenant_activated}, completed {tenant_completed}")

        if activated > 0 or completed > 0 or skipped_no_duration > 0:
            logger.info(f"[ExamTask] Summary: Tenants processed {total_tenants_processed}, activated {activated}, completed {completed}, skipped (no duration) {skipped_no_duration}, timezone conversions {timezone_conversions}")
        else:
            logger.info(f"[ExamTask] Ran at {now.isoformat()} - processed {total_tenants_processed} tenant(s), no exams to update")

        return {
            "tenants_processed": total_tenants_processed,
            "activated": activated,
            "completed": completed,
            "skipped_no_duration": skipped_no_duration,
            "timezone_conversions": timezone_conversions,
        }
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@celery_app.task(name="tasks.exam.update_exam_statuses_task")
def update_exam_statuses_task() -> Dict[str, Any]:
    """Celery wrapper for exam status update."""
    try:
        result = update_exam_statuses()
        logger.info("Exam status update completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Exam status update failed")
        raise
