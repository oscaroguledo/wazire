from sqlalchemy import DateTime, String, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
import uuid

from core.database import Base
from core.types.guid import GUID
from core.utils.uuid7 import uuid7


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    PENDING = "pending"
class Semester(str, enum.Enum):
    FALL = "fall"
    SPRING = "spring"
    SUMMER = "summer"
    WINTER = "winter"
    INTERIM = "interim"
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    SIXTH = "sixth"
    SEVENTH = "seventh"
    EIGHTH = "eighth"

class Enrollment(Base):
    __tablename__ = "enrollments"
    # Ensure a student can only be enrolled in a course once
    __table_args__ = (
        Index('ix_enrollment_student_course', 'student_id', 'course_id'),
        Index('ix_enrollment_semester', 'semester'),
        Index('ix_enrollment_status', 'status'),
        Index('ix_enrollment_course_id', 'course_id'),
        # Composite indexes for common query patterns
        Index('ix_enrollment_student_status', 'student_id', 'status'),
        Index('ix_enrollment_course_status', 'course_id', 'status'),
        Index('ix_enrollment_student_semester', 'student_id', 'semester'),
        UniqueConstraint('student_id', 'course_id', name='uq_student_course'),
        {"schema": "academic"},
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7 time-ordered")
    student_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id"), nullable=False, comment="FK: Student user ID")
    course_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic.courses.id"), nullable=False, comment="FK: Course ID")
    semester: Mapped[Semester] = mapped_column(SQLEnum(Semester, name="semester_enum", create_type=True), nullable=False, default=Semester.FALL, comment="Academic semester")
    status: Mapped[EnrollmentStatus] = mapped_column(SQLEnum(EnrollmentStatus, name="enrollment_status", create_type=True), nullable=False, default=EnrollmentStatus.ACTIVE, comment="Current enrollment status")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp (timezone-aware)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp (timezone-aware)")

    # Relationships (selectin loading for async safety)
    student = relationship("User", foreign_keys=[student_id], back_populates="enrollments", lazy="selectin")
    course = relationship("Course", foreign_keys=[course_id], back_populates="enrollments", lazy="selectin")

    

    def __repr__(self):
        return f"<Enrollment(student_id={self.student_id}, course_id={self.course_id}, semester={self.semester.value}, status={self.status.value})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "student": self.student.to_dict(),
            "course": self.course.to_dict(),
            "semester": self.semester.value,
            "year": self.created_at.year,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
