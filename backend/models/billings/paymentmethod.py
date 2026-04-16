import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Index, func, DateTime, ForeignKey,JSON,Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.types.guid import GUID


from core.database import Base
from core.utils.uuid7 import uuid7


class PaymentMethodType(str, Enum):
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"
class PaymentMethodDetails(Base):
    __tablename__ = "payment_method_details"
    __table_args__ = (
        Index("ix_payment_method_details_payment_method_id", "payment_method_id"),
        {"schema": "billings"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    payment_method_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("billings.payment_methods.id"), nullable=False, comment="Foreign key to payment_methods")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Payment method details")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="When the record was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="When the record was last updated")
    
    # Relationships (selectin loading for async safety)
    payment_method = relationship("PaymentMethod", back_populates="details", lazy="selectin")
    
    def __repr__(self):
        return f"<PaymentMethodDetails(id={self.id}, payment_method_id={self.payment_method_id})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "payment_method_id": str(self.payment_method_id),
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        Index("ix_payment_methods_type", "type"),
        {"schema": "billings"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    type: Mapped[PaymentMethodType] = mapped_column(SAEnum(PaymentMethodType), nullable=False, comment="Payment method type")
    # Relationships (selectin loading for async safety)
    details: Mapped[PaymentMethodDetails] = relationship("PaymentMethodDetails", back_populates="payment_method", lazy="selectin")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id"), nullable=False, comment="Tenant ID")
    tenant = relationship("Tenant", back_populates="payment_methods", lazy="selectin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="When the record was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="When the record was last updated")
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, type={self.type.value})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type.value,
            "tenant": self.tenant.to_dict() if self.tenant else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }