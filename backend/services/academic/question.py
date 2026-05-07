from __future__ import annotations

from typing import Optional, List, Any, Tuple
from uuid import UUID
import re
import json

from sqlalchemy import select, func, outerjoin, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.question import Question,  Answer, QuestionExams, Industry, AnswerEnum, QuestionType
from models.academic.exam import Exam
from models.academic.course import Course
from schemas.academic.question import QuestionCreate, QuestionUpdate

class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Note: normalization of options has been removed — options are expected
    # to already be provided in the canonical list-of-dicts format by callers.

    async def _refresh_with_relations(self, q: Question) -> Question:
        """Re-fetch a question with all relationships eagerly loaded."""
        stmt = select(Question).options(
            selectinload(Question.exams),
            selectinload(Question.answer),
        ).where(Question.id == q.id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, question_in: QuestionCreate, tenant_id: Optional[UUID] = None) -> Question:
        q = Question(
            number=question_in.number,
            text=question_in.text,
            images=question_in.images if getattr(question_in, "images", None) else None,
            industry=question_in.industry,
            parent_id=question_in.parent_id,
            tenant_id=tenant_id if tenant_id is not None else (question_in.tenant_id if getattr(question_in, "tenant_id", None) else None),
            qtype=question_in.qtype if getattr(question_in, "qtype", None) else QuestionType.THEORY.value,
            options=None,
            rules=getattr(question_in, "rules", None),
            mark=getattr(question_in, "mark", None),
            answer_id=question_in.answer_id if getattr(question_in, "answer_id", None) else None,
        )
        
        self.db.add(q)
        await self.db.commit()
        await self.db.refresh(q)
        
        # attach exams if provided (no tenant constraint on questions/answers)
        if question_in.exam_ids:
            stmt = select(Exam).options(
                selectinload(Exam.course).selectinload(Course.lecturer)
            ).where(Exam.id.in_(question_in.exam_ids))
            if tenant_id:
                stmt = stmt.where(Exam.tenant_id == tenant_id)
            res = await self.db.execute(stmt)
            exams = res.scalars().all()
            for ex in exams:
                # Check if a question with the same number and text already exists for this exam
                existing_stmt = (
                    select(Question)
                    .join(QuestionExams, Question.id == QuestionExams.question_id)
                    .where(
                        QuestionExams.exam_id == ex.id,
                        Question.number == question_in.number,
                        Question.text == question_in.text,
                    )
                )
                if tenant_id:
                    existing_stmt = existing_stmt.where(Question.tenant_id == tenant_id)
                existing_res = await self.db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    raise ValueError(f"Question with number '{question_in.number}' and same text already exists for exam '{ex.title}'")
                
                # Create association record
                assoc = QuestionExams(question_id=q.id, exam_id=ex.id)
                self.db.add(assoc)
            
            await self.db.commit()
            
            # Refresh and load the exams relationship
            await self.db.refresh(q, ["exams"])

        if q.qtype == QuestionType.MULTIPLE_CHOICE and getattr(question_in, "options", None):
            # Expect options to already be canonical list-of-dicts; store as-is
            q.options = question_in.options
            # Ensure any provided answer (either by value or id) is compatible with options
            valid_labels = {opt["label"] for opt in q.options}

            # If creator provided an `answer` value (label), link or create Answer record
            provided_answer = getattr(question_in, "answer", None)
            if provided_answer is not None:
                # extract enum value if needed, then normalize to lowercase
                label = (provided_answer.value if hasattr(provided_answer, "value") else str(provided_answer)).lower()
                if label not in valid_labels:
                    raise ValueError(f"Answer value '{label}' is not a valid option label for this question")
                # find existing Answer with this value
                stmt = select(Answer).where(Answer.value == label)
                res = await self.db.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    q.answer_id = existing.id
                else:
                    new_ans = Answer(value=label, answer_type="mcq")
                    self.db.add(new_ans)
                    await self.db.commit()
                    await self.db.refresh(new_ans)
                    q.answer_id = new_ans.id
            elif q.answer_id is not None:
                # validate provided answer_id exists and matches one of the option labels
                stmt = select(Answer).where(Answer.id == q.answer_id)
                res = await self.db.execute(stmt)
                a = res.scalar_one_or_none()
                if not a:
                    raise ValueError("Answer not found")
                if a.value not in valid_labels:
                    raise ValueError(f"Answer value '{a.value}' is not a valid option label for this question")
            else:
                # No answer provided — will be detected in background after creation
                pass
            self.db.add(q)
            await self.db.commit()
            await self.db.refresh(q)
        elif q.qtype == QuestionType.FILL_IN_BLANKS:
            # Handle FITB question creation
            if getattr(question_in, "options", None):
                # Store the blank positions as options (if provided)
                q.options = question_in.options
            
            # Handle FITB text answer
            fitb_answer = getattr(question_in, "answer", None)
            if fitb_answer is not None and isinstance(fitb_answer, str):
                # Create FITB answer record
                new_ans = Answer(
                    text_value=fitb_answer.strip(),
                    answer_type="fitb"
                )
                self.db.add(new_ans)
                await self.db.commit()
                await self.db.refresh(new_ans)
                q.answer_id = new_ans.id
                self.db.add(q)
                await self.db.commit()
                await self.db.refresh(q)
        return await self._refresh_with_relations(q)

    async def get(self, question_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[Question]:
        # Eager-load related exams and answer to avoid lazy-loading during serialization
        stmt = select(Question).options(
            selectinload(Question.exams),
            selectinload(Question.answer),
        ).where(Question.id == question_id)
        if tenant_id is not None:
            stmt = stmt.where(Question.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, question: Question, question_in: QuestionUpdate) -> Question:
        data = question_in.model_dump(exclude_unset=True)
        exam_ids = data.pop("exam_ids", None)
        answer_id = data.pop("answer_id", None)
        provided_answer = data.pop("answer", None)
        tenant_id = data.pop("tenant_id", None)
        qtype = data.pop("qtype", None)
        options = data.pop("options", None)
        pattern = re.compile(r"\[([^\]]+)\]\-([^\[]+)")
        for field, value in data.items():
            setattr(question, field, value)

        if exam_ids is not None:
            # Get the updated number and text (or current if not being updated)
            check_number = data.get("number", question.number)
            check_text = data.get("text", question.text)
            check_tenant_id = tenant_id if tenant_id is not None else question.tenant_id

            # replace exams relationship - but first check for duplicates
            stmt = select(Exam).options(
                selectinload(Exam.course).selectinload(Course.lecturer)
            ).where(Exam.id.in_(exam_ids))
            if check_tenant_id:
                stmt = stmt.where(Exam.tenant_id == check_tenant_id)
            res = await self.db.execute(stmt)
            exams = res.scalars().all()

            for ex in exams:
                # Check if another question with same number and text already exists for this exam
                existing_stmt = (
                    select(Question)
                    .join(QuestionExams, Question.id == QuestionExams.question_id)
                    .where(
                        QuestionExams.exam_id == ex.id,
                        Question.number == check_number,
                        Question.text == check_text,
                        Question.id != question.id,  # Exclude the current question being updated
                    )
                )
                if check_tenant_id:
                    existing_stmt = existing_stmt.where(Question.tenant_id == check_tenant_id)
                existing_res = await self.db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    raise ValueError(f"Question with number '{check_number}' and same text already exists for exam '{ex.title}'")
            
            question.exams[:] = exams

        if answer_id is not None:
            # validate answer exists
            if answer_id:
                stmt = select(Answer).where(Answer.id == answer_id)
                r = await self.db.execute(stmt)
                a = r.scalar_one_or_none()
                if not a:
                    raise ValueError("Answer not found")
            question.answer_id = answer_id

        if qtype is not None:
            # validate qtype/options combination (options are stored as a single string)
            if qtype == QuestionType.MULTIPLE_CHOICE or (isinstance(qtype, str) and qtype == QuestionType.MULTIPLE_CHOICE.value):
                question.options = options
            elif qtype == QuestionType.FILL_IN_BLANKS or (isinstance(qtype, str) and qtype == QuestionType.FILL_IN_BLANKS.value):
                # FITB: store options as blank positions if provided
                question.options = options
            else:
                # theory
                question.options = None
            # Normalize stored qtype to enum where possible
            try:
                question.qtype = QuestionType(qtype) if not isinstance(qtype, QuestionType) else qtype
            except Exception:
                question.qtype = QuestionType(qtype) if isinstance(qtype, str) else qtype

        if options is not None and qtype is None:
            # options provided without changing qtype: ensure current qtype allows options
            if question.qtype in (QuestionType.MULTIPLE_CHOICE, QuestionType.FILL_IN_BLANKS):
                question.options = options

        # Handle provided answer on update: find/create Answer and link it
        if provided_answer is not None:
            if question.qtype == QuestionType.MULTIPLE_CHOICE:
                # must have options available for multiple_choice
                if not getattr(question, "options", None):
                    raise ValueError("Cannot set an answer when question has no options")
                valid_labels = {opt["label"] for opt in question.options}
                # Extract just the value from AnswerEnum string like 'answerenum.d' -> 'd'
                label = str(provided_answer).lower().strip()
                if label.startswith('answerenum.'):
                    label = label.split('.')[-1]
                if label not in valid_labels:
                    raise ValueError(f"Answer value '{label}' is not a valid option label for this question")
                # find or create MCQ Answer
                stmt = select(Answer).where(Answer.value == label)
                res = await self.db.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    question.answer_id = existing.id
                else:
                    new_ans = Answer(value=label, answer_type="mcq")
                    self.db.add(new_ans)
                    await self.db.commit()
                    await self.db.refresh(new_ans)
                    question.answer_id = new_ans.id
            elif question.qtype == QuestionType.FILL_IN_BLANKS:
                # For FITB: provided_answer should be the text answer
                if isinstance(provided_answer, str):
                    new_ans = Answer(
                        text_value=provided_answer.strip(),
                        answer_type="fitb"
                    )
                    self.db.add(new_ans)
                    await self.db.commit()
                    await self.db.refresh(new_ans)
                    question.answer_id = new_ans.id
                else:
                    raise ValueError("FITB answer must be a text string")
            else:
                raise ValueError("Cannot set an answer for theory question")

        if tenant_id is not None:
            question.tenant_id = tenant_id

        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return await self._refresh_with_relations(question)
    
    async def delete(self, question: Question) -> None:
        # Clear exam associations first to avoid FK constraint errors
        question.exams.clear()
        await self.db.flush()
        await self.db.delete(question)
        await self.db.commit()

    async def list(self, exam_id: Optional[UUID] = None) -> List[Question]:
        """List all questions (no pagination - load all at once).

        Returns:
            List of questions
        """
        stmt = select(Question).options(
            selectinload(Question.exams),
            selectinload(Question.answer),
        ).outerjoin(QuestionExams, Question.id == QuestionExams.question_id)

        # Add exam_id filter if provided - use EXISTS subquery for better performance
        if exam_id:
            exam_filter = exists(
                select(QuestionExams.question_id).where(
                    QuestionExams.exam_id == exam_id,
                    QuestionExams.question_id == Question.id
                )
            ).correlate(QuestionExams)
            stmt = stmt.where(exam_filter)

        stmt = stmt.order_by(Question.qtype.asc(), Question.number.asc())
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        return list(items)

    async def count(self, exam_id: Optional[UUID] = None) -> int:
        stmt = select(func.count()).select_from(Question)
        
        # Add exam filter if provided
        if exam_id:
            stmt = stmt.where(
                exists(
                    select(QuestionExams.question_id).where(
                        QuestionExams.exam_id == exam_id,
                        QuestionExams.question_id == Question.id
                    )
                ).correlate(QuestionExams)
            )
        
        res = await self.db.execute(stmt)
        return int(res.scalar_one())
