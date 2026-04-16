from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID

class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    PENDING = "pending"

class Semester(str, Enum):
    FALL = "fall"
    SPRING = "spring"
    SUMMER = "summer"
    WINTER = "winter"
    INTERIM = "interim"
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    SIXTH = "sixth"
    SEVENTH = "seventh"
    EIGHTH = "eighth"

class EnrollmentCreate(BaseModel):
    student_id: str = Field(..., description="Student user ID")
    course_id: str = Field(..., description="Course ID")
    semester: Semester = Field(..., description="Academic semester")
    year: Optional[int] = Field(None, ge=2020, le=2100, description="Academic year (auto-set from current year if not provided)")

class EnrollmentUpdate(BaseModel):
    status: Optional[EnrollmentStatus] = Field(None, description="Enrollment status")

class EnrollmentResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = Field(None, description="Student full name")
    student_email: Optional[str] = Field(None, description="Student email address")
    institution_id: Optional[str] = Field(None, description="Student matric/reg number")
    course_id: str
    course_name: Optional[str] = Field(None, description="Course name")
    lecturer_id: Optional[str] = Field(None, description="Lecturer ID")
    semester: Semester
    year: Optional[int] = Field(None, description="Academic year")
    status: EnrollmentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EnrollmentListParams(BaseModel):
    page: Optional[int] = Field(1, ge=1, description="Page number")
    per_page: Optional[int] = Field(10, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(None, description="Search term")
    student_id: Optional[str] = Field(None, description="Filter by student ID")
    course_id: Optional[str] = Field(None, description="Filter by course ID")
    lecturer_id: Optional[UUID] = Field(None, description="Filter by lecturer ID")
    status: Optional[EnrollmentStatus] = Field(None, description="Filter by status")
    semester: Optional[Semester] = Field(None, description="Filter by semester")
    year: Optional[int] = Field(None, ge=2020, le=2100, description="Filter by academic year")

class BulkEnrollmentRequest(BaseModel):
    enrollments: List[EnrollmentCreate] = Field(..., description="List of enrollments to create")

class EnrollmentCheckRequest(BaseModel):
    student_id: str = Field(..., description="Student user ID")
    course_id: str = Field(..., description="Course ID")

class EnrollmentCheckResponse(BaseModel):
    enrolled: bool = Field(..., description="Whether student is enrolled")
    enrollment: Optional[EnrollmentResponse] = Field(None, description="Enrollment details if enrolled")

class EnrollmentListResponse(BaseModel):
    items: List[EnrollmentResponse]
    pagination: dict