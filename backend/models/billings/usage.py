from __future__ import annotations

import uuid
from enum import Enum
from datetime import datetime

from sqlalchemy import Index, func, CheckConstraint, Integer, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.types.guid import GUID
from core.database import Base
from core.utils.uuid7 import uuid7


class PlanType(str, Enum):
    STARTER = "starter"
    INTERMEDIATE = "intermediate"
    ENTERPRISE = "enterprise"


class CurrentUsage(Base):
    __tablename__ = "current_usage"
    __table_args__ = (
        Index("ix_current_usage_plan", "plan"),
        Index("ix_current_usage_tenant_id", "tenant_id"),
        Index("ix_current_usage_created_at", "created_at"),
        Index("ix_current_usage_updated_at", "updated_at"),
        Index("ix_current_usage_tenant_plan", "tenant_id", "plan"),
        CheckConstraint("student_count >= 0", name="check_student_count_non_negative"),
        CheckConstraint("exams_graded >= 0", name="check_exams_graded_non_negative"),
        {"schema": "billings"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="Number of students")
    exams_graded: Mapped[int] = mapped_column(Integer, nullable=False, comment="Number of exams graded")
    plan: Mapped[PlanType] = mapped_column(SAEnum(PlanType), nullable=False, comment="Current plan type")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id"), nullable=False, comment="Tenant ID")
    plan_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="When the plan was last updated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="When the record was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="When the record was last updated")
    
    # Relationships (selectin loading for async safety)
    tenant = relationship("Tenant", back_populates="usage", lazy="selectin")
    
    def __repr__(self):
        return f"<CurrentUsage(id={self.id}, student_count={self.student_count}, exams_graded={self.exams_graded}, plan={self.plan}, plan_updated_at={self.plan_updated_at})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "student_count": self.student_count,
            "exams_graded": self.exams_graded,
            "plan": self.plan.value,
            "tenant": self.tenant.to_dict() if self.tenant else None,
            "plan_updated_at": self.plan_updated_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    