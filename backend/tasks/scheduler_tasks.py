from __future__ import annotations

import asyncio
from typing import Any, Dict

from celery.utils.log import get_task_logger

from celery_app import celery_app
from services.engine.scheduler import update_exam_statuses

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.scheduler_tasks.update_exam_statuses_task")
def update_exam_statuses_task() -> Dict[str, Any]:
    """Celery wrapper around async exam status scheduler job."""
    try:
        result = asyncio.run(update_exam_statuses())
        logger.info("Exam status update completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Exam status update failed")
        raise exc
