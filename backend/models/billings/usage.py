import uuid
from datetime import datetime

from sqlalchemy import Index, func, CheckConstraint, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class CurrentUsage(Base):
    """Current usage tracking for billing dashboard.
    
    Matches the UsageCard component in Billing.tsx
    """
    __tablename__ = "current_usage"
    __table_args__ = (
        Index("ix_current_usage_tenant_id", "tenant_id"),
        Index("ix_current_usage_semester_id", "semester_id"),
        Index("ix_current_usage_created_at", "created_at"),
        Index("ix_current_usage_updated_at", "updated_at"),
        {"schema": "billings"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to current active semester")

    # Usage metrics (from Billing.tsx UsageCard)
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total number of students")

    # Plan info (single Standard plan at ₦2000/student)
    current_plan: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.billing_plans.id", ondelete="SET NULL"), nullable=True, comment="FK to billing plan")

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self):
        return f"<CurrentUsage(id={self.id}, tenant_id={self.tenant_id}, student_count={self.student_count}, current_plan={self.current_plan})>"
    
    def to_dict(self):
        return {
            "id": str(self.id) if self.id else None,
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "student_count": self.student_count,
            "current_plan": str(self.current_plan) if self.current_plan else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }