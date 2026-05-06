from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Index, func, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class PaymentMethodType(str, Enum):
    """Payment method types matching Billing.tsx."""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    DIRECT_DEBIT = "direct_debit"
    OTHER = "other"


class PaymentMethod(Base):
    """Payment method model matching Billing.tsx PaymentMethodCard.
    """
    __tablename__ = "payment_methods"
    __table_args__ = (
        Index("ix_payment_methods_tenant_id", "tenant_id"),
        Index("ix_payment_methods_type", "type"),
        Index("ix_payment_methods_is_default", "is_default"),
        Index("ix_payment_methods_created_at", "created_at"),
        Index("ix_payment_methods_updated_at", "updated_at"),
        Index("ix_payment_methods_created_by", "created_by"),
        Index("ix_payment_methods_updated_by", "updated_by"),
        # Composite indexes
        Index("ix_payment_methods_tenant_type", "tenant_id", "type"),
        {"schema": "billings"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    
    # Payment method details
    type: Mapped[PaymentMethodType] = mapped_column(SAEnum(PaymentMethodType, name="payment_method_type_enum", create_type=True), nullable=False, comment="Payment method type")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Payment method details (card last4, expiry, bank info, etc.)")
    is_default: Mapped[bool] = mapped_column(default=False, comment="Is this the default payment method")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, tenant_id={self.tenant_id}, type={self.type.value}, is_default={self.is_default})>"
    
    def to_dict(self):
        return {
            "id": str(self.id) if self.id else None,
            "tenant_id": str(self.tenant_id),
            "type": self.type.value,
            "details": self.details,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }