from sqlalchemy import DateTime, String, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
import uuid

from core.database import Base
from core.types.guid import GUID
from uuid_utils import uuid7


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    PENDING = "pending"

class Enrollment(Base):
    """Enrollment model for student-course relationships.
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        Index('ix_enrollment_student_course', 'student_id', 'course_id'),
        Index('ix_enrollment_semester_id', 'semester_id'),
        Index('ix_enrollment_status', 'status'),
        Index('ix_enrollment_course_id', 'course_id'),
        Index('ix_enrollment_tenant_id', 'tenant_id'),
        Index('ix_enrollment_created_at', 'created_at'),
        Index('ix_enrollment_updated_at', 'updated_at'),
        Index('ix_enrollment_created_by', 'created_by'),
        Index('ix_enrollment_updated_by', 'updated_by'),
        # Composite indexes
        Index('ix_enrollment_student_status', 'student_id', 'status'),
        Index('ix_enrollment_course_status', 'course_id', 'status'),
        Index('ix_enrollment_student_semester', 'student_id', 'semester_id'),
        Index('ix_enrollment_tenant_semester_status', 'tenant_id', 'semester_id', 'status'),
        UniqueConstraint('student_id', 'course_id', 'semester_id', name='uq_student_course_semester'),
        {"schema": "academic"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    student_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id"), nullable=False, comment="FK: Student user ID")
    course_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.courses.id"), nullable=False, comment="FK: Course ID")
    semester_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("billings.semesters.id", ondelete="SET NULL"), nullable=True, comment="FK to semester from billings")
    status: Mapped[EnrollmentStatus] = mapped_column(SQLEnum(EnrollmentStatus, name="enrollment_status", create_type=True), nullable=False, default=EnrollmentStatus.ACTIVE, comment="Current enrollment status")
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.tenants.id"), nullable=False, comment="FK: Tenant ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=True, comment="FK: user who last updated this record")

    def __repr__(self):
        return f"<Enrollment(student_id={self.student_id}, course_id={self.course_id}, semester_id={self.semester_id}, status={self.status.value})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "course_id": str(self.course_id),
            "semester_id": str(self.semester_id) if self.semester_id else None,
            "year": self.created_at.year,
            "status": self.status.value,
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
