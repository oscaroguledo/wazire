from __future__ import annotations

import uuid
from enum import Enum
from datetime import datetime, timezone

from sqlalchemy import String, Index, func, CheckConstraint, DateTime, ForeignKey, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


from core.database import Base
from uuid_utils import uuid7


class SemesterStatus(str, Enum):
    """Semester status options."""
    UPCOMING = "upcoming"
    ACTIVE = "active"
    ENDED = "ended"


class SemesterType(str, Enum):
    """Semester type/number options."""
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"  # Summer semester for institutions with 3 semesters


class Semester(Base):
    """
    Tracks each school's semester periods.
    Each semester triggers a billing cycle based on student_count × ₦2,000.
    """
    __tablename__ = "semesters"
    __table_args__ = (
        Index("ix_semesters_tenant_id", "tenant_id"),
        Index("ix_semesters_start_date", "start_date"),
        Index("ix_semesters_status", "status"),
        {"schema": "billings"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to school/tenant")

    # Semester identity
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, comment="e.g. '2024/2025'")
    semester_number: Mapped[SemesterType] = mapped_column(SAEnum(SemesterType, name="semester_type_enum", create_type=True),nullable=False, comment="first | second | third (for 3-semester institutions)")
    label: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. 'First Semester 2024/2025'")

    # Date range
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="When semester begins")
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="When semester ends")

    # Status
    status: Mapped[SemesterStatus] = mapped_column(SAEnum(SemesterStatus, name="semester_status_enum", create_type=True),nullable=False, default=SemesterStatus.UPCOMING, comment="upcoming | active | ended")

    # Billing snapshot — captured at semester start
    student_count_snapshot: Mapped[int] = mapped_column(nullable=False, default=0, comment="Student count locked in at billing time")
    fee_per_student: Mapped[int] = mapped_column(nullable=False, default=2000, comment="Fee in Naira at time of billing (₦2,000 default)")
    total_amount_due: Mapped[int] = mapped_column(nullable=False, default=0, comment="student_count_snapshot × fee_per_student")
    is_billed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Whether invoice has been generated for this semester")
    billed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="When the invoice was generated")

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"))
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"))


    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "academic_year": self.academic_year,
            "semester_number": self.semester_number.value,
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "status": self.status.value,
            "student_count_snapshot": self.student_count_snapshot,
            "fee_per_student": self.fee_per_student,
            "total_amount_due": self.total_amount_due,
            "is_billed": self.is_billed,
            "billed_at": self.billed_at.isoformat() if self.billed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }

    def __repr__(self):
        return f"<Semester({self.label}, tenant={self.tenant_id}, status={self.status})>"

class UserRole(str, Enum):
    STUDENT = "student"
    LECTURER = "lecturer"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"  # App owner only


class User(Base):
    """User model for authentication and profile.
    
    Fields:
    - id: UUID primary key (uuid7 time-ordered)
    - first_name, middle_name, last_name: User name fields
    - email: Login email (unique)
    - password: Hashed password
    - role: User role enum (admin, lecturer, student)
    - is_active: Account active flag
    - is_locked: Account locked flag - students locked until semester software fees are paid
    - tenant_id: FK to tenant for multi-tenancy
    - institution_id: Institution ID (e.g., matric number)
    - created_at / updated_at timestamps
    - created_by / updated_by: Audit fields
    """
    __tablename__ = "users"
    __table_args__ = (
        # Keep composite indexes that match common query patterns and
        # remove redundant single-column indexes (low-cardinality or
        # covered by composites) to reduce write/storage overhead.
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_updated_at", "updated_at"),
        Index("ix_users_created_by", "created_by"),
        Index("ix_users_updated_by", "updated_by"),
        # Composite indexes (retain)
        Index("ix_users_tenant_role", "tenant_id", "role"),
        Index("ix_users_tenant_active", "tenant_id", "is_active"),
        Index("ix_users_email_tenant", "email", "tenant_id"),
        Index("ix_users_tenant_institution", "tenant_id", "institution_id"),
        {"schema": "account"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    first_name: Mapped[str] = mapped_column(String(100), comment="Given name")
    middle_name: Mapped[str] = mapped_column(String(100), nullable=True, comment="Middle name, optional")
    last_name: Mapped[str] = mapped_column(String(100), comment="Family name")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="Login email (unique)")
    password: Mapped[str] = mapped_column(String(255), comment="Hashed password")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role", create_type=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="User role enum")
    is_active: Mapped[bool] = mapped_column(default=False, comment="Account active flag")
    is_deleted: Mapped[bool] = mapped_column(default=False, comment="Soft delete flag")
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="Soft delete timestamp")
    is_locked: Mapped[bool] = mapped_column(default=True, comment="Account locked flag - students locked until semester software fees are paid")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=True, comment="FK: tenant id for multi-tenancy")
    institution_id: Mapped[str] = mapped_column(String(100), nullable=True, comment="Institution ID e.g., Student matric/registration number")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def full_name(self) -> str:
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def delete(self):
        """Soft delete user by setting is_active to False and is_locked to True."""
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted user by setting is_active to True."""
        self.is_active = True
        self.is_deleted = False
        self.deleted_at = None
        self.updated_at = datetime.now(timezone.utc)
    
    def lock(self):
        """Lock user account (e.g., for students with unpaid fees)."""
        self.is_locked = True
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "institution_id": str(self.institution_id) if self.institution_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }