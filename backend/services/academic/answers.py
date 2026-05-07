from __future__ import annotations

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.academic.question import Answer as AnswerModel
from schemas.academic.answer import AnswerCreate, AnswerUpdate


class AnswerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, answer_in: AnswerCreate) -> AnswerModel:
        """Create an answer record.
        
        For MCQ: value field is required (a-z)
        For FITB: text_value field is required
        """
        answer = AnswerModel(
            value=answer_in.value,
            text_value=answer_in.text_value,
            acceptable_variations=answer_in.acceptable_variations,
            answer_type=answer_in.answer_type or "mcq"
        )
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def get(self, answer_id: UUID) -> Optional[AnswerModel]:
        stmt = select(AnswerModel).where(AnswerModel.id == answer_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> Tuple[List[AnswerModel], int]:
        """List answers with limit/offset pagination."""
        stmt = select(AnswerModel).order_by(AnswerModel.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        items = res.scalars().all()
        
        # Get total count
        count_stmt = select(func.count()).select_from(AnswerModel)
        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        return list(items), total

    async def update(self, answer: AnswerModel, answer_in: AnswerUpdate) -> AnswerModel:
        data = answer_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(answer, field, value)
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def delete(self, answer: AnswerModel) -> None:
        await self.db.delete(answer)
        await self.db.commit()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(AnswerModel)
        res = await self.db.execute(stmt)
        return int(res.scalar_one())
