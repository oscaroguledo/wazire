from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, func, DateTime, ForeignKey, String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from core.types.guid import GUID
from core.database import Base
from uuid_utils import uuid7


class BillingPlan(Base):
    """Billing plan configuration matching Billing.tsx pricing plan.
    
    Schools only pay for students who have paid their school fees (pay-as-you-collect).
    Default: ₦2,000 per paid student, billed monthly in arrears.
    """
    __tablename__ = "billing_plans"
    __table_args__ = (
        Index("ix_billing_plans_tenant_id", "tenant_id"),
        Index("ix_billing_plans_is_active", "is_active"),
        Index("ix_billing_plans_created_at", "created_at"),
        Index("ix_billing_plans_updated_at", "updated_at"),
        Index("ix_billing_plans_created_by", "created_by"),
        Index("ix_billing_plans_updated_by", "updated_by"),
        {"schema": "billings"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    
    # Plan configuration (matches Billing.tsx pricingPlan)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False, default="standard", comment="Plan identifier e.g. 'standard'")
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Standard", comment="Plan name")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="Simple pricing for all institutions", comment="Plan description")
    
    # Pricing
    price_per_student: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, comment="Price per student in NGN")
    min_students: Mapped[int] = mapped_column(Integer, nullable=False, default=20, comment="Minimum students required")
    
    # Features (stored as comma-separated string, matching Billing.tsx features array)
    features: Mapped[str] = mapped_column(String(2000), nullable=False, default="Unlimited students,Unlimited lecturers,Unlimited AI grading,Priority support,Analytics & reports,Paper exam scanning,Custom branding,API access,Mobile-friendly exams", comment="Comma-separated list of features")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self):
        return f"<BillingPlan(id={self.id}, tenant_id={self.tenant_id}, name={self.name}, price_per_student={self.price_per_student})>"
    
    def get_features_list(self) -> list[str]:
        """Return features as a list (for API response matching Billing.tsx)."""
        return [f.strip() for f in self.features.split(",") if f.strip()]
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "tenant_id": str(self.tenant_id),
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "price_per_student": self.price_per_student,
            "min_students": self.min_students,
            "features": self.get_features_list(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
