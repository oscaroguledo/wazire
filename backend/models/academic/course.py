
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Index, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.types.guid import GUID

from core.database import Base
from core.utils.uuid7 import uuid7


class Course(Base):
    """Course model with lecturer and tenant support."""

    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_course_code", "course_code", unique=True),
        Index("ix_courses_lecturer_id", "lecturer_id"),
        Index("ix_courses_tenant_id", "tenant_id"),
        Index("ix_courses_created_at", "created_at"),
        Index("ix_courses_updated_at", "updated_at"),
        # Composite indexes
        Index("ix_courses_lecturer_tenant", "lecturer_id", "tenant_id"),
        Index("ix_courses_tenant_code", "tenant_id", "course_code"),
        Index("ix_courses_tenant_created", "tenant_id", "created_at"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Course name")
    description: Mapped[str] = mapped_column(String(255), nullable=True, comment="Optional course description")
    course_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="Short course code")
    lecturer_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK to users (lecturer)")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=True, comment="FK to tenants (organization)")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")

    # Relationships (selectin loading for async safety)
    enrollments = relationship("Enrollment", foreign_keys="Enrollment.course_id", back_populates="course", lazy="selectin")
    exams = relationship("Exam", back_populates="course", lazy="selectin")
    lecturer = relationship("User", foreign_keys=[lecturer_id], back_populates="courses", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, course_code={self.course_code}, name={self.name})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "name": self.name,
            "description": self.description,
            "course_code": self.course_code,
            "lecturer": self.lecturer.to_dict() if self.lecturer else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }