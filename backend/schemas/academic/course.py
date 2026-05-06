from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CourseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: Optional[str] = None
    course_code: str
    lecturer_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = None
    description: Optional[str] = None
    course_code: Optional[str] = None
    lecturer_id: Optional[UUID] = None


class CourseRead(CourseBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
