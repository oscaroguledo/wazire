"""Student-scoped academic endpoints.

Provides read-only views of academic data from a student's perspective.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.middleware.auth import get_token_service, create_auth_dependency
from schemas.account.users import UserRead
from models.account.users import UserRole
from models.academic.enrollment import Enrollment, EnrollmentStatus
from models.academic.exam import Exam

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}/exams")
async def get_student_exams(
    student_id: uuid.UUID,
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Return all exams for courses the student is enrolled in.

    Access rules:
    - Students can only query their own student_id.
    - Admins and lecturers can query any student within their tenant.

    Scoped to the student's tenant.
    Returns: exam.id, title, start_time, end_time, status, duration for each exam.
    """
    # Students can only view their own exams
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        return Response(
            success=False,
            error="Students can only view their own exams",
            request=request,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Determine tenant scope
    tenant_id = current_user.tenant_id
    if current_user.role == UserRole.SUPERADMIN:
        tenant_id = None

    # Find all course IDs the student is enrolled in (active or completed)
    enrollment_stmt = select(Enrollment.course_id).where(
        Enrollment.student_id == student_id,
        Enrollment.status.in_([EnrollmentStatus.ACTIVE.value, EnrollmentStatus.COMPLETED.value]),
    )
    if tenant_id:
        enrollment_stmt = enrollment_stmt.where(Enrollment.tenant_id == tenant_id)

    enrollment_result = await db.execute(enrollment_stmt)
    course_ids = [row[0] for row in enrollment_result.all()]

    if not course_ids:
        return Response(
            success=True,
            message="No exams found",
            data=[],
            page=page,
            per_page=per_page,
            total=0,
            request=request,
        )

    offset = (page - 1) * per_page

    # Query exams for those courses
    exam_stmt = (
        select(Exam)
        .where(Exam.course_id.in_(course_ids))
        .order_by(Exam.start_time.desc().nullslast())
        .offset(offset)
        .limit(per_page)
    )
    if tenant_id:
        exam_stmt = exam_stmt.where(Exam.tenant_id == tenant_id)

    exam_result = await db.execute(exam_stmt)
    exams = exam_result.scalars().all()

    # Count total
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(Exam).where(Exam.course_id.in_(course_ids))
    if tenant_id:
        count_stmt = count_stmt.where(Exam.tenant_id == tenant_id)
    count_result = await db.execute(count_stmt)
    total = int(count_result.scalar_one())

    data = [
        {
            "id": str(e.id),
            "title": e.title,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "status": e.status.value if e.status else None,
            "duration": float(e.duration) if e.duration is not None else None,
            "course_id": str(e.course_id) if e.course_id else None,
        }
        for e in exams
    ]

    return Response(
        success=True,
        message="Student exams retrieved",
        data=data,
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )
