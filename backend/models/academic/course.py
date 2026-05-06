
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Index, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from core.types.guid import GUID
from core.database import Base
from uuid_utils import uuid7


class Course(Base):
    """Course model with lecturer and tenant support."""

    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_course_code", "course_code", unique=True),
        Index("ix_courses_lecturer_id", "lecturer_id"),
        Index("ix_courses_tenant_id", "tenant_id"),
        Index("ix_courses_semester_id", "semester_id"),
        Index("ix_courses_created_at", "created_at"),
        Index("ix_courses_updated_at", "updated_at"),
        Index("ix_courses_created_by", "created_by"),
        Index("ix_courses_updated_by", "updated_by"),
        # Composite indexes
        Index("ix_courses_lecturer_tenant", "lecturer_id", "tenant_id"),
        Index("ix_courses_tenant_code", "tenant_id", "course_code"),
        Index("ix_courses_tenant_created", "tenant_id", "created_at"),
        Index("ix_courses_tenant_semester", "tenant_id", "semester_id"),
        {"schema": "academic"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Course name")
    description: Mapped[str] = mapped_column(String(255), nullable=True, comment="Optional course description")
    course_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="Short course code")
    lecturer_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK to users (lecturer)")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenants (organization)")
    semester_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, course_code={self.course_code}, name={self.name})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "name": self.name,
            "description": self.description,
            "course_code": self.course_code,
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }