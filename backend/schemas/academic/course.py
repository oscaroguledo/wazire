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
    name: str
    description: Optional[str] = None
    course_code: str
    lecturer_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None


class CourseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = None
    description: Optional[str] = None
    course_code: Optional[str] = None
    lecturer_id: Optional[UUID] = None


class CourseRead(CourseBase):
    id: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "name": self.name,
            "description": self.description,
            "course_code": self.course_code,
            "lecturer_id": str(self.lecturer_id) if self.lecturer_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
