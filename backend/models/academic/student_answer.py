from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, JSON, Index, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.types.guid import GUID
from core.database import Base
from core.utils.uuid7 import uuid7


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = (
        Index("ix_student_answers_student_id", "student_id"),
        Index("ix_student_answers_exam_id", "exam_id"),
        Index("ix_student_answers_question_id", "question_id"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    student_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.exams.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.questions.id", ondelete="CASCADE"), nullable=False)
    answer: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Student's in-progress answer JSON")
    last_saved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "exam_id": str(self.exam_id),
            "question_id": str(self.question_id),
            "answer": self.answer,
            "last_saved_at": self.last_saved_at.isoformat() if self.last_saved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
