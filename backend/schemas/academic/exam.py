from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional, Dict

from core.utils.response import ResponseModel as _BaseResponseModel
from core.utils.validation import ValidationMixin, validate_duration


class KeysetMeta(BaseModel):
    next_cursor: Optional[str] = None


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

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate exam title."""
        if not v or len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        if len(v) > 200:
            raise ValueError('Title must not exceed 200 characters')
        return v

    @field_validator('duration_hours', 'duration_minutes')
    @classmethod
    def validate_duration_fields(cls, v, field_name):
        """Validate exam duration hours and minutes."""
        if field_name == 'duration_hours':
            if v < 1 or v > 24:
                raise ValueError('Duration hours must be between 1 and 24')
        elif field_name == 'duration_minutes':
            if v < 0 or v > 59:
                raise ValueError('Duration minutes must be between 0 and 59')
        return v

    @field_validator('total_marks', 'passing_marks')
    @classmethod
    def validate_marks(cls, v):
        """Validate marks."""
        if v is not None:
            if v < 0:
                raise ValueError('Marks cannot be negative')
            if v > 1000:
                raise ValueError('Marks cannot exceed 1000')
        return v

    @field_validator('max_attempts')
    @classmethod
    def validate_max_attempts(cls, v):
        """Validate max attempts."""
        if v < 1:
            raise ValueError('Max attempts must be at least 1')
        if v > 10:
            raise ValueError('Max attempts cannot exceed 10')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate exam status."""
        if v is not None:
            valid_statuses = ['not_started', 'in_progress', 'finished', 'draft']
            if v.lower() not in valid_statuses:
                raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
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

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate exam title."""
        if v is not None:
            if len(v.strip()) < 3:
                raise ValueError('Title must be at least 3 characters long')
            if len(v) > 200:
                raise ValueError('Title must not exceed 200 characters')
        return v

    @field_validator('duration_hours', 'duration_minutes')
    @classmethod
    def validate_duration_fields(cls, v, field_name):
        """Validate exam duration hours and minutes."""
        if v is not None:
            if field_name == 'duration_hours':
                if v < 1 or v > 24:
                    raise ValueError('Duration hours must be between 1 and 24')
            elif field_name == 'duration_minutes':
                if v < 0 or v > 59:
                    raise ValueError('Duration minutes must be between 0 and 59')
        return v


class ExamRead(ExamBase):
    id: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# Response envelopes
class ExamResponse(_BaseResponseModel):
    data: Optional[ExamRead] = None


class ExamListResponse(_BaseResponseModel):
    data: Optional[List[ExamRead]] = None
    meta: Optional[KeysetMeta] = None
