from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.student_answer import StudentAnswer


class StudentAnswerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, student_id: UUID, exam_id: UUID, question_id: UUID, answer: dict) -> StudentAnswer:
        """Atomically insert or update a student answer using ON CONFLICT DO UPDATE.

        Uses PostgreSQL's INSERT ... ON CONFLICT (student_id, exam_id, question_id)
        DO UPDATE SET answer=EXCLUDED.answer, updated_at=now() to avoid race conditions
        that could produce duplicate rows with a SELECT+INSERT pattern.
        """
        stmt = (
            pg_insert(StudentAnswer)
            .values(
                student_id=student_id,
                exam_id=exam_id,
                question_id=question_id,
                answer=answer,
                tenant_id=None,  # will be set by caller if needed; nullable
            )
            .on_conflict_do_update(
                constraint="uq_student_answer_student_exam_question",
                set_={
                    "answer": answer,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            .returning(StudentAnswer)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one()
        return row

    async def list(self, student_id: UUID, exam_id: UUID) -> List[StudentAnswer]:
        stmt = select(StudentAnswer).where(
            StudentAnswer.student_id == student_id,
            StudentAnswer.exam_id == exam_id,
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def answers_map_for_student_exam(self, student_id: UUID, exam_id: UUID) -> Dict[str, dict]:
        rows = await self.list(student_id, exam_id)
        return {str(r.question_id): r.answer for r in rows}
