from __future__ import annotations

from typing import Optional, List, Any, Tuple
from uuid import UUID
import re
import json

from sqlalchemy import select, func, outerjoin, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.question import Question as QuestionModel, Answer as AnswerModel, QuestionExams, Industry, AnswerEnum
from models.academic.exam import Exam as ExamModel
from schemas.academic.question import QuestionCreate, QuestionUpdate
from services.engine.exam_extractor import ExamParser
from core.websockets import notify_exam_update

class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _normalize_options(self, opts: Any) -> str:
        """Accept many input shapes for `options` and return canonical
        storage as a list of dicts: [{"label":"a","text":"Option A"}, ...].

        Supported input types:
        - already-formatted labeled string: "[a]-Option A [b]-Option B"
        - JSON string representing list or dict
        - list of strings -> labels will be 1-based numbers
        - list of dicts with `label` and `text`
        - dict mapping label->text
        Raises ValueError on invalid/empty input.
        """
        if opts is None:
            return None
        pattern = re.compile(r"\[([^\]]+)\]\-([^\[]+)")

        # If it's a string, try regex labeled format first, else try JSON parsing
        if isinstance(opts, str):
            if pattern.search(opts):
                # parse labeled string into list of dicts
                matches = pattern.findall(opts)
                return [{"label": m[0].strip(), "text": m[1].strip()} for m in matches]
            try:
                parsed = json.loads(opts)
            except Exception:
                raise ValueError("Options string is not in the expected labeled format or valid JSON")
            opts = parsed

        # Now opts is list or dict
        if isinstance(opts, dict):
            # dict mapping label->text
            items = [{"label": str(k), "text": str(v).strip()} for k, v in opts.items()]
        elif isinstance(opts, list):
            items = []
            for i, v in enumerate(opts, start=1):
                if isinstance(v, str):
                    items.append({"label": str(i), "text": v})
                elif isinstance(v, dict):
                    label = v.get("label") or str(i)
                    text = v.get("text") or v.get("value") or None
                    if text is None:
                        raise ValueError("Option dicts must include 'text' or 'value'")
                    items.append({"label": str(label), "text": str(text).strip()})
                else:
                    raise ValueError("Unsupported option list item type; must be string or dict")
        else:
            raise ValueError("Unsupported options type; must be labeled string, JSON string, list, or dict")

        if not items:
            raise ValueError("Options cannot be empty for multiple_choice questions")

        # Validate text is non-empty and labels conform to AnswerEnum
        valid_labels = {v.value for v in AnswerModel.__dict__.get('AnswerEnum', [])} if False else None
        # Use models.academic.question.AnswerEnum
        try:
            valid_labels = {m.value for m in AnswerEnum}
        except Exception:
            valid_labels = {chr(c) for c in range(ord('a'), ord('z')+1)}

        normalized = []
        for it in items:
            lbl = str(it.get("label")).strip()
            txt = str(it.get("text")).strip()
            if not txt:
                raise ValueError("Option text cannot be empty")
            # normalize label to lowercase and validate
            lbl_norm = lbl.lower()
            if lbl_norm not in valid_labels:
                raise ValueError(f"Invalid option label '{lbl}'; must be one of {sorted(valid_labels)}")
            normalized.append({"label": lbl_norm, "text": txt})

        return normalized

    async def _refresh_with_relations(self, q: QuestionModel) -> QuestionModel:
        """Re-fetch a question with all relationships eagerly loaded."""
        stmt = select(QuestionModel).options(
            selectinload(QuestionModel.exams),
            selectinload(QuestionModel.answer),
        ).where(QuestionModel.id == q.id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, question_in: QuestionCreate, tenant_id: Optional[UUID] = None) -> QuestionModel:
        q = QuestionModel(
            number=question_in.number,
            text=question_in.text,
            images=question_in.images if getattr(question_in, "images", None) else None,
            industry=question_in.industry,
            parent_id=question_in.parent_id,
            tenant_id=tenant_id if tenant_id is not None else (question_in.tenant_id if getattr(question_in, "tenant_id", None) else None),
            qtype=question_in.qtype if getattr(question_in, "qtype", None) else "theory",
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
            stmt = select(ExamModel).where(ExamModel.id.in_(question_in.exam_ids))
            if tenant_id:
                stmt = stmt.where(ExamModel.tenant_id == tenant_id)
            res = await self.db.execute(stmt)
            exams = res.scalars().all()
            for ex in exams:
                # Check if a question with the same number and text already exists for this exam
                existing_stmt = (
                    select(QuestionModel)
                    .join(QuestionExams, QuestionModel.id == QuestionExams.question_id)
                    .where(
                        QuestionExams.exam_id == ex.id,
                        QuestionModel.number == question_in.number,
                        QuestionModel.text == question_in.text,
                    )
                )
                if tenant_id:
                    existing_stmt = existing_stmt.where(QuestionModel.tenant_id == tenant_id)
                existing_res = await self.db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    raise ValueError(f"Question with number '{question_in.number}' and same text already exists for exam '{ex.title}'")
                
                # Create association record
                assoc = QuestionExams(question_id=q.id, exam_id=ex.id)
                self.db.add(assoc)
            
            await self.db.commit()
            
            # Refresh and load the exams relationship
            await self.db.refresh(q, ["exams"])

        if q.qtype == "multiple_choice" and getattr(question_in, "options", None):
            # Normalize options to canonical list-of-dicts and store
            q.options = self._normalize_options(question_in.options)
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
                stmt = select(AnswerModel).where(AnswerModel.value == label)
                res = await self.db.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    q.answer_id = existing.id
                else:
                    new_ans = AnswerModel(value=label, answer_type="mcq")
                    self.db.add(new_ans)
                    await self.db.commit()
                    await self.db.refresh(new_ans)
                    q.answer_id = new_ans.id
            elif q.answer_id is not None:
                # validate provided answer_id exists and matches one of the option labels
                stmt = select(AnswerModel).where(AnswerModel.id == q.answer_id)
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
        elif q.qtype == "fill_in_blanks":
            # Handle FITB question creation
            if getattr(question_in, "options", None):
                # Store the blank positions as options (if provided)
                q.options = question_in.options
            
            # Handle FITB text answer
            fitb_answer = getattr(question_in, "answer", None)
            if fitb_answer is not None and isinstance(fitb_answer, str):
                # Create FITB answer record
                new_ans = AnswerModel(
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

    async def get(self, question_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[QuestionModel]:
        # Eager-load related exams and answer to avoid lazy-loading during serialization
        stmt = select(QuestionModel).options(
            selectinload(QuestionModel.exams),
            selectinload(QuestionModel.answer),
        ).where(QuestionModel.id == question_id)
        if tenant_id is not None:
            stmt = stmt.where(QuestionModel.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, question: QuestionModel, question_in: QuestionUpdate) -> QuestionModel:
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
            stmt = select(ExamModel).where(ExamModel.id.in_(exam_ids))
            if check_tenant_id:
                stmt = stmt.where(ExamModel.tenant_id == check_tenant_id)
            res = await self.db.execute(stmt)
            exams = res.scalars().all()

            for ex in exams:
                # Check if another question with same number and text already exists for this exam
                existing_stmt = (
                    select(QuestionModel)
                    .join(QuestionExams, QuestionModel.id == QuestionExams.question_id)
                    .where(
                        QuestionExams.exam_id == ex.id,
                        QuestionModel.number == check_number,
                        QuestionModel.text == check_text,
                        QuestionModel.id != question.id,  # Exclude the current question being updated
                    )
                )
                if check_tenant_id:
                    existing_stmt = existing_stmt.where(QuestionModel.tenant_id == check_tenant_id)
                existing_res = await self.db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    raise ValueError(f"Question with number '{check_number}' and same text already exists for exam '{ex.title}'")
            
            question.exams[:] = exams

        if answer_id is not None:
            # validate answer exists
            if answer_id:
                stmt = select(AnswerModel).where(AnswerModel.id == answer_id)
                r = await self.db.execute(stmt)
                a = r.scalar_one_or_none()
                if not a:
                    raise ValueError("Answer not found")
            question.answer_id = answer_id

        if qtype is not None:
            # validate qtype/options combination (options are stored as a single string)
            if qtype == "multiple_choice":
                question.options = self._normalize_options(options)
            elif qtype == "fill_in_blanks":
                # FITB: store options as blank positions if provided
                question.options = options
            else:
                # theory
                question.options = None
            question.qtype = qtype

        if options is not None and qtype is None:
            # options provided without changing qtype: ensure current qtype allows options
            if question.qtype in ["multiple_choice", "fill_in_blanks"]:
                if question.qtype == "multiple_choice":
                    question.options = self._normalize_options(options)
                else:
                    question.options = options

        # Handle provided answer on update: find/create Answer and link it
        if provided_answer is not None:
            if question.qtype == "multiple_choice":
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
                stmt = select(AnswerModel).where(AnswerModel.value == label)
                res = await self.db.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    question.answer_id = existing.id
                else:
                    new_ans = AnswerModel(value=label, answer_type="mcq")
                    self.db.add(new_ans)
                    await self.db.commit()
                    await self.db.refresh(new_ans)
                    question.answer_id = new_ans.id
            elif question.qtype == "fill_in_blanks":
                # For FITB: provided_answer should be the text answer
                if isinstance(provided_answer, str):
                    new_ans = AnswerModel(
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

    async def list_for_exam(self, exam_id: UUID) -> List[QuestionModel]:
        """List all questions for a specific exam without pagination."""
        stmt = select(QuestionModel).options(
            selectinload(QuestionModel.exams),
            selectinload(QuestionModel.answer),
        ).outerjoin(QuestionExams, QuestionModel.id == QuestionExams.question_id)
        
        # Add exam_id filter using EXISTS subquery
        exam_filter = exists(
            select(QuestionExams.question_id).where(
                QuestionExams.exam_id == exam_id,
                QuestionExams.question_id == QuestionModel.id
            )
        ).correlate(QuestionExams)
        stmt = stmt.where(exam_filter)
        
        # Order by number
        stmt = stmt.order_by(QuestionModel.number.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete(self, question: QuestionModel) -> None:
        # Clear exam associations first to avoid FK constraint errors
        question.exams.clear()
        await self.db.flush()
        await self.db.delete(question)
        await self.db.commit()

    async def list(self, exam_id: Optional[UUID] = None) -> List[QuestionModel]:
        """List all questions (no pagination - load all at once).

        Returns:
            List of questions
        """
        stmt = select(QuestionModel).options(
            selectinload(QuestionModel.exams),
            selectinload(QuestionModel.answer),
        ).outerjoin(QuestionExams, QuestionModel.id == QuestionExams.question_id)

        # Add exam_id filter if provided - use EXISTS subquery for better performance
        if exam_id:
            exam_filter = exists(
                select(QuestionExams.question_id).where(
                    QuestionExams.exam_id == exam_id,
                    QuestionExams.question_id == QuestionModel.id
                )
            ).correlate(QuestionExams)
            stmt = stmt.where(exam_filter)

        stmt = stmt.order_by(QuestionModel.qtype.asc(), QuestionModel.number.asc())
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        return list(items)

    async def count(self, exam_id: Optional[UUID] = None) -> int:
        stmt = select(func.count()).select_from(QuestionModel)
        
        # Add exam filter if provided
        if exam_id:
            stmt = stmt.where(
                exists(
                    select(QuestionExams.question_id).where(
                        QuestionExams.exam_id == exam_id,
                        QuestionExams.question_id == QuestionModel.id
                    )
                ).correlate(QuestionExams)
            )
        
        res = await self.db.execute(stmt)
        return int(res.scalar_one())

    # ---------------------------------------------------------------------------
    # Background helpers (run by Celery tasks)
    # ---------------------------------------------------------------------------

    async def detect_answer_background(self, question_id: str) -> None:
        """Run AI answer detection for an MCQ question in the background."""
        from services.engine.answer_grader import QuestionAnswerer
        from core.database import get_session_factory

        AsyncSessionLocal = get_session_factory()
        async with AsyncSessionLocal() as db:
            q = (await db.execute(
                select(QuestionModel).where(QuestionModel.id == UUID(question_id))
            )).scalar_one_or_none()
            if not q or q.qtype != "multiple_choice" or q.answer_id is not None:
                print(f"[question] Answer detection skipped for question {question_id}")
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
                print(f"[question] Answer detection failed for question {question_id}")
                return

            graded_label = results[0].get("answer", "").lower().strip()
            valid_labels = {opt["label"] for opt in (q.options or [])}
            if graded_label not in valid_labels:
                print(f"[question] Invalid answer '{graded_label}' for question {question_id}")
                return

            existing = (await db.execute(
                select(AnswerModel).where(AnswerModel.value == graded_label)
            )).scalar_one_or_none()

            if existing:
                q.answer_id = existing.id
            else:
                new_ans = AnswerModel(value=graded_label)
                db.add(new_ans)
                await db.flush()
                q.answer_id = new_ans.id

            db.add(q)
            await db.commit()
            print(f"[question] Answer detected for question {question_id}: {graded_label}")

    async def parse_and_create_background(
        self,
        pages: List[str],
        industry: str,
        exam_id: str,
        mark_per_question: Optional[float],
        tenant_id: Optional[UUID],
    ) -> None:
        """Parse exam paper images and bulk-create questions in the background."""

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

        # Notify start (commented out - only send completion)
        # await notify_exam_update(exam_id, "extraction_started", {
        #     "total_questions": total,
        #     "processed": 0,
        #     "created": 0
        # })

        AsyncSessionLocal = get_session_factory()
        async with AsyncSessionLocal() as db:
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
                    
                    # Notify progress for each question created (commented out - only send completion)
                    # await notify_exam_update(exam_id, "question_created", {
                    #     "question_id": str(q.id),
                    #     "number": q.number,
                    #     "qtype": q.qtype,
                    #     "progress": {
                    #         "total": total,
                    #         "current": idx + 1,
                    #         "created": len(created),
                    #         "errors": len(errors)
                    #     }
                    # })
                except Exception as e:
                    errors.append({"number": raw.get("number"), "error": str(e)})

        # Notify completion
        await notify_exam_update(exam_id, "extraction_complete", {
            "total": total,
            "created": len(created),
            "errors": len(errors),
            "error_details": errors if errors else None
        })

        print(f"[question] Paper parsing complete: {len(created)} created, {len(errors)} errors for exam {exam_id}")
        if errors:
            print(f"[question] Errors: {errors}")
