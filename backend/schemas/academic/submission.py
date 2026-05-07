from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmissionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    exam_id: UUID
    student_id: Optional[UUID] = None
    course_id: Optional[UUID] = None


class SubmissionCreate(SubmissionBase):
    max_attempts: Optional[int] = None


class SubmissionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score: Optional[Decimal] = None
    status: Optional[str] = None


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    exam: Dict[str, Any]
    course_id: Optional[UUID] = None
    latest_score: Optional[Decimal] = None
    attempts_count: int
    status: str = "pending"
    graded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    attempts: List["SubmissionAttemptRead"] = []


class SubmissionAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    submission_id: UUID
    attempt_number: int
    score: Optional[Decimal] = None
    scan_pages: Optional[List[str]] = None
    graded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SubmissionDelete(BaseModel):
    id: UUID


class ExamSubmit(BaseModel):
    """Request body for submitting an exam."""
    model_config = ConfigDict(from_attributes=True)
    exam_id: UUID
    answers: Optional[List[Dict[str, Any]]] = None


class ExamSubmitResponse(BaseModel):
    """Response after submitting an exam."""
    model_config = ConfigDict(from_attributes=True)
    submission_id: UUID
    status: str
    message: str
    submitted_at: Optional[datetime] = None
