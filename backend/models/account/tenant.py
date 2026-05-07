from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Index, func, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class Tenant(Base):
	"""Tenant model representing a single school / organization.

	Fields:
	- id: UUID primary key (uuid7 time-ordered)
	- name: Tenant display name
	- domain: Optional canonical domain (example.edu) — indexed and unique where applicable
	- admin_user_ids: optional list of admin user ids (many-to-many)
	- is_active: tenant enabled flag
	- is_deleted: Tenant deleted flag
	- deleted_at: Soft delete timestamp
	- created_at / updated_at timestamps
	"""

	__tablename__ = "tenants"
	__table_args__ = (
		Index("ix_tenants_domain", "domain", unique=True),
		Index("ix_tenants_is_active", "is_active"),
		Index("ix_tenants_deleted_at", "deleted_at"),
		Index("ix_tenants_name", "name"),
		Index("ix_tenants_tenant_code", "tenant_code", unique=True),
		Index("ix_tenants_start_date", "start_date"),
		Index("ix_tenants_end_date", "end_date"),
		Index("ix_tenants_created_at", "created_at"),
		Index("ix_tenants_updated_at", "updated_at"),
		Index("ix_tenants_created_by", "created_by"),
		Index("ix_tenants_updated_by", "updated_by"),
		{"schema": "account"},
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
	name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Tenant display name")
	domain: Mapped[str] = mapped_column(String(255), nullable=True, comment="Canonical domain, e.g. example.edu")
	logo_url: Mapped[str] = mapped_column(String(255), nullable=True, comment="Optional logo URL")
	tenant_code: Mapped[str] = mapped_column(String(6), unique=True, nullable=False, comment="6-char uppercase alphanumeric join code, auto-generated per tenant")
	is_active: Mapped[bool] = mapped_column(default=True, comment="Tenant enabled flag")
	is_deleted: Mapped[bool] = mapped_column(default=False, comment="Tenant deleted flag")
	deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="Soft delete timestamp")
	start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Tenant contract start date")
	end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Tenant contract end date")
	paystack_customer_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Paystack customer reference code")
	monnify_account_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Monnify account reference")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
	created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
	updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")

	def __repr__(self) -> str:
		return f"<Tenant(id={self.id}, name={self.name}, domain={self.domain})>"

	def full_name(self) -> str:
		return self.name

	def can_be_deleted(self, has_unpaid_invoices: bool = False, has_active_semesters: bool = False) -> tuple[bool, str]:
		"""Check if tenant can be soft deleted.
		
		Returns:
			tuple: (can_delete: bool, reason: str)
		"""
		if has_unpaid_invoices:
			return False, "Cannot delete tenant with unpaid invoices"
		
		if has_active_semesters:
			return False, "Cannot delete tenant with active semesters - wait for semester to end"
		
		return True, "Tenant can be deleted"

	def delete(self) -> None:
		"""Mark tenant as deleted."""
		self.deleted_at = datetime.now(timezone.utc)
		self.is_deleted = True
		self.is_active = False

	def restore(self) -> None:
		"""Restore a soft-deleted tenant."""
		self.deleted_at = None
		self.is_deleted = False
		self.is_active = True

	def to_dict(self) -> dict:
		return {
				"id": str(self.id) if self.id else None,
				"name": self.name,
				"domain": self.domain,
				"logo_url": self.logo_url,
				"tenant_code": self.tenant_code,
				"is_active": self.is_active,
				"is_deleted": self.is_deleted,
				"deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
				"start_date": self.start_date.isoformat() if self.start_date else None,
				"end_date": self.end_date.isoformat() if self.end_date else None,
				"paystack_customer_code": self.paystack_customer_code,
				"monnify_account_reference": self.monnify_account_reference,
				"created_at": self.created_at.isoformat() if self.created_at else None,
				"updated_at": self.updated_at.isoformat() if self.updated_at else None,
				"created_by": str(self.created_by) if self.created_by else None,
				"updated_by": str(self.updated_by) if self.updated_by else None,
			}
