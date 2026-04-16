from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict


class LecturerDashboardBase(BaseModel):
    total_courses: int = 0
    total_exams: int = 0
    total_students: int = 0
    pending_submissions: int = 0
    graded_submissions: int = 0
    active_courses: int = 0


class LecturerDashboardCreate(LecturerDashboardBase):
    lecturer_id: uuid.UUID


class LecturerDashboardUpdate(BaseModel):
    total_courses: Optional[int] = None
    total_exams: Optional[int] = None
    total_students: Optional[int] = None
    pending_submissions: Optional[int] = None
    graded_submissions: Optional[int] = None
    active_courses: Optional[int] = None


class LecturerDashboardResponse(LecturerDashboardBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    lecturer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AdminDashboardBase(BaseModel):
    total_users: int = 0
    total_lecturers: int = 0
    total_students: int = 0
    total_courses: int = 0
    total_exams: int = 0
    total_submissions: int = 0
    total_graded_submissions: int = 0
    total_pending_submissions: int = 0


class AdminDashboardCreate(AdminDashboardBase):
    admin_id: uuid.UUID


class AdminDashboardUpdate(BaseModel):
    total_users: Optional[int] = None
    total_lecturers: Optional[int] = None
    total_students: Optional[int] = None
    total_courses: Optional[int] = None
    total_exams: Optional[int] = None
    total_submissions: Optional[int] = None
    total_graded_submissions: Optional[int] = None
    total_pending_submissions: Optional[int] = None


class AdminDashboardResponse(AdminDashboardBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    admin_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class StudentDashboardBase(BaseModel):
    total_courses: int = 0
    total_exams: int = 0
    total_submissions: int = 0
    total_graded_submissions: int = 0
    total_pending_submissions: int = 0
    missed_exams: int = 0
    upcoming_exams: int = 0


class StudentDashboardCreate(StudentDashboardBase):
    student_id: uuid.UUID


class StudentDashboardUpdate(BaseModel):
    total_courses: Optional[int] = None
    total_exams: Optional[int] = None
    total_submissions: Optional[int] = None
    total_graded_submissions: Optional[int] = None
    total_pending_submissions: Optional[int] = None
    missed_exams: Optional[int] = None
    upcoming_exams: Optional[int] = None


class StudentDashboardResponse(StudentDashboardBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DashboardSummary(BaseModel):
    """Summary response for any user type's dashboard"""
    role: str
    data: Union[LecturerDashboardResponse, AdminDashboardResponse, StudentDashboardResponse]


class DashboardRefreshRequest(BaseModel):
    """Request to refresh dashboard stats"""
    user_id: Optional[uuid.UUID] = None  # If None, refresh for current user
