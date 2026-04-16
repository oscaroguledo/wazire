from __future__ import annotations

import base64
import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, exists
from sqlalchemy.ext.asyncio import AsyncSession


from services.analytics.dashboard import refresh_dashboard_bg, refresh_multiple_dashboards_bg

from models.academic.submission import Submission as SubmissionModel, SubmissionAttempt as SubmissionAttemptModel
from models.academic.exam import Exam as ExamModel
from models.academic.course import Course as CourseModel
from models.academic.question import Question as QuestionModel, Answer as AnswerModel, QuestionExams
from models.academic.student_answer import StudentAnswer as StudentAnswerModel
from services.academic.student_answer import StudentAnswerService
from services.engine.similarity_grader import SimilarityGrader
from models.account.users import User as UserModel


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
        stmt = select(ExamModel).where(ExamModel.id == exam_id)
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
                attempts_count=0,
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
        if exam.max_attempts is not None and submission.attempts_count >= exam.max_attempts:
            raise ValueError(f"Maximum attempts ({exam.max_attempts}) reached")

        attempt_number = submission.attempts_count + 1
        # Save attempt immediately — answers will be stored separately in StudentAnswer rows
        attempt = SubmissionAttemptModel(
            submission_id=submission.id,
            attempt_number=attempt_number,
            score=None,
            scan_pages=scan_pages or [],
            graded_at=None,
        )
        self.db.add(attempt)
        submission.attempts_count = attempt_number
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

    async def get(self, submission_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[SubmissionModel]:
        stmt = select(SubmissionModel).where(SubmissionModel.id == submission_id)
        if tenant_id:
            stmt = stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_my_submission(self, student_id: UUID, exam_id: UUID) -> Optional[SubmissionModel]:
        return await self._get_by_student_exam(student_id, exam_id)

    async def get_all_my_submissions(self, student_id: UUID, tenant_id: Optional[UUID] = None) -> List[SubmissionModel]:
        """Get all submissions for a specific student across all exams."""
        stmt = select(SubmissionModel).where(SubmissionModel.student_id == student_id)
        if tenant_id:
            stmt = stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)
        stmt = stmt.order_by(SubmissionModel.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_for_exam(
        self,
        exam_id: UUID,
        tenant_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SubmissionModel]:
        """List submissions for an exam with limit/offset pagination."""
        stmt = select(SubmissionModel).where(
            SubmissionModel.exam_id == exam_id
        ).order_by(SubmissionModel.created_at.desc()).offset(offset).limit(limit)

        if tenant_id:
            stmt = stmt.join(ExamModel, ExamModel.id == SubmissionModel.exam_id).where(ExamModel.tenant_id == tenant_id)
        
        if status:
            if status == "graded":
                stmt = stmt.where(SubmissionModel.latest_score.isnot(None))
            elif status == "pending":
                stmt = stmt.where(SubmissionModel.latest_score.is_(None))

        items = (await self.db.execute(stmt)).scalars().all()
        return list(items)

    async def list_students_with_submissions(
        self,
        exam_id: UUID,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """Return each student with their submission summary for a specific exam."""
        # Verify the exam exists and belongs to the tenant
        exam_stmt = select(ExamModel).where(ExamModel.id == exam_id)
        if tenant_id:
            exam_stmt = exam_stmt.where(ExamModel.tenant_id == tenant_id)
        exam = (await self.db.execute(exam_stmt)).scalar_one_or_none()
        if not exam:
            raise ValueError("Exam not found for this tenant")

        stmt = (
            select(UserModel, SubmissionModel)
            .join(SubmissionModel, SubmissionModel.student_id == UserModel.id)
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
            attempts = (await self.db.execute(
                select(SubmissionAttemptModel)
                .where(SubmissionAttemptModel.submission_id == submission.id)
                .order_by(SubmissionAttemptModel.attempt_number)
            )).scalars().all()

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
                    "attempts_count": submission.attempts_count,
                    "max_attempts": submission.max_attempts,
                    "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
                    "created_at": submission.created_at.isoformat() if submission.created_at else None,
                },
                "attempts": [
                    {
                        "id": str(a.id),
                        "attempt_number": a.attempt_number,
                        "score": str(a.score) if a.score is not None else None,
                        # answers removed: stored separately in student_answers
                        "scan_pages": a.scan_pages or [],
                        "graded_at": a.graded_at.isoformat() if a.graded_at else None,
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
                attempts_count=0,
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
            select(QuestionModel, AnswerModel)
            .outerjoin(AnswerModel, AnswerModel.id == QuestionModel.answer_id)
            .where(
                exists().where(
                    QuestionExams.question_id == QuestionModel.id,
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
                student_option = str(raw) if q.qtype == "multiple_choice" else ""
                student_text = str(raw) if q.qtype in ["theory", "fill_in_blanks"] else ""

            student_answer = student_option if q.qtype == "multiple_choice" else student_text
            industry = q.industry.value if q.industry else "general"
            mark = Decimal(str(q.mark)) if q.mark is not None else Decimal("0.00")

            grade_kwargs = dict(
                question_type=q.qtype,
                industry=industry,
                student_answer=student_answer,
            )
            if q.qtype == "multiple_choice":
                grade_kwargs["mcq_answer"] = str(a.value).strip() if a and a.value else None
            elif q.qtype == "fill_in_blanks":
                grade_kwargs["fitb_answer"] = a.text_value.strip() if a and a.text_value else None
                grade_kwargs["fitb_variations"] = a.acceptable_variations if a and a.acceptable_variations else None
            else:
                grade_kwargs["question_text"] = q.text
                grade_kwargs["rules"] = q.rules

            answer_score, reason = grader.grade(**grade_kwargs)

            answer_score_d = Decimal(str(answer_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            question_score = (answer_score_d * mark).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_score += question_score

            entry: dict = {"answer_score": str(answer_score_d), "reason": reason}
            if q.qtype == "multiple_choice":
                entry["option"] = student_option
            elif q.qtype == "fill_in_blanks":
                entry["text"] = student_text
            else:
                entry["text"] = student_text
            graded_answers[qid] = entry

        return total_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), graded_answers

    # ------------------------------------------------------------------
    # Background helpers (run by Celery tasks)
    # ------------------------------------------------------------------

    async def grade_attempt_background(self, attempt_id: str, exam_id: str) -> None:
        """Grade an attempt in the background (used by Celery tasks)."""
        from core.database import get_session_factory

        AsyncSessionLocal = get_session_factory()
        async with AsyncSessionLocal() as db:
            attempt = (await db.execute(
                select(SubmissionAttemptModel).where(
                    SubmissionAttemptModel.id == UUID(attempt_id)
                )
            )).scalar_one_or_none()

            if not attempt:
                print(f"[grading] Attempt {attempt_id} not found")
                return

            service = SubmissionService(db)
            # If attempt.answers are empty (we store answers in StudentAnswer rows),
            # fetch student answers for grading
            submission = (await db.execute(
                select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id)
            )).scalar_one_or_none()

            if submission is None:
                print(f"[grading] Submission for attempt {attempt_id} not found")
                return

            student_id = submission.student_id
            # Use StudentAnswerService to gather answers
            sa_service = StudentAnswerService(db)
            answers_map = await sa_service.answers_map_for_student_exam(student_id, UUID(exam_id))

            score, graded_answers = await service._grade_answers(UUID(exam_id), answers_map)

            attempt.score = score
            attempt.graded_at = datetime.now(timezone.utc)
            db.add(attempt)

            submission = (await db.execute(
                select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id)
            )).scalar_one_or_none()
            if submission:
                submission.latest_score = score
                submission.graded_at = datetime.now(timezone.utc)
                db.add(submission)

            await db.commit()
            print(f"[grading] Graded attempt {attempt_id} with score {score}")
            
            # Refresh dashboards after grading
            if submission:
                await refresh_dashboard_bg(submission.student_id)
                # Get exam to find lecturer for dashboard refresh
                exam_result = await db.execute(select(ExamModel).where(ExamModel.id == UUID(exam_id)))
                exam = exam_result.scalar_one_or_none()
                if exam and exam.course_id:
                    course_result = await db.execute(select(CourseModel).where(CourseModel.id == exam.course_id))
                    course = course_result.scalar_one_or_none()
                    if course and course.lecturer_id:
                        await refresh_dashboard_bg(course.lecturer_id)

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

async def grade_attempt_bg(
    attempt_id: str,
    exam_id: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> None:
    """Re-grade a submission attempt in the background and persist the result.

    Called after the attempt row is created with score=None so the HTTP
    response returns immediately. Grading runs here, then the attempt and
    parent submission are updated.
    """
    attempt = (await db.execute(
        select(SubmissionAttemptModel).where(SubmissionAttemptModel.id == _uuid.UUID(attempt_id))
    )).scalar_one_or_none()
    if not attempt:
        return

    service = SubmissionService(db)
    # Gather answers from StudentAnswer rows for grading
    from services.academic.student_answer import StudentAnswerService
    sa_service = StudentAnswerService(db)
    answers_map = await sa_service.answers_map_for_student_exam((await db.execute(select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id))).scalar_one().student_id, _uuid.UUID(exam_id))
    score, graded_answers = await service._grade_answers(_uuid.UUID(exam_id), answers_map)

    attempt.score = score
    attempt.graded_at = datetime.now(timezone.utc)
    db.add(attempt)

    # Update parent submission
    submission = (await db.execute(
        select(SubmissionModel).where(SubmissionModel.id == attempt.submission_id)
    )).scalar_one_or_none()
    if submission:
        submission.latest_score = score
        submission.graded_at = datetime.now(timezone.utc)
        db.add(submission)

    await db.commit()
    
    # Refresh dashboards after grading
    if submission:
        # Get exam to find lecturer for dashboard refresh
        exam_result = await db.execute(select(ExamModel).where(ExamModel.id == _uuid.UUID(exam_id)))
        exam = exam_result.scalar_one_or_none()
        user_ids_to_refresh = [str(submission.student_id)]
        if exam and exam.course_id:
            course_result = await db.execute(select(CourseModel).where(CourseModel.id == exam.course_id))
            course = course_result.scalar_one_or_none()
            if course and course.lecturer_id:
                user_ids_to_refresh.append(str(course.lecturer_id))
        await refresh_multiple_dashboards_bg(user_ids_to_refresh)

    # WebSocket notification — commented out until WS is enabled
    # from core.websockets import notify
    # await notify(user_id, {"job_id": attempt_id, "status": "done", "score": str(score) if score is not None else None})
