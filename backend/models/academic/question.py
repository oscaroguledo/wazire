from decimal import Decimal
from enum import Enum
import re
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import ForeignKey, String, Integer, Index, func, CheckConstraint, JSON, Numeric, Enum as SAEnum, inspect, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.types.guid import GUID

from core.database import Base
from core.utils.uuid7 import uuid7

class QuestionExams(Base):
    __tablename__ = "question_exams"
    __table_args__ = (
        Index("ix_question_exams_question_id", "question_id"),
        Index("ix_question_exams_exam_id", "exam_id"),
        {"schema": "academic"},
    )

    question_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.questions.id", ondelete="CASCADE"), primary_key=True, comment="FK to question")
    exam_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.exams.id", ondelete="CASCADE"), primary_key=True, comment="FK to exam")

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
    """Question model representing a question in an exam."""
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_tenant_id", "tenant_id"),
        Index("ix_questions_parent_id", "parent_id"),
        Index("ix_questions_created_at", "created_at"),
        Index("ix_questions_industry", "industry"),
        Index("ix_questions_tenant_created_at", "tenant_id", "created_at"),
        CheckConstraint("qtype IN ('multiple_choice','theory','fill_in_blanks')", name="ck_questions_qtype"),
        {"schema": "academic"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    number: Mapped[str] = mapped_column(String(20), nullable=False, comment="Question number within the exam")
    text: Mapped[str] = mapped_column(String(2000), nullable=False, comment="Question text")
    images: Mapped[list] = mapped_column(JSON, nullable=True, comment="Optional array of image URLs for the question")
    parent_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.questions.id", ondelete="CASCADE"), nullable=True, comment="Optional FK to parent question for sub-questions")
    # Optional tenant_id: questions can be tenant-scoped or global when None
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to tenant/organization")
    rules: Mapped[str] = mapped_column(String(2000), nullable=True, comment="Optional grading rules or metadata in JSON format")
    mark: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True, comment="Mark for the question")
    # Question type: 'multiple_choice', 'theory', or 'fill_in_blanks'
    industry: Mapped[Industry] = mapped_column(SAEnum(Industry, name="industry_enum"), nullable=False, comment="Industry/subject area of the question")
    qtype: Mapped[str] = mapped_column(String(50), nullable=False, server_default="theory", comment="Question type: multiple_choice|theory|fill_in_blanks")
    # Options for multiple choice questions stored as JSON array of {label,text}
    # Canonical storage: [{"label":"a","text":"Option A"}, ...]
    options: Mapped[list] = mapped_column(JSON, nullable=True, comment='Options JSON list, e.g. [{"label":"a","text":"Option A"}]')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (selectin loading for async safety)
    exams: Mapped[list] = relationship("Exam", secondary="academic.question_exams", back_populates="questions", lazy="selectin")
    # Each Question may reference a single Answer (many Questions can share the same Answer)
    answer_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.answers.id", ondelete="SET NULL"), nullable=True, comment="Optional FK to an Answer shared across questions")
    answer: Mapped["Answer"] = relationship("Answer", back_populates="questions", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, number={self.number}, type={self.qtype}, tenant_id={self.tenant_id})>"

    def get_options(self) -> list[dict]:
        """Return options as a list of {label,text} regardless of storage shape.

        Stored `options` may be:
        - a list of dicts (canonical)
        - a dict mapping label->text
        - a single labeled string (legacy): "[a]-Option A [b]-Option B"
        This method normalizes all shapes to a list of {label,text}.
        """
        raw = getattr(self, "options", None)
        if not raw:
            return []
        # Already canonical list
        if isinstance(raw, list):
            items = []
            for i, v in enumerate(raw, start=1):
                if isinstance(v, dict):
                    items.append({"label": str(v.get("label", i)), "text": str(v.get("text", "")).strip()})
                elif isinstance(v, str):
                    items.append({"label": str(i), "text": v})
            return items

        # dict mapping label->text
        if isinstance(raw, dict):
            return [{"label": k, "text": v} for k, v in raw.items()]

        # legacy string format: parse labeled segments
        try:
            pattern = re.compile(r"\[([^\]]+)\]\-([^\[]+)")
            m = pattern.findall(str(raw))
            if m:
                return [{"label": lbl.strip(), "text": txt.strip()} for lbl, txt in m]
        except Exception:
            pass

        return []
    def to_dict(self) -> dict:
        # Check if relationships are loaded to avoid lazy loading errors
        inspector = inspect(self)
        exams_loaded = 'exams' not in inspector.unloaded
        answer_loaded = 'answer' not in inspector.unloaded

        # Build exams list only if loaded (avoid circular reference)
        exams_list = []
        if exams_loaded and getattr(self, 'exams', None):
            if isinstance(self.exams, list):
                # Only include exam IDs to avoid circular reference
                exams_list = [{"id": str(e.id)} for e in self.exams]

        # Build answer dict only if loaded
        answer_dict = None
        if answer_loaded and getattr(self, 'answer', None):
            try:
                answer_dict = self.answer.to_dict() if hasattr(self.answer, 'to_dict') else None
            except Exception:
                # If answer.to_dict() fails, return None
                answer_dict = None

        return {
            "id": str(self.id) if self.id else None,
            "number": self.number,
            "text": self.text,
            "rules": self.rules,
            "images": self.images if getattr(self, "images", None) else [],
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "industry": self.industry.value if self.industry else None,
            "qtype": self.qtype if self.qtype else None,
            "options": self.options if getattr(self, "options", None) else None,
            "parsed_options": self.get_options(),
            "exams": exams_list,
            "mark": float(self.mark) if self.mark else None,
            "answer": answer_dict,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class AnswerEnum(str, Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"
    
class Answer(Base):
    """Answer model representing a correct answer for a question.
    
    Supports both MCQ (option letters A-Z) and fill-in-the-blanks (text answers).
    For MCQ: use `value` field (AnswerEnum a-z)
    For FITB: use `text_value` field (actual text answer)
    """
    __tablename__ = "answers"
    __table_args__ = (
        Index("ix_answers_id", "id"),
        Index("ix_answers_created_at", "created_at"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    # For MCQ questions: stores the correct option letter (a-z)
    value: Mapped[AnswerEnum] = mapped_column(SAEnum(AnswerEnum, name="answer_enum"), nullable=True, comment="MCQ answer: option letter a-z")
    # For fill-in-the-blanks questions: stores the correct text answer
    text_value: Mapped[str] = mapped_column(String(500), nullable=True, comment="FITB answer: correct text answer (case-insensitive match)")
    # Optional: acceptable variations for FITB (JSON array of strings)
    acceptable_variations: Mapped[list] = mapped_column(JSON, nullable=True, comment='FITB: acceptable answer variations, e.g., ["Photosynthesis", "photosynthesis"]')
    # Answer type discriminator
    answer_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="mcq", comment="Answer type: mcq|fitb")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (selectin loading for async safety)
    questions: Mapped[list] = relationship("Question", back_populates="answer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Answer(id={self.id})>"

    def to_dict(self) -> dict:
        # Check if questions relationship is loaded to avoid lazy loading errors
        inspector = inspect(self)
        questions_loaded = 'questions' not in inspector.unloaded

        # Build questions list only if loaded (avoid circular reference)
        questions_list = []
        if questions_loaded and getattr(self, 'questions', None):
            if isinstance(self.questions, list):
                # Only include question IDs to avoid circular reference
                questions_list = [{"id": str(q.id)} for q in self.questions]

        return {
            "id": str(self.id) if self.id else None,
            "value": self.value.value if self.value else None,
            "text_value": self.text_value if self.text_value else None,
            "acceptable_variations": self.acceptable_variations if self.acceptable_variations else [],
            "answer_type": self.answer_type,
            "question": questions_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }