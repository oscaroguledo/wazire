from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Index, func, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.types.guid import GUID

from core.database import Base
from core.utils.uuid7 import uuid7


# Association table for tenant admins (many-to-many)
tenant_admins = Table(
	"tenant_admins",
	Base.metadata,
	Column("tenant_id", GUID(), ForeignKey("account.tenants.id", ondelete="CASCADE"), primary_key=True),
	Column("user_id", GUID(), ForeignKey("account.users.id", ondelete="CASCADE"), primary_key=True),
	schema="account",
)


class Tenant(Base):
	"""Tenant model representing a single school / organization.

	Fields:
	- id: UUID primary key (uuid7 time-ordered)
	- name: Tenant display name
	- domain: Optional canonical domain (example.edu) — indexed and unique where applicable
	- admin_user_ids: optional list of admin user ids (many-to-many)
	- is_active: tenant enabled flag
	- created_at / updated_at timestamps
	"""

	__tablename__ = "tenants"
	__table_args__ = (
		Index("ix_tenants_domain", "domain", unique=True),
		Index("ix_tenants_is_active", "is_active"),
		Index("ix_tenants_name", "name"),
		Index("ix_tenants_created_at", "created_at"),
		Index("ix_tenants_updated_at", "updated_at"),
		{"schema": "account"},
	)

	id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
	name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Tenant display name")
	domain: Mapped[str] = mapped_column(String(255), nullable=True, comment="Canonical domain, e.g. example.edu")
	logo_url: Mapped[str] = mapped_column(String(255), nullable=True, comment="Optional logo URL")
	# Many-to-many association with users that are admins for this tenant
	# Association table defined below
	is_active: Mapped[bool] = mapped_column(default=True, comment="Tenant enabled flag")

	created_at: Mapped[datetime] = mapped_column(server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

	# Relationships (selectin loading for async safety)
	admins = relationship("User", secondary=tenant_admins, back_populates="admin_tenants", lazy="selectin")
	invoices = relationship("Invoice", back_populates="tenant", lazy="selectin")
	usage = relationship("CurrentUsage", back_populates="tenant", uselist=False, lazy="selectin")
	payment_methods = relationship("PaymentMethod", back_populates="tenant", lazy="selectin")

	def __repr__(self) -> str:
		return f"<Tenant(id={self.id}, name={self.name}, domain={self.domain})>"

	def full_name(self) -> str:
		return self.name

	def to_dict(self) -> dict:
		return {
				"id": str(self.id) if self.id else None,
				"name": self.name,
				"domain": self.domain,
				"logo_url": self.logo_url,
				"is_active": self.is_active,
				"created_at": self.created_at.isoformat() if self.created_at else None,
				"updated_at": self.updated_at.isoformat() if self.updated_at else None,
				"admin_users": [u.to_dict() for u in self.admins],
				"invoices": [i.to_dict() for i in self.invoices],
				"usage": self.usage.to_dict() if self.usage else None,
				"payment_methods": [pm.to_dict() for pm in self.payment_methods],
			}
