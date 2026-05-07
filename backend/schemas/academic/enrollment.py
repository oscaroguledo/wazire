from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    PENDING = "pending"


class Semester(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    SIXTH = "sixth"
    SEVENTH = "seventh"
    EIGHTH = "eighth"
    FALL = "fall"
    SPRING = "spring"
    SUMMER = "summer"
    WINTER = "winter"
    INTERIM = "interim"


class EnrollmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: UUID
    course_id: UUID
    semester: Semester
    year: Optional[int] = Field(None, ge=2020, le=2100)


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: Optional[EnrollmentStatus] = None


class EnrollmentRead(EnrollmentBase):
    id: UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    institution_id: Optional[str] = None
    course_name: Optional[str] = None
    lecturer_id: Optional[UUID] = None
    status: EnrollmentStatus
    created_at: datetime
    updated_at: datetime


# Alias for API responses
EnrollmentResponse = EnrollmentRead


class EnrollmentListParams(BaseModel):
    """Query parameters for listing enrollments."""
    course_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    status: Optional[EnrollmentStatus] = None
    semester: Optional[Semester] = None
    year: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class BulkEnrollmentRequest(BaseModel):
    """Request body for bulk enrollment."""
    course_id: UUID
    student_ids: List[UUID]
    semester: Semester
    year: Optional[int] = Field(None, ge=2020, le=2100)


class EnrollmentCheckRequest(BaseModel):
    """Request to check if a student is enrolled in a course."""
    student_id: UUID
    course_id: UUID


class EnrollmentCheckResponse(BaseModel):
    """Response for enrollment check."""
    is_enrolled: bool
    enrollment: Optional[EnrollmentRead] = None


class EnrollmentListResponse(BaseModel):
    """Paginated list of enrollments."""
    data: List[EnrollmentRead]
    total: int
    page: int
    page_size: int


class EnrollmentDelete(BaseModel):
    id: UUID
