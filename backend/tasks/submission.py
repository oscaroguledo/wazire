from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict

from celery.utils.log import get_task_logger

from celery_app import celery_app
from core.database import get_db
from services.academic.submission import grade_attempt_bg
from services.analytics.dashboard import refresh_dashboard_bg

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.submission_tasks.grade_submission_attempt_task")
def grade_submission_attempt_task(attempt_id: str, exam_id: str) -> Dict[str, Any]:
    """Grade a stored submission attempt asynchronously."""

    async def _run() -> Dict[str, Any]:
        async with get_db() as db:
            await grade_attempt_bg(attempt_id=attempt_id, exam_id=exam_id, db=db)
        return {"graded": True, "attempt_id": attempt_id, "exam_id": exam_id}

    result = asyncio.run(_run())
    logger.info("Graded attempt=%s exam=%s", attempt_id, exam_id)
    return result


@celery_app.task(name="tasks.submission_tasks.refresh_dashboard_task")
def refresh_dashboard_task(user_id: str) -> Dict[str, Any]:
    """Refresh a single user's dashboard asynchronously."""
    uid = uuid.UUID(user_id)
    async def _run_refresh():
        async with get_db() as db:
            await refresh_dashboard_bg(uid, db)

    asyncio.run(_run_refresh())
    logger.info("Dashboard refreshed for user=%s", user_id)
    return {"refreshed": True, "user_id": user_id}
