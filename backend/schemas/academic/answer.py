from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.utils.response import ResponseModel as _BaseResponseModel
from core.dependencies.pagination import PaginationResponse


KeysetMeta = PaginationResponse


class AnswerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    value: Optional[str] = None  # MCQ answer (a-z)
    text_value: Optional[str] = None  # FITB answer (text)
    acceptable_variations: Optional[List[str]] = None  # FITB: acceptable variations
    answer_type: Literal["mcq", "fitb"] = "mcq"


class AnswerCreate(AnswerBase):
    """Create an answer record.
    
    For MCQ: provide `value` (e.g., 'a', 'b')
    For FITB: provide `text_value` and optionally `acceptable_variations`
    """
    pass


class AnswerUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    value: Optional[str] = None
    text_value: Optional[str] = None
    acceptable_variations: Optional[List[str]] = None
    answer_type: Optional[Literal["mcq", "fitb"]] = None


class AnswerRead(AnswerBase):
    id: UUID
    question_ids: Optional[list[UUID]] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    


# Response envelopes
class AnswerResponse(_BaseResponseModel):
    data: Optional[AnswerRead] = None


class AnswerListResponse(_BaseResponseModel):
    data: Optional[List[AnswerRead]] = None
    meta: Optional[PaginationResponse] = None


class UpsertPayload(BaseModel):
    exam_id: UUID
    question_id: UUID
    answer: Dict[str, Any]