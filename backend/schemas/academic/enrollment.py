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


class EnrollmentDelete(BaseModel):
    id: UUID
