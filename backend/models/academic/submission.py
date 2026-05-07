import uuid
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, JSON, Numeric, Integer, Index, func, CheckConstraint, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    GRADING_IN_PROGRESS = "grading_in_progress"
    GRADED = "graded"


class Submission(Base):
    """One submission record per student per exam.

    Tracks how many attempts the student has made and their latest score.
    Each individual attempt is stored in SubmissionAttempt.
    """

    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_student_id", "student_id"),
        Index("ix_submissions_exam_id", "exam_id"),
        Index("ix_submissions_tenant_id", "tenant_id"),
        Index("ix_submissions_semester_id", "semester_id"),
        Index("ix_submissions_graded_at", "graded_at"),
        Index("ix_submissions_created_at", "created_at"),
        Index("ix_submissions_updated_at", "updated_at"),
        Index("uq_submissions_student_exam", "student_id", "exam_id", unique=True),
        # Composite indexes for dashboard queries
        Index("ix_submissions_exam_graded", "exam_id", "graded_at"),
        Index("ix_submissions_student_graded", "student_id", "graded_at"),
        Index("ix_submissions_tenant_exam", "tenant_id", "exam_id"),
        Index("ix_submissions_tenant_semester", "tenant_id", "semester_id"),
        CheckConstraint("attempts >= 0", name="ck_submissions_attempts_nonnegative"),
        CheckConstraint("(latest_score IS NULL) OR (latest_score >= 0)", name="ck_submissions_latest_score_nonnegative"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.exams.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False)
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester")
    latest_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[SubmissionStatus] = mapped_column(SAEnum(SubmissionStatus, name="submission_status_enum", create_type=True), nullable=False, default=SubmissionStatus.PENDING, comment="Submission status: pending|submitted|grading_in_progress|graded")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, comment="UTC moment when the student submitted the exam")
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Submission(id={self.id}, student_id={self.student_id}, exam_id={self.exam_id})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "exam_id": str(self.exam_id),
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "latest_score": str(self.latest_score) if self.latest_score is not None else None,
            "attempts": self.attempts,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SubmissionAttempt(Base):
    """One row per attempt a student makes on a submission."""

    __tablename__ = "submission_attempts"
    __table_args__ = (
        Index("ix_submission_attempts_submission_id", "submission_id"),
        Index("ix_submission_attempts_graded_at", "graded_at"),
        Index("ix_submission_attempts_created_at", "created_at"),
        CheckConstraint("(score IS NULL) OR (score >= 0)", name="ck_submission_attempts_score_nonneg"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.submissions.id", ondelete="CASCADE"), nullable=False, comment="FK to submission")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-based attempt number for this submission")
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    scan_pages: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="List of scanned page URLs for offline exams")
    grading_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, comment="UTC moment when grading began for this attempt")
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SubmissionAttempt(id={self.id}, submission_id={self.submission_id}, attempt_number={self.attempt_number}, score={self.score})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "submission_id": str(self.submission_id),
            "attempt_number": self.attempt_number,
            "score": str(self.score) if self.score is not None else None,
            "scan_pages": self.scan_pages,
            "grading_started_at": self.grading_started_at.isoformat() if self.grading_started_at else None,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
