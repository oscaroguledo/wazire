"""Kafka event handlers for question parsing, answer detection, and exam preloading."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from uuid import UUID

from core.utils.logger import logger
from schemas.academic.question import QuestionCreate
from models.academic.question import Industry, QuestionType

TOPIC = "tenant-tasks"


async def detect_answer_background(db, question_id: str) -> None:
    """Run AI answer detection for an MCQ question using an existing DB session."""
    from services.engine.answer_grader import QuestionAnswerer
    from sqlalchemy import select
    from models.academic.question import Question as QuestionModel, Answer as AnswerModel

    q = (await db.execute(select(QuestionModel).where(QuestionModel.id == UUID(question_id)))).scalar_one_or_none()
    if not q or q.qtype != QuestionType.MULTIPLE_CHOICE or q.answer_id is not None:
        logger.info("[question] Answer detection skipped for question %s", question_id)
        return

    questions = [{
        "id": str(q.id),
        "question": q.text,
        "qtype": q.qtype.value if hasattr(q.qtype, "value") else q.qtype,
        "options": q.options,
        "topic": q.industry.value if hasattr(q.industry, "value") else q.industry,
        "question_image_b64": None,
    }]

    answerer = QuestionAnswerer()
    results = answerer.process(questions)
    if not results:
        logger.info("[question] Answer detection failed for question %s", question_id)
        return

    graded_label = results[0].get("answer", "").lower().strip()
    valid_labels = {opt["label"] for opt in (q.options or [])}
    if graded_label not in valid_labels:
        logger.info("[question] Invalid answer '%s' for question %s", graded_label, question_id)
        return

    existing = (await db.execute(select(AnswerModel).where(AnswerModel.value == graded_label))).scalar_one_or_none()

    if existing:
        q.answer_id = existing.id
    else:
        new_ans = AnswerModel(value=graded_label)
        db.add(new_ans)
        await db.flush()
        q.answer_id = new_ans.id

    db.add(q)
    await db.commit()
    logger.info("[question] Answer detected for question %s: %s", question_id, graded_label)


async def parse_and_create_background(db, pages: list, industry: str, exam_id: str, mark_per_question: Optional[float], tenant_id: Optional[UUID]) -> None:
    """Parse exam pages and bulk-create questions using an existing DB session."""
    from services.engine.exam_extractor import ExamParser
    from services.academic.questions import QuestionService
    from uuid import UUID

    parser = ExamParser()
    raw_questions = parser.parse(
        pages=pages,
        industry=industry,
        exam_id=exam_id,
        mark_per_question=mark_per_question,
    )

    created = []
    errors = []
    total = len(raw_questions)

    service = QuestionService(db)
    for idx, raw in enumerate(raw_questions):
        try:
            raw_options = raw.get("options") or None
            q_in = QuestionCreate(
                number=str(raw.get("number", "")),
                text=raw.get("text", ""),
                qtype=raw.get("qtype", QuestionType.THEORY.value),
                industry=Industry(industry),
                options=raw_options,
                answer=raw.get("answer"),
                rules=raw.get("rules"),
                mark=raw.get("mark") or mark_per_question,
                exam_ids=[UUID(exam_id)],
            )
            q = await service.create(q_in, tenant_id=tenant_id)
            created.append(str(q.id))
        except Exception as e:
            errors.append({"number": raw.get("number"), "error": str(e)})

    logger.info("[question] Paper parsing complete: %d created, %d errors for exam %s", len(created), len(errors), exam_id)
    if errors:
        logger.info("[question] Errors: %s", errors)


def emit_detect_answer(question_id: str) -> None:
    """Schedule answer detection in-process using a DB session (no Kafka)."""
    import asyncio
    from .utils import with_db

    asyncio.ensure_future(
        with_db(detect_answer_background, question_id)
    )


def emit_parse_and_create(pages: list, industry: str, exam_id: str, mark: float, tenant_id: Optional[UUID]) -> None:
    """Schedule parse-and-create in-process using a DB session (no Kafka)."""
    import asyncio
    from .utils import with_db

    asyncio.ensure_future(
        with_db(parse_and_create_background, pages, industry, exam_id, mark, tenant_id)
    )


async def handle_detect_answer(data: Dict[str, Any]) -> None:
    """Auto-detect the correct answer for a question.

    Expected data keys: question_id
    """
    question_id = data.get("question_id")
    if not question_id:
        logger.warning("DETECT_ANSWER: missing question_id — data=%s", data)
        return

    from .utils import with_db
    try:
        await with_db(detect_answer_background, question_id)
        logger.info("Answer detected for question %s", question_id)
    except Exception:
        logger.exception("DETECT_ANSWER failed (question=%s)", question_id)
        raise


async def handle_parse_and_create(data: Dict[str, Any]) -> None:
    """Parse exam pages and bulk-create questions.

    Expected data keys: pages, industry, exam_id, mark_per_question, tenant_id
    """
    pages = data.get("pages")
    industry = data.get("industry")
    exam_id = data.get("exam_id")
    mark = data.get("mark_per_question")
    tenant_id_raw = data.get("tenant_id")
    tenant_id = None
    if tenant_id_raw:
        try:
            tenant_id = UUID(str(tenant_id_raw))
        except Exception:
            tenant_id = None

    if not pages or not exam_id:
        logger.warning("PARSE_AND_CREATE: missing pages or exam_id — data=%s", data)
        return

    from .utils import with_db
    try:
        await with_db(parse_and_create_background, pages, industry, exam_id, mark, tenant_id)
        logger.info("Questions parsed and created for exam %s", exam_id)
    except Exception:
        logger.exception("PARSE_AND_CREATE failed (exam=%s)", exam_id)
        raise


async def handle_preload_questions(data: Dict[str, Any]) -> None:
    """Pre-load exam questions from PostgreSQL into Redis before the exam starts.

    Expected data keys: exam_id, duration_seconds, tenant_id

    Writes:
      - exam:{exam_id}:questions  → JSON array of question dicts  (TTL = duration_seconds + 1800)
      - exam:{exam_id}:preloaded  → "1" sentinel                  (same TTL)
    """
    exam_id = data.get("exam_id")
    duration_seconds = data.get("duration_seconds", 3600)
    if not exam_id:
        logger.warning("PRELOAD_QUESTIONS: missing exam_id — data=%s", data)
        return

    ttl = int(duration_seconds) + 1800  # exam duration + 30-minute buffer

    from core.database import get_redis_client
    redis = get_redis_client()
    if redis is None:
        logger.warning("PRELOAD_QUESTIONS: Redis not configured — skipping preload for exam %s", exam_id)
        return

    from .utils import with_db
    from services.academic.questions import QuestionService

    async def _fetch_and_cache(db) -> None:
        service = QuestionService(db)
        questions = await service.list(exam_id=UUID(exam_id))
        questions_json = json.dumps([q.to_dict() for q in questions])

        questions_key = f"exam:{exam_id}:questions"
        sentinel_key = f"exam:{exam_id}:preloaded"

        await redis.set(questions_key, questions_json, ex=ttl)
        await redis.set(sentinel_key, "1", ex=ttl)
        logger.info(
            "PRELOAD_QUESTIONS: cached %d questions for exam %s (TTL=%ds)",
            len(questions), exam_id, ttl,
        )

    try:
        await with_db(_fetch_and_cache)
    except Exception:
        logger.exception("PRELOAD_QUESTIONS failed (exam=%s)", exam_id)
        raise


async def handle_upsert_student_answer(data: Dict[str, Any]) -> None:
    """Perform an atomic UPSERT of a student answer into PostgreSQL.

    Expected data keys: student_id, exam_id, question_id, answer, tenant_id

    Uses INSERT ... ON CONFLICT (student_id, exam_id, question_id) DO UPDATE
    so concurrent events for the same tuple are idempotent and produce no
    duplicate rows.  The Kafka offset is committed only after the DB write
    succeeds (handled by KafkaConsumerService's manual-commit flow).
    """
    student_id_raw = data.get("student_id")
    exam_id_raw = data.get("exam_id")
    question_id_raw = data.get("question_id")
    answer = data.get("answer")
    tenant_id_raw = data.get("tenant_id")

    if not all([student_id_raw, exam_id_raw, question_id_raw, answer is not None]):
        logger.warning("UPSERT_STUDENT_ANSWER: missing required fields — data=%s", data)
        return

    try:
        student_id = UUID(str(student_id_raw))
        exam_id = UUID(str(exam_id_raw))
        question_id = UUID(str(question_id_raw))
        tenant_id = UUID(str(tenant_id_raw)) if tenant_id_raw else None
    except (ValueError, AttributeError) as exc:
        logger.error("UPSERT_STUDENT_ANSWER: invalid UUID in payload — %s", exc)
        return

    from .utils import with_db
    from services.academic.student_answer import StudentAnswerService

    async def _upsert(db) -> None:
        service = StudentAnswerService(db)
        # Override tenant_id on the service call if provided
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from models.academic.student_answer import StudentAnswer
        from datetime import datetime, timezone

        stmt = (
            pg_insert(StudentAnswer)
            .values(
                student_id=student_id,
                exam_id=exam_id,
                question_id=question_id,
                answer=answer,
                tenant_id=tenant_id,
            )
            .on_conflict_do_update(
                constraint="uq_student_answer_student_exam_question",
                set_={
                    "answer": answer,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)
        await db.commit()
        logger.debug(
            "UPSERT_STUDENT_ANSWER: upserted answer for student=%s exam=%s question=%s",
            student_id, exam_id, question_id,
        )

    try:
        await with_db(_upsert)
    except Exception:
        logger.exception(
            "UPSERT_STUDENT_ANSWER failed (student=%s exam=%s question=%s)",
            student_id_raw, exam_id_raw, question_id_raw,
        )
        raise  # Re-raise so KafkaConsumerService does NOT commit the offset


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "DETECT_ANSWER": handle_detect_answer,
    "PARSE_AND_CREATE": handle_parse_and_create,
    "PRELOAD_QUESTIONS": handle_preload_questions,
    "UPSERT_STUDENT_ANSWER": handle_upsert_student_answer,
}
