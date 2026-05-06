from __future__ import annotations

import uuid
from enum import Enum
from datetime import datetime

from sqlalchemy import Index, func, CheckConstraint, Integer, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class Invoice(Base):
    """Invoice model for billing history.
    
    Matches the Invoice interface in Billing.tsx
    """
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoice_status", "status"),
        Index("ix_invoice_tenant_id", "tenant_id"),
        Index("ix_invoice_semester_id", "semester_id"),
        Index("ix_invoice_created_at", "created_at"),
        Index("ix_invoice_updated_at", "updated_at"),
        Index("ix_invoice_created_by", "created_by"),
        Index("ix_invoice_updated_by", "updated_by"),
        Index("ix_invoice_tenant_status", "tenant_id", "status"),
        CheckConstraint("student_count >= 0", name="check_invoice_student_count_non_negative"),
        CheckConstraint("amount_per_student >= 0", name="check_amount_per_student_non_negative"),
        CheckConstraint("total_amount >= 0", name="check_total_amount_non_negative"),
        {"schema": "billings"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    semester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester this invoice is for")

    # Invoice details (from Billing.tsx)
    description: Mapped[str] = mapped_column(String(255), nullable=False, comment="Invoice description e.g. 'Fall Semester 2024 - 2,500 students'")
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="Number of students billed")
    amount_per_student: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, comment="Amount per student in NGN")
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="Total invoice amount")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, tenant_id={self.tenant_id}, description={self.description}, total_amount={self.total_amount}, status={self.status.value})>"
    
    def to_dict(self):
        return {
            "id": str(self.id) if self.id else None,
            "tenant_id": str(self.tenant_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "description": self.description,
            "student_count": self.student_count,
            "amount_per_student": self.amount_per_student,
            "total_amount": self.total_amount,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }