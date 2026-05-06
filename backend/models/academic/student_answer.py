from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, JSON, Index, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class StudentAnswer(Base):
    """Student answer model for exam responses.
    """
    __tablename__ = "student_answers"
    __table_args__ = (
        Index("ix_student_answers_student_id", "student_id"),
        Index("ix_student_answers_exam_id", "exam_id"),
        Index("ix_student_answers_question_id", "question_id"),
        Index("ix_student_answers_tenant_id", "tenant_id"),
        Index("ix_student_answers_semester_id", "semester_id"),
        Index("ix_student_answers_created_at", "created_at"),
        Index("ix_student_answers_updated_at", "updated_at"),
        Index("ix_student_answers_created_by", "created_by"),
        Index("ix_student_answers_updated_by", "updated_by"),
        # Composite indexes for common query patterns
        Index("ix_student_answers_student_exam", "student_id", "exam_id"),
        Index("ix_student_answers_exam_question", "exam_id", "question_id"),
        Index("ix_student_answers_student_question", "student_id", "question_id"),
        Index("ix_student_answers_tenant_exam", "tenant_id", "exam_id"),
        Index("ix_student_answers_tenant_semester", "tenant_id", "semester_id"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.exams.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.questions.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False)
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester")
    answer: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Student's in-progress answer JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who last updated the answer")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who created the answer")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "exam_id": str(self.exam_id),
            "question_id": str(self.question_id),
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "answer": self.answer,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_by": str(self.created_by) if self.created_by else None,
        }
