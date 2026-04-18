from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmissionAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    submission_id: UUID
    attempt_number: int
    # answers removed: per-question answers are stored in StudentAnswer table
    score: Optional[Decimal]   # total of (answer_score * mark) across all questions
    scan_pages: Optional[List[str]] = None  # storage URLs for paper submissions
    graded_at: Optional[datetime]
    created_at: Optional[datetime]


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    exam: Dict[str, Any]
    course_id: Optional[UUID] = None
    latest_score: Optional[Decimal]
    attempts_count: int
    # in_progress_answers removed: drafts are stored in student_answers table
    status: str = "pending"  # Computed: pending, submitted, graded
    graded_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SubmissionWithAttemptsRead(SubmissionRead):
    """Submission + all its attempts — returned to the student viewing their own work."""
    attempts: List[SubmissionAttemptRead] = []


class ExamSubmit(BaseModel):
    """Payload to submit an exam attempt."""
    model_config = ConfigDict(from_attributes=True)
    exam_id: UUID
    max_attempts: Optional[int] = None


class ExamSubmitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    submission: SubmissionRead
    attempt: SubmissionAttemptRead


class AttemptGrade(BaseModel):
    """Lecturer manually sets a score on a theory attempt."""
    model_config = ConfigDict(from_attributes=True)
    score: Decimal
