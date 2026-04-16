from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, JSON, Numeric, Integer, Index, func, CheckConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.types.guid import GUID
from core.database import Base
from core.utils.uuid7 import uuid7


class Submission(Base):
    """One submission record per student per exam.

    Tracks how many attempts the student has made and their latest score.
    Each individual attempt is stored in SubmissionAttempt.
    """

    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_student_id", "student_id"),
        Index("ix_submissions_exam_id", "exam_id"),
        Index("ix_submissions_graded_at", "graded_at"),
        Index("uq_submissions_student_exam", "student_id", "exam_id", unique=True),
        CheckConstraint("attempts_count >= 0", name="ck_submissions_attempts_nonnegative"),
        CheckConstraint("(latest_score IS NULL) OR (latest_score >= 0)", name="ck_submissions_latest_score_nonnegative"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    student_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.exams.id", ondelete="CASCADE"), nullable=False)
    latest_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (selectin loading for async safety)
    exam = relationship("Exam", back_populates="submissions", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Submission(id={self.id}, student_id={self.student_id}, exam_id={self.exam_id})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "exam_id": str(self.exam_id),
            "latest_score": str(self.latest_score) if self.latest_score is not None else None,
            "attempts_count": self.attempts_count,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SubmissionAttempt(Base):
    """One row per attempt a student makes on a submission."""

    __tablename__ = "submission_attempts"
    __table_args__ = (
        Index("ix_submission_attempts_submission_id", "submission_id"),
        Index("ix_submission_attempts_submission_attempt", "submission_id", "attempt_number", unique=True),
        Index("ix_submission_attempts_graded_at", "graded_at"),
        CheckConstraint("(score IS NULL) OR (score >= 0)", name="ck_submission_attempts_score_nonneg"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    submission_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.submissions.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    scan_pages: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list, comment="List of scanned page URLs for offline exams")
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SubmissionAttempt(id={self.id}, submission_id={self.submission_id}, attempt={self.attempt_number})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "submission_id": str(self.submission_id),
            "attempt_number": self.attempt_number,
            "score": str(self.score) if self.score is not None else None,
            "scan_pages": self.scan_pages or [],
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
