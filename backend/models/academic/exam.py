import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, Enum as SQLEnum, String, Integer, Numeric, Index, func, CheckConstraint, DateTime, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base
from uuid_utils import uuid7

class ExamStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"

class Exam(Base):
    """Exam instance for a course.

    Fields:
    - id: UUID primary key (uuid7 time-ordered)
    - title: exam title
    - duration: duration in minutes
    - course_id: FK to `academic.courses.id`
    - tenant_id: FK to `account.tenants.id`
    - semester_id: FK to `billings.semesters.id`
    - created_by / updated_by: FK to `account.users.id` (user ids)
    - created_at / updated_at timestamps
    """

    __tablename__ = "exams"
    __table_args__ = (
        Index("ix_exams_course_id", "course_id"),
        Index("ix_exams_tenant_id", "tenant_id"),
        Index("ix_exams_semester_id", "semester_id"),
        Index("ix_exams_status", "status"),
        Index("ix_exams_start_time", "start_time"),
        Index("ix_exams_end_time", "end_time"),
        Index("ix_exams_created_by", "created_by"),
        Index("ix_exams_updated_by", "updated_by"),
        Index("ix_exams_created_at", "created_at"),
        Index("ix_exams_updated_at", "updated_at"),
        # Composite indexes for common query patterns
        Index("ix_exams_tenant_status", "tenant_id", "status"),
        Index("ix_exams_tenant_start_time", "tenant_id", "start_time"),
        Index("ix_exams_course_status", "course_id", "status"),
        Index("ix_exams_course_start_time", "course_id", "start_time"),
        Index("ix_exams_tenant_semester", "tenant_id", "semester_id"),
        Index("ix_exams_course_semester", "course_id", "semester_id"),
        CheckConstraint("duration > 0", name="ck_exams_duration_positive"),
        CheckConstraint("max_attempts > 0", name="ck_exams_max_attempts_positive"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="Exam title")
    description: Mapped[str] = mapped_column(String(2000), nullable=True, comment="Exam description")
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Exam start time (timezone-aware)")
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Exam end time: start_time + duration (persisted)")
    duration: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, comment="Duration in hours (decimal)")
    total_marks: Mapped[int] = mapped_column(Integer, nullable=True, comment="Total marks for the exam")
    passing_marks: Mapped[int] = mapped_column(Integer, nullable=True, comment="Passing marks for the exam")
    status: Mapped[ExamStatus] = mapped_column(SQLEnum(ExamStatus, name="exam_status", create_type=True), nullable=True, default=ExamStatus.NOT_STARTED, comment="Exam status: not_started, in_progress, finished")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="Maximum attempts allowed (default 1)")

    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.courses.id", ondelete="CASCADE"), nullable=True, comment="FK to course")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant/organization")
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")


    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, title={self.title}, course_id={self.course_id})>"

    
    def to_dict(self) -> dict:
        # Convert duration to hours and minutes
        duration_hours = int(self.duration) if self.duration else 0
        duration_minutes = int(round((self.duration - Decimal(duration_hours)) * Decimal(60))) if self.duration else 0

        return {
            "id": str(self.id) if self.id else None,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": duration_hours,
            "duration_minutes": duration_minutes,
            "total_marks": self.total_marks,
            "passing_marks": self.passing_marks,
            "status": self.status.value if self.status else None,
            "max_attempts": self.max_attempts,
            "course_id": str(self.course_id) if self.course_id else None,
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }