from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnswerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    value: Optional[str] = None
    text_value: Optional[str] = None
    acceptable_variations: Optional[List[str]] = None
    answer_type: Literal["mcq", "fitb"] = "mcq"


class AnswerCreate(AnswerBase):
    exam_id: UUID
    question_id: UUID


class AnswerUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    value: Optional[str] = None
    text_value: Optional[str] = None
    acceptable_variations: Optional[List[str]] = None
    answer_type: Optional[Literal["mcq", "fitb"]] = None


class AnswerRead(AnswerBase):
    id: UUID
    question_ids: Optional[List[UUID]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
