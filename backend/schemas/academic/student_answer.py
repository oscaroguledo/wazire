from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime


class StudentAnswerCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    exam_id: UUID
    question_id: UUID
    answer: Dict[str, Any]


class StudentAnswerRead(StudentAnswerCreate):
    id: UUID
    student_id: UUID
    last_saved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
