import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, func, Integer, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from uuid_utils import uuid7


class LecturerDashboard(Base):
    """Dashboard metrics for lecturers.
    
    Aggregates data from courses, exams, enrollments, and submissions
    to provide lecturer-level analytics.
    """

    __tablename__ = "lecturer_dashboard"
    __table_args__ = (
        Index("ix_lecturer_dashboard_lecturer_id", "lecturer_id"),
        Index("ix_lecturer_dashboard_tenant_id", "tenant_id"),
        Index("ix_lecturer_dashboard_created_at", "created_at"),
        Index("ix_lecturer_dashboard_updated_at", "updated_at"),
        Index("ix_lecturer_dashboard_created_by", "created_by"),
        Index("ix_lecturer_dashboard_updated_by", "updated_by"),
        {"schema": "analytics"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    lecturer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False, comment="FK to lecturer user")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    
    # Course metrics
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total courses assigned to lecturer")
    active_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Courses with active enrollments")
    
    # Student metrics
    total_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total students enrolled in lecturer's courses")
    
    # Exam metrics
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total exams in lecturer's courses")
    
    # Submission metrics
    pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions awaiting grading")
    graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions already graded")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")

    def __repr__(self):
        return f"<LecturerDashboard(id={self.id}, lecturer_id={self.lecturer_id})>" 
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "lecturer_id": str(self.lecturer_id),
            "tenant_id": str(self.tenant_id),
            "total_courses": self.total_courses,
            "active_courses": self.active_courses,
            "total_students": self.total_students,
            "total_exams": self.total_exams,
            "pending_submissions": self.pending_submissions,
            "graded_submissions": self.graded_submissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }


class AdminDashboard(Base):
    """Dashboard metrics for tenant admins.
    
    Aggregates platform-wide metrics for tenant-level administration.
    """

    __tablename__ = "admin_dashboard"
    __table_args__ = (
        Index("ix_admin_dashboard_tenant_id", "tenant_id"),
        Index("ix_admin_dashboard_created_at", "created_at"),
        Index("ix_admin_dashboard_updated_at", "updated_at"),
        Index("ix_admin_dashboard_created_by", "created_by"),
        Index("ix_admin_dashboard_updated_by", "updated_by"),
        {"schema": "analytics"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, unique=True, comment="FK to tenant (one dashboard per tenant)")
    
    # User metrics
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total users in tenant")
    total_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total students in tenant")
    total_lecturers: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total lecturers in tenant")
    
    # Course metrics
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total courses in tenant")
    
    # Exam metrics
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total exams in tenant")
    
    # Submission metrics
    total_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total submissions in tenant")
    pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions awaiting grading")
    graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions already graded")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")
    
    def __repr__(self):
        return f"<AdminDashboard(id={self.id}, tenant_id={self.tenant_id})>" 
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "total_users": self.total_users,
            "total_students": self.total_students,
            "total_lecturers": self.total_lecturers,
            "total_courses": self.total_courses,
            "total_exams": self.total_exams,
            "total_submissions": self.total_submissions,
            "pending_submissions": self.pending_submissions,
            "graded_submissions": self.graded_submissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }


class StudentDashboard(Base):
    """Dashboard metrics for students.
    
    Aggregates data from enrollments, exams, and submissions
    to provide student-level analytics.
    """

    __tablename__ = "student_dashboard"
    __table_args__ = (
        Index("ix_student_dashboard_student_id", "student_id"),
        Index("ix_student_dashboard_tenant_id", "tenant_id"),
        Index("ix_student_dashboard_created_at", "created_at"),
        Index("ix_student_dashboard_updated_at", "updated_at"),
        Index("ix_student_dashboard_created_by", "created_by"),
        Index("ix_student_dashboard_updated_by", "updated_by"),
        {"schema": "analytics"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False, unique=True, comment="FK to student user (one dashboard per student)")
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.tenants.id", ondelete="CASCADE"), nullable=False, comment="FK to tenant")
    
    # Course metrics
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total courses enrolled")
    active_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Active enrollments")
    completed_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Completed courses")
    
    # Exam metrics
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total exams in enrolled courses")
    upcoming_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Exams with start_time in future")
    missed_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Exams with start_time in past and no submission")
    
    # Submission metrics
    total_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total submissions made")
    graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions with graded status")
    pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Submissions with pending/submitted status")
    average_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True, comment="Average score across all graded submissions")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who created this record")
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account.users.id", ondelete="SET NULL"), nullable=True, comment="FK: user who last updated this record")

    def __repr__(self):
        return f"<StudentDashboard(id={self.id}, student_id={self.student_id})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "tenant_id": str(self.tenant_id),
            "total_courses": self.total_courses,
            "active_courses": self.active_courses,
            "completed_courses": self.completed_courses,
            "total_exams": self.total_exams,
            "upcoming_exams": self.upcoming_exams,
            "missed_exams": self.missed_exams,
            "total_submissions": self.total_submissions,
            "graded_submissions": self.graded_submissions,
            "pending_submissions": self.pending_submissions,
            "average_score": float(self.average_score) if self.average_score else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
