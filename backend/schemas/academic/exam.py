from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from core.utils.validation import ValidationMixin


class ExamBase(ValidationMixin):
    model_config = ConfigDict(from_attributes=True)
    title: str
    description: Optional[str] = None
    duration_hours: int
    duration_minutes: int = 0
    total_marks: Optional[int] = None
    passing_marks: Optional[int] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    max_attempts: int = 1
    course_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Title must be at least 3 characters long")
        if len(v) > 200:
            raise ValueError("Title must not exceed 200 characters")
        return v

    @field_validator("duration_hours", "duration_minutes")
    @classmethod
    def validate_duration_fields(cls, v, info):
        if info.field_name == "duration_hours" and not (1 <= v <= 24):
            raise ValueError("Duration hours must be between 1 and 24")
        if info.field_name == "duration_minutes" and not (0 <= v <= 59):
            raise ValueError("Duration minutes must be between 0 and 59")
        return v

    @field_validator("total_marks", "passing_marks")
    @classmethod
    def validate_marks(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Marks cannot be negative")
            if v > 1000:
                raise ValueError("Marks cannot exceed 1000")
        return v

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v):
        if not (1 <= v <= 10):
            raise ValueError("Max attempts must be between 1 and 10")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            valid = ["not_started", "in_progress", "finished", "draft"]
            if v.lower() not in valid:
                raise ValueError(f"Invalid status. Must be one of: {', '.join(valid)}")
        return v


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)
    title: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[int] = None
    duration_minutes: Optional[int] = None
    total_marks: Optional[int] = None
    passing_marks: Optional[int] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    max_attempts: Optional[int] = None


class ExamRead(ExamBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExamDelete(BaseModel):
    id: UUID
