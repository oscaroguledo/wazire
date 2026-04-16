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


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoice_status", "status"),
        Index("ix_invoice_tenant_id", "tenant_id"),
        Index("ix_invoice_created_at", "created_at"),
        Index("ix_invoice_updated_at", "updated_at"),
        Index("ix_invoice_tenant_status", "tenant_id", "status"),
        CheckConstraint("student_count >= 0", name="check_invoice_student_count_non_negative"),
        CheckConstraint("amount_per_student >= 0", name="check_amount_per_student_non_negative"),
        CheckConstraint("total_amount >= 0", name="check_total_amount_non_negative"),
        {"schema": "billings"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="Number of students")
    amount_per_student: Mapped[int] = mapped_column(Integer, nullable=False, comment="Amount per student")
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="Total amount")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id"), nullable=False, comment="Tenant ID")
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), nullable=False, comment="Invoice status")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="When the record was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="When the record was last updated")
    
    # Relationships (selectin loading for async safety)
    tenant = relationship("Tenant", back_populates="invoices", lazy="selectin")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, student_count={self.student_count}, amount_per_student={self.amount_per_student}, total_amount={self.total_amount}, status={self.status.value})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "student_count": self.student_count,
            "amount_per_student": self.amount_per_student,
            "total_amount": self.total_amount,
            "tenant": self.tenant.to_dict() if self.tenant else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }