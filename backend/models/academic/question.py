from decimal import Decimal
from enum import Enum
import re
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import ForeignKey, String, Integer, Index, func, CheckConstraint, JSON, Numeric, Enum as SAEnum, inspect, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base
from uuid_utils import uuid7

class QuestionExams(Base):
    __tablename__ = "question_exams"
    __table_args__ = (
        Index("ix_question_exams_question_id", "question_id"),
        Index("ix_question_exams_exam_id", "exam_id"),
        {"schema": "academic"},
    )

    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.questions.id", ondelete="CASCADE"), primary_key=True, comment="FK to question")
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.exams.id", ondelete="CASCADE"), primary_key=True, comment="FK to exam")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<QuestionExams(question_id={self.question_id}, exam_id={self.exam_id})>"

    def to_dict(self) -> dict:
        return {
            "question_id": str(self.question_id) if self.question_id else None,
            "exam_id": str(self.exam_id) if self.exam_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    THEORY = "theory"
    FILL_IN_BLANKS = "fill_in_blanks"

class Industry(str, Enum):
    MEDICAL_AND_HEALTH_SCIENCES = "medical_and_health_sciences"
    NATURAL_SCIENCES = "natural_sciences"
    MATHEMATICS_AND_STATISTICS = "mathematics_and_statistics"
    ENGINEERING_AND_TECHNOLOGY = "engineering_and_technology"
    COMPUTING_AND_INFORMATION_TECHNOLOGY = "computing_and_information_technology"
    BUSINESS_AND_MANAGEMENT = "business_and_management"
    ECONOMICS_AND_FINANCE = "economics_and_finance"
    LAW_AND_GOVERNANCE = "law_and_governance"
    SOCIAL_SCIENCES = "social_sciences"
    HUMANITIES = "humanities"
    ARTS_AND_DESIGN = "arts_and_design"
    MEDIA_AND_COMMUNICATION = "media_and_communication"
    EDUCATION = "education"
    SPORTS_AND_PHYSICAL_EDUCATION = "sports_and_physical_education"
    AGRICULTURE_AND_FOOD_SCIENCE = "agriculture_and_food_science"
    ENVIRONMENT_AND_SUSTAINABILITY = "environment_and_sustainability"
    VOCATIONAL_AND_APPLIED = "vocational_and_applied"
    GENERAL = "general"

class Question(Base):
    """Question model representing a question in an exam.
    """
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_tenant_id", "tenant_id"),
        Index("ix_questions_parent_id", "parent_id"),
        Index("ix_questions_answer_id", "answer_id"),
        Index("ix_questions_semester_id", "semester_id"),
        Index("ix_questions_created_at", "created_at"),
        Index("ix_questions_industry", "industry"),
        Index("ix_questions_qtype", "qtype"),
        Index("ix_questions_updated_at", "updated_at"),
        Index("ix_questions_created_by", "created_by"),
        Index("ix_questions_updated_by", "updated_by"),
        Index("ix_questions_tenant_created_at", "tenant_id", "created_at"),
        # Composite indexes for common query patterns
        Index("ix_questions_tenant_qtype", "tenant_id", "qtype"),
        Index("ix_questions_tenant_industry", "tenant_id", "industry"),
        Index("ix_questions_parent_qtype", "parent_id", "qtype"),
        Index("ix_questions_tenant_semester", "tenant_id", "semester_id"),
        {"schema": "academic"},
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    number: Mapped[str] = mapped_column(String(20), nullable=False, comment="Question number within the exam")
    text: Mapped[str] = mapped_column(String(2000), nullable=False, comment="Question text")
    images: Mapped[list] = mapped_column(JSON, nullable=True, comment="Optional array of image URLs for the question")
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.questions.id", ondelete="CASCADE"), nullable=True, comment="Optional FK to parent question for sub-questions")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant/organization")
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester")
    answer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic.answers.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to an Answer shared across questions")
    rules: Mapped[str] = mapped_column(String(2000), nullable=True, comment="Optional grading rules or metadata in JSON format")
    mark: Mapped[Optional[Decimal]] = mapped_column(Decimal(10, 2), nullable=True, comment="Mark for the question")
    industry: Mapped[Industry] = mapped_column(SAEnum(Industry, name="industry_enum"), nullable=False, comment="Industry/subject area of the question")
    qtype: Mapped[QuestionType] = mapped_column(SAEnum(QuestionType, name="question_type_enum", create_type=True), nullable=False, default=QuestionType.THEORY, comment="Question type: multiple_choice|theory|fill_in_blanks")
    options: Mapped[list] = mapped_column(JSON, nullable=True, comment='Options JSON list, e.g. [{"label":"a","text":"Option A"}]')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who created the question")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who last updated the question")
    
    def __repr__(self) -> str:
        return f"<Question(id={self.id}, number={self.number}, type={self.qtype}, tenant_id={self.tenant_id})>"

    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "number": self.number,
            "text": self.text,
            "rules": self.rules,
            "images": self.images if getattr(self, "images", None) else [],
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "industry": self.industry.value if self.industry else None,
            "qtype": self.qtype.value if self.qtype else None,
            "options": self.options,
            "mark": float(self.mark) if self.mark else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }

class AnswerEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"
    J = "J"
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    O = "O"
    P = "P"
    Q = "Q"
    R = "R"
    S = "S"
    T = "T"
    U = "U"
    V = "V"
    W = "W"
    X = "X"
    Y = "Y"
    Z = "Z"
    
class Answer(Base):
    """Answer model representing a correct answer for a question.
    
    Supports both MCQ (option letters A-Z) and fill-in-the-blanks (text answers).
    For MCQ: use `value` field (AnswerEnum A-Z)
    For FITB: use `text_value` field (actual text answer)
    """
    __tablename__ = "answers"
    __table_args__ = (
        Index("ix_answers_id", "id"),
        Index("ix_answers_created_at", "created_at"),
        Index("ix_answers_created_by", "created_by"),
        Index("ix_answers_updated_by", "updated_by"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    # For MCQ questions: stores the correct option letter (a-z)
    value: Mapped[AnswerEnum] = mapped_column(SAEnum(AnswerEnum, name="answer_enum"), nullable=True, comment="MCQ answer: option letter a-z")
    # For fill-in-the-blanks questions: stores the correct text answer
    text_value: Mapped[str] = mapped_column(String(500), nullable=True, comment="FITB answer: correct text answer (case-insensitive match)")
    # Optional: acceptable variations for FITB (JSON array of strings)
    acceptable_variations: Mapped[list] = mapped_column(JSON, nullable=True, comment='FITB: acceptable answer variations, e.g., ["Photosynthesis", "photosynthesis"]')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who created the answer")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to user who last updated the answer")
    
    def __repr__(self) -> str:
        return f"<Answer(id={self.id}, value={self.value}, text_value={self.text_value})>"

    def to_dict(self) -> dict:

        return {
            "id": str(self.id) if self.id else None,
            "value": self.value.value if self.value else None,
            "text_value": self.text_value if self.text_value else None,
            "acceptable_variations": self.acceptable_variations if self.acceptable_variations else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }