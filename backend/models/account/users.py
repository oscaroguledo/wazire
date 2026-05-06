from __future__ import annotations

import uuid
from enum import Enum
from datetime import datetime

from sqlalchemy import String, Index, func, CheckConstraint, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from core.types.guid import GUID


from core.database import Base
from core.utils.uuid7 import uuid7


class UserRole(str, Enum):
    STUDENT = "student"
    LECTURER = "lecturer"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"  # App owner only


class User(Base):
    """User model with authentication and tenant support."""
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_is_active", "is_active"),
        Index("ix_users_institution_id", "institution_id"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_updated_at", "updated_at"),
        # Composite indexes
        Index("ix_users_tenant_role", "tenant_id", "role"),
        Index("ix_users_tenant_active", "tenant_id", "is_active"),
        Index("ix_users_email_tenant", "email", "tenant_id"),
        Index("ix_users_tenant_institution", "tenant_id", "institution_id"),
        {"schema": "account"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    first_name: Mapped[str] = mapped_column(String(100), comment="Given name")
    middle_name: Mapped[str] = mapped_column(String(100), nullable=True, comment="Middle name, optional")
    last_name: Mapped[str] = mapped_column(String(100), comment="Family name")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="Login email (unique)")
    password: Mapped[str] = mapped_column(String(255), comment="Hashed password")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role", create_type=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="User role enum")
    is_active: Mapped[bool] = mapped_column(default=False, comment="Account active flag")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=True, comment="FK: tenant id for multi-tenancy")
    institution_id: Mapped[str] = mapped_column(String(100), nullable=True, comment="Institution ID e.g., Student matric/registration number")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def full_name(self) -> str:
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "institution_id": self.institution_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }