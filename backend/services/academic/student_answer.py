from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.student_answer import StudentAnswer as StudentAnswerModel


class StudentAnswerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, student_id: UUID, exam_id: UUID, question_id: UUID, answer: dict) -> StudentAnswerModel:
        stmt = select(StudentAnswerModel).where(
            StudentAnswerModel.student_id == student_id,
            StudentAnswerModel.exam_id == exam_id,
            StudentAnswerModel.question_id == question_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.answer = answer
            self.db.add(existing)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        sa = StudentAnswerModel(
            student_id=student_id,
            exam_id=exam_id,
            question_id=question_id,
            answer=answer,
        )
        self.db.add(sa)
        await self.db.commit()
        await self.db.refresh(sa)
        return sa

    async def list_for_student_exam(self, student_id: UUID, exam_id: UUID) -> List[StudentAnswerModel]:
        stmt = select(StudentAnswerModel).where(
            StudentAnswerModel.student_id == student_id,
            StudentAnswerModel.exam_id == exam_id,
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def answers_map_for_student_exam(self, student_id: UUID, exam_id: UUID) -> Dict[str, dict]:
        rows = await self.list_for_student_exam(student_id, exam_id)
        return {str(r.question_id): r.answer for r in rows}
