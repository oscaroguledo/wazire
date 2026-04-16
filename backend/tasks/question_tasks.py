from __future__ import annotations

import asyncio
from typing import Optional

from celery.utils.log import get_task_logger

from celery_app import celery_app
from core.database import get_worker_db
from services.academic.question import QuestionService

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.question_tasks.detect_answer_task")
def detect_answer_task(question_id: str) -> dict:
    """Detect MCQ answer for a question (runs the existing async helper)."""
    try:
        async def _run():
            async with get_worker_db() as db:
                svc = QuestionService(db)
                await svc.detect_answer_background(question_id)

        asyncio.run(_run())
        logger.info("Question answer detection enqueued/ran for %s", question_id)
        return {"detected": True, "question_id": question_id}
    except Exception as e:
        logger.error("detect_answer_task failed for %s: %s", question_id, e)
        return {"detected": False, "question_id": question_id, "error": str(e)}


@celery_app.task(name="tasks.question_tasks.parse_and_create_task")
def parse_and_create_task(pages: list, industry: str, exam_id: str, mark_per_question: Optional[float], tenant_id: Optional[str] = None) -> dict:
    """Parse exam pages and create questions in the DB (runs existing async helper)."""
    try:
        async def _run():
            async with get_worker_db() as db:
                svc = QuestionService(db)
                await svc.parse_and_create_background(pages, industry, exam_id, mark_per_question, tenant_id)

        asyncio.run(_run())
        logger.info("Exam parsing task completed for exam=%s", exam_id)
        return {"created": True, "exam_id": exam_id}
    except Exception as e:
        logger.error("parse_and_create_task failed for exam=%s: %s", exam_id, e)
        return {"created": False, "exam_id": exam_id, "error": str(e)}
