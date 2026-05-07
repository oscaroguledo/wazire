"""Kafka event handlers for exam status updates and queued emails."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select

from core.database import get_db
from core.utils.logger import logger
from models.academic.exam import Exam


async def _update_exam_statuses() -> Dict[str, int]:
    """Update exam statuses using async DB session."""
    db_gen = get_db()
    db = await db_gen.__anext__()
    now = datetime.now(timezone.utc)
    activated = completed = skipped = tz_fixed = 0

    try:
        result = await db.execute(select(Exam).where(Exam.start_time.is_not(None)))
        exams = result.scalars().all()

        for exam in exams:
            if not exam.duration:
                skipped += 1
                continue

            start = exam.start_time
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
                tz_fixed += 1

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
            "Exam status update: activated=%d completed=%d skipped=%d tz_fixed=%d",
            activated, completed, skipped, tz_fixed,
        )
        return {"activated": activated, "completed": completed, "skipped": skipped, "tz_fixed": tz_fixed}

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


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "UPDATE_EXAM_STATUS": handle_update_exam_status,
    "SEND_QUEUED_EMAILS": handle_send_queued_emails,
}
