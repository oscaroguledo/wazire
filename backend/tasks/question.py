"""Kafka event handlers for question parsing and answer detection."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from core.utils.logger import logger
from schemas.academic.question import QuestionCreate
from models.academic.question import Industry

TOPIC = "tenant-tasks"


async def detect_answer_background(db, question_id: str) -> None:
    """Run AI answer detection for an MCQ question using an existing DB session."""
    from services.engine.answer_grader import QuestionAnswerer
    from sqlalchemy import select
    from models.academic.question import Question as QuestionModel, Answer as AnswerModel

    q = (await db.execute(select(QuestionModel).where(QuestionModel.id == UUID(question_id)))).scalar_one_or_none()
    if not q or q.qtype != "multiple_choice" or q.answer_id is not None:
        logger.info("[question] Answer detection skipped for question %s", question_id)
        return

    questions = [{
        "id": str(q.id),
        "question": q.text,
        "qtype": q.qtype,
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
                qtype=raw.get("qtype", "theory"),
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


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "DETECT_ANSWER": handle_detect_answer,
    "PARSE_AND_CREATE": handle_parse_and_create,
}
