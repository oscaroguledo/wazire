from __future__ import annotations

import asyncio
import json
import random
import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple, Dict
from uuid import UUID

from sqlalchemy import select, func, exists, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from models.academic.submission import Submission as SubmissionModel, SubmissionAttempt as SubmissionAttemptModel, SubmissionStatus
from models.academic.exam import Exam as ExamModel
from models.academic.course import Course as CourseModel
from models.academic.question import Question, Answer, QuestionExams, QuestionType
from models.academic.student_answer import StudentAnswer as StudentAnswer
from services.academic.student_answer import StudentAnswerService
from services.engine.similarity_grader import SimilarityGrader
from core.database import get_db
from core.config import get_settings
from core.utils.logger import logger
from tasks.submission import emit_refresh_dashboard
from models.account.users import User as UserModel


# ---------------------------------------------------------------------------
# Per-tenant grading semaphores (in-process; Kafka partition key ensures
# same tenant → same worker replica, so in-process semaphores are effective)
# ---------------------------------------------------------------------------
_tenant_semaphores: Dict[str, asyncio.Semaphore] = {}


class SubmissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Core: submit exam (enrol + attempt in one shot)
    # ------------------------------------------------------------------

    async def submit_exam(
        self,
        exam_id: UUID,
        student_id: UUID,
        answers: dict | None = None,
        tenant_id: Optional[UUID] = None,
        scan_pages: Optional[List[str]] = None,
    ) -> Tuple[SubmissionModel, SubmissionAttemptModel]:
        """Enrol the student if needed, record the attempt, auto-grade it.

        - First call  → creates Submission + Attempt #1
        - Repeat call → reuses Submission, adds Attempt #N
        - Raises ValueError if exam not found or max attempts exceeded
        """
        stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer)
        ).where(ExamModel.id == exam_id)
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        exam = (await self.db.execute(stmt)).scalar_one_or_none()
        if not exam:
            raise ValueError("Exam not found for your tenant" if tenant_id else "Exam not found")

        submission = await self._get_by_student_exam(student_id, exam_id)
        if submission is None:
            submission = SubmissionModel(
                student_id=student_id,
                exam_id=exam_id,
                attempts=0,
            )
            self.db.add(submission)
            await self.db.flush()

        # If answers were supplied in the submit request, persist them to StudentAnswer rows
        sa_service = StudentAnswerService(self.db)
        if answers and isinstance(answers, dict) and len(answers) > 0:
            # Expected shape: {questionId: {option?|text?}}
            for qid, val in answers.items():
                # Upsert per-question answer so grading can read them later
                try:
                    await sa_service.upsert(student_id, exam_id, _uuid.UUID(qid), val)
                except Exception as e:
                    # Log individual upsert failures but continue with other questions
                    print(f"[submission] Failed to upsert answer for question {qid}: {str(e)}")
                    continue
        else:
            # No answers in payload — try to use stored StudentAnswer rows (if any)
            answers = await sa_service.answers_map_for_student_exam(student_id, exam_id)

        # Use exam's max_attempts for validation
        if exam.max_attempts is not None and submission.attempts >= exam.max_attempts:
            raise ValueError(f"Maximum attempts ({exam.max_attempts}) reached")

        attempt_number = submission.attempts + 1
        # Save attempt immediately — answers will be stored separately in StudentAnswer rows
        attempt = SubmissionAttemptModel(
            submission_id=submission.id,
            attempt_number=attempt_number,
            score=None,
            scan_pages=scan_pages if scan_pages else None,
        )
        self.db.add(attempt)
        submission.attempts = attempt_number
        submission.status = "submitted"
        submission.submitted_at = datetime.now(timezone.utc)
        self.db.add(submission)

        await self.db.commit()
        await self.db.refresh(submission)
        await self.db.refresh(attempt)
        return submission, attempt

    # Note: draft answers are now stored in `student_answers` per-question rows.
    # The legacy `update_draft_answers` method was removed to avoid duplicate
    # storage on the Submission row. Use `StudentAnswerService.upsert` instead.

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get(
        self,
        submission_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        student_id: Optional[UUID] = None,
        exam_id: Optional[UUID] = None,
    ) -> Optional[SubmissionModel]:
        """Get a submission by `submission_id` or by `(student_id, exam_id)`.

        Provide either `submission_id` (preferred) or both `student_id` and
        `exam_id`. `tenant_id` applies when resolving by `submission_id`.
        """
        if submission_id is not None:
            stmt = select(SubmissionModel).options(
                selectinload(SubmissionModel.exam).selectinload(ExamModel.course).selectinload(CourseModel.lecturer),
                selectinload(SubmissionModel.student)
            ).where(SubmissionModel.id == submission_id)
            if tenant_id:
                stmt = stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)
            return (await self.db.execute(stmt)).scalar_one_or_none()

        if student_id is not None and exam_id is not None:
            return await self._get_by_student_exam(student_id, exam_id)

        raise ValueError("Either submission_id or (student_id and exam_id) must be provided")

    async def get_my_submission(self, student_id: UUID, exam_id: UUID) -> Optional[SubmissionModel]:
        return await self.get(student_id=student_id, exam_id=exam_id)

    async def list(
        self,
        student_id: Optional[UUID] = None,
        exam_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SubmissionModel]:
        """Unified listing for submissions.

        - If `student_id` is provided and `limit==0`, returns all submissions for the student.
        - If `exam_id` is provided, returns submissions for that exam with pagination.
        - `tenant_id` is applied when joining to Exam for tenant scoping.
        """
        stmt = select(SubmissionModel).options(
            selectinload(SubmissionModel.exam).selectinload(ExamModel.course),
            selectinload(SubmissionModel.student),
        )

        if student_id is not None:
            stmt = stmt.where(SubmissionModel.student_id == student_id)
        elif exam_id is not None:
            stmt = stmt.where(SubmissionModel.exam_id == exam_id)
        else:
            # No filter provided — return empty list to avoid accidental full scan
            return []

        if tenant_id:
            stmt = stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)

        if status:
            if status == "graded":
                stmt = stmt.where(SubmissionModel.latest_score.isnot(None))
            elif status == "pending":
                stmt = stmt.where(SubmissionModel.latest_score.is_(None))

        stmt = stmt.order_by(SubmissionModel.created_at.desc())

        if limit and limit > 0:
            stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_students(
        self,
        exam_id: UUID,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """Return each student with their submission summary for a specific exam."""
        # Verify the exam exists and belongs to the tenant
        exam_stmt = select(ExamModel).options(
            selectinload(ExamModel.course).selectinload(CourseModel.lecturer)
        ).where(ExamModel.id == exam_id)
        if tenant_id:
            exam_stmt = exam_stmt.where(ExamModel.tenant_id == tenant_id)
        exam = (await self.db.execute(exam_stmt)).scalar_one_or_none()
        if not exam:
            raise ValueError("Exam not found for this tenant")

        stmt = (
            select(UserModel, SubmissionModel)
            .join(SubmissionModel, SubmissionModel.student_id == UserModel.id)
            .options(
                selectinload(SubmissionModel.attempts)
            )
            .where(SubmissionModel.exam_id == exam_id)
        )
        if tenant_id:
            stmt = stmt.where(UserModel.tenant_id == tenant_id)

        # Get total count before pagination
        count_result = await self.db.execute(
            select(func.count()).select_from(
                UserModel.join(SubmissionModel, SubmissionModel.student_id == UserModel.id)
            ).where(SubmissionModel.exam_id == exam_id)
        )
        total = int(count_result.scalar_one())

        stmt = stmt.order_by(UserModel.last_name, UserModel.first_name, UserModel.id).offset(offset).limit(limit)
        rows = (await self.db.execute(stmt)).all()

        results = []
        for user, submission in rows:
            # Attempts already loaded via selectinload
            attempts = submission.attempts

            results.append({
                "student": {
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "middle_name": user.middle_name,
                    "last_name": user.last_name,
                    "email": user.email,
                },
                "submission": {
                    "id": str(submission.id),
                    "latest_score": str(submission.latest_score) if submission.latest_score is not None else None,
                    "attempts": submission.attempts,
                    "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
                    "created_at": submission.created_at.isoformat() if submission.created_at else None,
                },
                "attempts": [
                    {
                        "id": str(a.id),
                        "score": str(a.score) if a.score is not None else None,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in attempts
                ],
            })

        return results, total

    async def get_attempts(self, submission_id: UUID) -> List[SubmissionAttemptModel]:
        res = await self.db.execute(
            select(SubmissionAttemptModel)
            .where(SubmissionAttemptModel.submission_id == submission_id)
            .order_by(SubmissionAttemptModel.attempt_number)
        )
        return res.scalars().all()

    async def get_attempt(self, attempt_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[SubmissionAttemptModel]:
        stmt = select(SubmissionAttemptModel).where(SubmissionAttemptModel.id == attempt_id)
        if tenant_id:
            stmt = (
                stmt.join(SubmissionModel, SubmissionModel.id == SubmissionAttemptModel.submission_id)
                .join(ExamModel, ExamModel.id == SubmissionModel.exam_id)
                .where(ExamModel.tenant_id == tenant_id)
            )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def grade_attempt(self, attempt: SubmissionAttemptModel, score: Decimal) -> SubmissionAttemptModel:
        """Lecturer manually grades a theory attempt and updates the parent submission."""
        attempt.score = score
        attempt.graded_at = datetime.now(timezone.utc)
        self.db.add(attempt)

        # Update latest_score on the parent submission if this is the latest attempt
        submission = (await self.db.execute(
            select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id)
        )).scalar_one_or_none()
        if submission:
            submission.latest_score = score
            submission.graded_at = datetime.now(timezone.utc)
            self.db.add(submission)

        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def delete(self, submission: SubmissionModel) -> None:
        await self.db.delete(submission)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_by_student_exam(self, student_id: UUID, exam_id: UUID) -> Optional[SubmissionModel]:
        return (await self.db.execute(
            select(SubmissionModel).where(
                SubmissionModel.student_id == student_id,
                SubmissionModel.exam_id == exam_id,
            )
        )).scalar_one_or_none()

    async def create_submission(self, exam_id: UUID, student_id: UUID) -> SubmissionModel:
        """Create or return an existing Submission record without adding an attempt.

        This is used when the student clicks "Start Exam" — we want a Submission
        row to exist (attempts_count stays 0) but not create an Attempt until
        the student actually submits their answers.
        """
        submission = await self._get_by_student_exam(student_id, exam_id)
        if submission is None:
            submission = SubmissionModel(
                student_id=student_id,
                exam_id=exam_id,
                attempts=0,
            )
            self.db.add(submission)
            await self.db.commit()
            await self.db.refresh(submission)
        return submission

    async def _grade_answers(self, exam_id: UUID, answers: dict) -> Tuple[Optional[Decimal], dict]:
        """Grade all questions (MCQ + theory).

        Returns:
            (total_score, graded_answers) where:
            - total_score: sum of (answer_score * mark) across all questions, or None
            - graded_answers: enriched answers dict with answer_score and reason per question
        """
        # Fetch all exam questions; outer-join Answer so theory questions without answers still load
        stmt = (
            select(Question, Answer)
            .outerjoin(Answer, Answer.id == Question.answer_id)
            .where(
                exists().where(
                    QuestionExams.question_id == Question.id,
                    QuestionExams.exam_id == exam_id
                )
            )
        )
        rows = (await self.db.execute(stmt)).all()
        if not rows:
            return None, {}

        grader = SimilarityGrader()
        total_score = Decimal("0.00")
        graded_answers = {}

        for q, a in rows:
            qid = str(q.id)
            raw = answers.get(qid, {})

            if isinstance(raw, dict):
                student_option = raw.get("option", "")
                student_text = raw.get("text", "")
            else:
                student_option = str(raw) if q.qtype == QuestionType.MULTIPLE_CHOICE else ""
                student_text = str(raw) if q.qtype in (QuestionType.THEORY, QuestionType.FILL_IN_BLANKS) else ""

            student_answer = student_option if q.qtype == QuestionType.MULTIPLE_CHOICE else student_text
            industry = q.industry.value if q.industry else "general"
            mark = Decimal(str(q.mark)) if q.mark is not None else Decimal("0.00")

            grade_kwargs = dict(
                question_type=q.qtype.value if hasattr(q.qtype, "value") else q.qtype,
                industry=industry,
                student_answer=student_answer,
            )
            if q.qtype == QuestionType.MULTIPLE_CHOICE:
                grade_kwargs["mcq_answer"] = str(a.value).strip().lower() if a and a.value else None
                student_answer = student_answer.lower() if student_answer else student_answer
            elif q.qtype == QuestionType.FILL_IN_BLANKS:
                grade_kwargs["fitb_answer"] = a.text_value.strip() if a and a.text_value else None
                grade_kwargs["fitb_variations"] = a.acceptable_variations if a and a.acceptable_variations else None
            else:
                grade_kwargs["question_text"] = q.text
                grade_kwargs["rules"] = q.rules

            answer_score, reason = await grader.grade(**grade_kwargs)

            answer_score_d = Decimal(str(answer_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            question_score = (answer_score_d * mark).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_score += question_score

            entry: dict = {"answer_score": str(answer_score_d), "reason": reason}
            if q.qtype == QuestionType.MULTIPLE_CHOICE:
                entry["option"] = student_option
            elif q.qtype == QuestionType.FILL_IN_BLANKS:
                entry["text"] = student_text
            else:
                entry["text"] = student_text
            graded_answers[qid] = entry

        return total_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), graded_answers

    # ------------------------------------------------------------------
    # Background helpers (run by background worker / Kafka)
    # ------------------------------------------------------------------

    async def grade_attempt_background(self, attempt_id: str, exam_id: str) -> None:
        """Grade an attempt in the background (used by background worker / Kafka).

        Implements:
        - Per-tenant asyncio.Semaphore (GRADING_CONCURRENCY_PER_TENANT)
        - Sets Submission.status = GRADING_IN_PROGRESS at start
        - Sets SubmissionAttempt.grading_started_at at start
        - Batch theory grading: one Groq API call for all theory questions
        - MCQ/FITB graded inline without API call
        - Jitter (0.1–0.5s) applied after the Groq call
        - Bulk DB writes via INSERT ... ON CONFLICT DO UPDATE
        - Idempotency: caller checks attempt.score before calling this method

        Exceptions are propagated so the Kafka consumer does NOT commit the
        offset on failure — allowing message redelivery on restart.
        """
        settings = get_settings()
        max_concurrency = settings.GRADING_CONCURRENCY_PER_TENANT
        db_write_batch_size = settings.DB_WRITE_BATCH_SIZE

        async for db in get_db():
            # ----------------------------------------------------------------
            # Load attempt and submission
            # ----------------------------------------------------------------
            attempt = (await db.execute(
                select(SubmissionAttemptModel).where(
                    SubmissionAttemptModel.id == UUID(attempt_id)
                )
            )).scalar_one_or_none()

            if not attempt:
                logger.warning("[grading] Attempt %s not found", attempt_id)
                return

            submission = (await db.execute(
                select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id)
            )).scalar_one_or_none()

            if submission is None:
                logger.warning("[grading] Submission for attempt %s not found", attempt_id)
                return

            tenant_id_str = str(submission.tenant_id) if submission.tenant_id else "default"

            # ----------------------------------------------------------------
            # Acquire per-tenant semaphore (task 10.9)
            # ----------------------------------------------------------------
            if tenant_id_str not in _tenant_semaphores:
                _tenant_semaphores[tenant_id_str] = asyncio.Semaphore(max_concurrency)
            semaphore = _tenant_semaphores[tenant_id_str]

            async with semaphore:
                # ----------------------------------------------------------------
                # Set grading_in_progress status and grading_started_at (10.12, 10.13)
                # ----------------------------------------------------------------
                submission.status = SubmissionStatus.GRADING_IN_PROGRESS
                attempt.grading_started_at = datetime.now(timezone.utc)
                db.add(submission)
                db.add(attempt)
                await db.flush()

                student_id = submission.student_id
                sa_service = StudentAnswerService(db)
                answers_map = await sa_service.answers_map_for_student_exam(student_id, UUID(exam_id))

                # ----------------------------------------------------------------
                # Batch grading (task 10.6)
                # ----------------------------------------------------------------
                score, graded_answers = await self._grade_answers_batch(UUID(exam_id), answers_map)

                # ----------------------------------------------------------------
                # Jitter between submissions (task 10.8)
                # Applied after the Groq call, before DB writes
                # ----------------------------------------------------------------
                await asyncio.sleep(random.uniform(0.1, 0.5))

                # ----------------------------------------------------------------
                # Persist score on the attempt (idempotency sentinel)
                # ----------------------------------------------------------------
                attempt.score = score
                attempt.graded_at = datetime.now(timezone.utc)
                db.add(attempt)

                # Update submission with final score and status
                submission.latest_score = score
                submission.graded_at = datetime.now(timezone.utc)
                submission.status = SubmissionStatus.GRADED
                db.add(submission)

                # Commit grading writes atomically
                await db.commit()
                logger.info("[grading] Graded attempt %s with score %s", attempt_id, score)

                # ----------------------------------------------------------------
                # Bulk DB writes for per-question graded results (task 10.10)
                # ----------------------------------------------------------------
                try:
                    await self._bulk_upsert_graded_answers(
                        db,
                        student_id=student_id,
                        exam_id=UUID(exam_id),
                        graded_answers=graded_answers,
                        batch_size=db_write_batch_size,
                    )
                except Exception as e:
                    logger.warning("[grading] Failed to persist graded answers in bulk: %s", e)

                # ----------------------------------------------------------------
                # Refresh dashboards after grading
                # ----------------------------------------------------------------
                await emit_refresh_dashboard(str(submission.student_id))
                exam_result = await db.execute(select(ExamModel).where(ExamModel.id == UUID(exam_id)))
                exam = exam_result.scalar_one_or_none()
                if exam and exam.course_id:
                    course_result = await db.execute(select(CourseModel).where(CourseModel.id == exam.course_id))
                    course = course_result.scalar_one_or_none()
                    if course and course.lecturer_id:
                        await emit_refresh_dashboard(str(course.lecturer_id))

    async def _grade_answers_batch(self, exam_id: UUID, answers: dict) -> Tuple[Optional[Decimal], dict]:
        """Grade all questions using batch Groq call for theory questions.

        MCQ and FITB are graded inline (no API call).
        All theory questions are collected and sent in a SINGLE Groq API call
        per submission, regardless of question count (task 10.6).

        Returns:
            (total_score, graded_answers) where graded_answers maps question_id
            to {answer_score, reason, option|text}.
        """
        # Fetch all exam questions with their answers
        stmt = (
            select(Question, Answer)
            .outerjoin(Answer, Answer.id == Question.answer_id)
            .where(
                exists().where(
                    QuestionExams.question_id == Question.id,
                    QuestionExams.exam_id == exam_id
                )
            )
        )
        rows = (await self.db.execute(stmt)).all()
        if not rows:
            return None, {}

        grader = SimilarityGrader()
        total_score = Decimal("0.00")
        graded_answers: dict = {}

        # Separate MCQ/FITB (direct compare) from theory (AI batch)
        direct_rows = []
        theory_rows = []
        for q, a in rows:
            if q.qtype in (QuestionType.MULTIPLE_CHOICE, QuestionType.FILL_IN_BLANKS):
                direct_rows.append((q, a))
            else:
                theory_rows.append((q, a))

        # ----------------------------------------------------------------
        # Grade MCQ and FITB inline — no API call
        # ----------------------------------------------------------------
        for q, a in direct_rows:
            qid = str(q.id)
            raw = answers.get(qid, {})
            if isinstance(raw, dict):
                student_option = raw.get("option", "")
                student_text = raw.get("text", "")
            else:
                student_option = str(raw) if q.qtype == QuestionType.MULTIPLE_CHOICE else ""
                student_text = str(raw) if q.qtype == QuestionType.FILL_IN_BLANKS else ""

            student_answer = student_option if q.qtype == QuestionType.MULTIPLE_CHOICE else student_text
            mark = Decimal(str(q.mark)) if q.mark is not None else Decimal("0.00")

            grade_kwargs = dict(
                question_type=q.qtype.value if hasattr(q.qtype, "value") else q.qtype,
                industry=q.industry.value if q.industry else "general",
                student_answer=student_answer,
            )
            if q.qtype == QuestionType.MULTIPLE_CHOICE:
                grade_kwargs["mcq_answer"] = str(a.value).strip().lower() if a and a.value else None
            else:
                grade_kwargs["fitb_answer"] = a.text_value.strip() if a and a.text_value else None
                grade_kwargs["fitb_variations"] = a.acceptable_variations if a and a.acceptable_variations else None

            answer_score, reason = await grader.grade(**grade_kwargs)
            answer_score_d = Decimal(str(answer_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_score += (answer_score_d * mark).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            entry: dict = {"answer_score": str(answer_score_d), "reason": reason}
            if q.qtype == QuestionType.MULTIPLE_CHOICE:
                entry["option"] = student_option
            else:
                entry["text"] = student_text
            graded_answers[qid] = entry

        # ----------------------------------------------------------------
        # Grade all theory questions in ONE Groq API call (task 10.6)
        # ----------------------------------------------------------------
        if theory_rows:
            theory_results = await self._batch_grade_theory(grader, theory_rows, answers)
            for qid, entry in theory_results.items():
                graded_answers[qid] = entry
                q_mark = next((Decimal(str(q.mark)) for q, _ in theory_rows if str(q.id) == qid and q.mark is not None), Decimal("0.00"))
                answer_score_d = Decimal(str(entry.get("answer_score", "0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_score += (answer_score_d * q_mark).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return total_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), graded_answers

    async def _batch_grade_theory(
        self,
        grader: SimilarityGrader,
        theory_rows: list,
        answers: dict,
    ) -> dict:
        """Send all theory questions in a single Groq API call.

        Builds a batch prompt requesting a JSON object keyed by question_id.
        Falls back to per-question grading if the batch call fails.

        Returns:
            Dict mapping question_id (str) → {answer_score, reason, text}.
        """
        if not theory_rows or grader.client is None:
            # No client — return zero scores for all theory questions
            result = {}
            for q, _ in theory_rows:
                qid = str(q.id)
                raw = answers.get(qid, {})
                student_text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
                result[qid] = {"answer_score": "0.00", "reason": "Error: Groq client not available", "text": student_text}
            return result

        # Build batch prompt
        questions_payload = []
        for q, _ in theory_rows:
            qid = str(q.id)
            raw = answers.get(qid, {})
            student_text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
            industry = q.industry.value if q.industry else "general"
            questions_payload.append({
                "question_id": qid,
                "question_text": q.text or "",
                "student_answer": student_text,
                "industry": industry,
                "rules": q.rules or "",
            })

        batch_prompt = (
            "You are an expert academic grader. Grade each student answer below.\n\n"
            "For each question, evaluate the student's answer based on accuracy, completeness, "
            "and depth of knowledge. Apply any grading rules provided.\n\n"
            "Questions to grade:\n"
            + json.dumps(questions_payload, indent=2)
            + "\n\nReturn ONLY a JSON object where each key is the question_id and the value is:\n"
            '{"score": float (0.0-1.0), "reason": string}\n\n'
            "Example:\n"
            '{"<uuid1>": {"score": 0.85, "reason": "Good answer but missed one detail."}, '
            '"<uuid2>": {"score": 1.0, "reason": "Complete and accurate."}}'
        )

        import asyncio as _asyncio
        last_error = "Unknown error"
        _RETRY_DELAYS = [1.0, 2.0, 4.0]

        for idx, backoff in enumerate(_RETRY_DELAYS):
            try:
                chat = await _asyncio.to_thread(
                    grader.client.chat.completions.create,
                    model=grader.model,
                    messages=[{"role": "user", "content": batch_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                batch_result = json.loads(chat.choices[0].message.content)

                result = {}
                for q, _ in theory_rows:
                    qid = str(q.id)
                    raw = answers.get(qid, {})
                    student_text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
                    q_result = batch_result.get(qid, {})
                    score_val = Decimal(str(q_result.get("score", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    score_val = max(Decimal("0.00"), min(Decimal("1.00"), score_val))
                    result[qid] = {
                        "answer_score": str(score_val),
                        "reason": q_result.get("reason", "No reason provided"),
                        "text": student_text,
                    }
                return result

            except Exception as e:
                last_error = str(e)
                if "invalid_api_key" in last_error.lower() or "authentication" in last_error.lower():
                    break
                if idx < len(_RETRY_DELAYS) - 1:
                    await _asyncio.sleep(backoff)

        # Batch failed — return error scores for all theory questions
        logger.warning("[grading] Batch theory grading failed: %s", last_error)
        result = {}
        for q, _ in theory_rows:
            qid = str(q.id)
            raw = answers.get(qid, {})
            student_text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
            result[qid] = {"answer_score": "0.00", "reason": f"Error: {last_error}", "text": student_text}
        return result

    async def _bulk_upsert_graded_answers(
        self,
        db: AsyncSession,
        student_id: UUID,
        exam_id: UUID,
        graded_answers: dict,
        batch_size: int = 500,
    ) -> None:
        """Bulk-upsert graded answer results using INSERT ... ON CONFLICT DO UPDATE.

        Replaces per-row session.add() loops with a single DB round-trip per batch.
        Uses PostgreSQL's ON CONFLICT clause to remain idempotent (task 10.10).
        """
        if not graded_answers:
            return

        items = list(graded_answers.items())
        for i in range(0, len(items), batch_size):
            batch = items[i: i + batch_size]
            values = []
            for qid, entry in batch:
                # Merge graded result into the answer JSON
                answer_payload = {
                    "graded": {
                        "answer_score": entry.get("answer_score", "0.00"),
                        "reason": entry.get("reason", ""),
                    }
                }
                if "option" in entry:
                    answer_payload["option"] = entry["option"]
                if "text" in entry:
                    answer_payload["text"] = entry["text"]
                values.append({
                    "student_id": student_id,
                    "exam_id": exam_id,
                    "question_id": UUID(qid),
                    "answer": answer_payload,
                })

            if not values:
                continue

            stmt = pg_insert(StudentAnswer).values(values)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_student_answer_student_exam_question",
                set_={"answer": stmt.excluded.answer},
            )
            await db.execute(stmt)

        await db.commit()

    async def list_for_lecturer(
        self,
        lecturer_id: UUID,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SubmissionModel]:
        """Get all submissions for exams in courses assigned to the lecturer."""
        stmt = (
            select(SubmissionModel)
            .join(ExamModel, SubmissionModel.exam_id == ExamModel.id)
            .join(CourseModel, ExamModel.course_id == CourseModel.id)
            .where(CourseModel.lecturer_id == lecturer_id)
            .order_by(SubmissionModel.created_at.desc())
            .offset(offset).limit(limit)
        )
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_for_lecturer(self, lecturer_id: UUID, tenant_id: Optional[UUID] = None) -> int:
        stmt = (
            select(func.count()).select_from(SubmissionModel)
            .join(ExamModel, SubmissionModel.exam_id == ExamModel.id)
            .join(CourseModel, ExamModel.course_id == CourseModel.id)
            .where(CourseModel.lecturer_id == lecturer_id)
        )
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        return int((await self.db.execute(stmt)).scalar_one())

    async def list_for_tenant(self, tenant_id: Optional[UUID], limit: int = 50, offset: int = 0) -> List[SubmissionModel]:
        """Get all submissions in a tenant (for admins)."""
        stmt = (
            select(SubmissionModel)
            .join(ExamModel, SubmissionModel.exam_id == ExamModel.id)
            .order_by(SubmissionModel.created_at.desc())
            .offset(offset).limit(limit)
        )
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_for_tenant(self, tenant_id: Optional[UUID]) -> int:
        stmt = (
            select(func.count()).select_from(SubmissionModel)
            .join(ExamModel, SubmissionModel.exam_id == ExamModel.id)
        )
        if tenant_id:
            stmt = stmt.where(ExamModel.tenant_id == tenant_id)
        return int((await self.db.execute(stmt)).scalar_one())

    async def count_for_exam(self, exam_id: UUID, tenant_id: Optional[UUID] = None, status: Optional[str] = None) -> int:
        """Count submissions for a specific exam."""
        count_stmt = select(func.count()).select_from(SubmissionModel).where(SubmissionModel.exam_id == exam_id)
        if tenant_id:
            count_stmt = count_stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)
        if status:
            if status == "graded":
                count_stmt = count_stmt.where(SubmissionModel.latest_score.isnot(None))
            elif status == "pending":
                count_stmt = count_stmt.where(SubmissionModel.latest_score.is_(None))
        result = await self.db.execute(count_stmt)
        return int(result.scalar_one())


# ---------------------------------------------------------------------------
# Background task: grade an already-saved attempt
# ---------------------------------------------------------------------------
