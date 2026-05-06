
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Index, func, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.types.guid import GUID

from core.database import Base
from core.utils.uuid7 import uuid7


class LecturerDashboard(Base):
    __tablename__ = "lecturer_dashboard"
    __table_args__ = (
        Index("ix_lecturer_dashboard_lecturer_id", "lecturer_id"),
        Index("ix_lecturer_dashboard_created_at", "created_at"),
        Index("ix_lecturer_dashboard_updated_at", "updated_at"),
        {"schema": "analytics"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    lecturer_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("account.users.id"), nullable=False)
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships (noload to prevent loading - we don't need lecturer in dashboard response)
    lecturer = relationship("User", back_populates="lecturer_dashboard", lazy="noload")

    def __repr__(self):
        return f"<LecturerDashboard(id={self.id}, lecturer_id={self.lecturer_id})>" 
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "lecturer_id": str(self.lecturer_id),
            "total_courses": self.total_courses,
            "total_exams": self.total_exams,
            "total_students": self.total_students,
            "pending_submissions": self.pending_submissions,
            "graded_submissions": self.graded_submissions,
            "active_courses": self.active_courses,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class AdminDashboard(Base):
    __tablename__ = "admin_dashboard"
    __table_args__ = (
        Index("ix_admin_dashboard_admin_id", "admin_id"),
        Index("ix_admin_dashboard_created_at", "created_at"),
        Index("ix_admin_dashboard_updated_at", "updated_at"),
        {"schema": "analytics"},
    )
    
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    admin_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("account.users.id"), nullable=False)
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_lecturers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships (noload to prevent loading - we don't need admin in dashboard response)
    admin = relationship("User", back_populates="admin_dashboard", lazy="noload")
    
    def __repr__(self):
        return f"<AdminDashboard(id={self.id}, admin_id={self.admin_id})>" 
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "admin_id": str(self.admin_id),
            "total_users": self.total_users,
            "total_lecturers": self.total_lecturers,
            "total_students": self.total_students,
            "total_courses": self.total_courses,
            "total_exams": self.total_exams,
            "total_submissions": self.total_submissions,
            "total_graded_submissions": self.total_graded_submissions,
            "total_pending_submissions": self.total_pending_submissions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class StudentDashboard(Base):
    __tablename__ = "student_dashboard"
    __table_args__ = (
        Index("ix_student_dashboard_student_id", "student_id"),
        Index("ix_student_dashboard_created_at", "created_at"),
        Index("ix_student_dashboard_updated_at", "updated_at"),
        {"schema": "analytics"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    student_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("account.users.id"), nullable=False)
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_graded_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pending_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missed_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upcoming_exams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships (noload to prevent loading - we don't need student in dashboard response)
    student = relationship("User", back_populates="student_dashboard", lazy="noload")

    def __repr__(self):
        return f"<StudentDashboard(id={self.id}, student_id={self.student_id})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "student_id": str(self.student_id),
            "total_courses": self.total_courses,
            "total_exams": self.total_exams,
            "total_submissions": self.total_submissions,
            "total_graded_submissions": self.total_graded_submissions,
            "total_pending_submissions": self.total_pending_submissions,
            "missed_exams": self.missed_exams,
            "upcoming_exams": self.upcoming_exams,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
