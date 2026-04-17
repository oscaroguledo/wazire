from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, status, Request, Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, lecturer_or_admin_dep, authenticated_dep
from services.academic.exam import ExamService
from tasks.submission import refresh_dashboard_task
from schemas.academic.exam import ExamCreate, ExamUpdate
from schemas.account.users import UserRead
from models.academic.course import Course
from models.academic.enrollment import Enrollment

router = APIRouter(prefix="/exams", tags=["exams"])


def _tenant(user: UserRead):
    return None if user.role == "superadmin" else user.tenant_id


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_in: ExamCreate,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    # PostgreSQL handles timezone-aware datetimes natively - no conversion needed
    exam_data = exam_in.model_copy()

    # Set tenant_id based on user role
    tenant_id = _tenant(current_user)
    if not tenant_id and current_user.role not in ("admin", "superadmin"):
        return Response(success=False, error="No tenant assigned to your account", request=request, status_code=status.HTTP_403_FORBIDDEN)

    # Override tenant_id if provided in payload for admins
    if exam_data.tenant_id and current_user.role in ("admin", "superadmin"):
        tenant_id = exam_data.tenant_id

    # course_id can be None for standalone exams
    exam = await service.create(exam_data, tenant_id=tenant_id)

    # Refresh lecturer dashboard in background
    if exam.course_id:
        course_stmt = select(Course).where(Course.id == exam.course_id)
        course_result = await service.db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            refresh_dashboard_task.delay(str(course.lecturer_id))

    return Response(success=True, message="Exam created", data=exam.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.get("/")
async def list_exams(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    course_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    """List exams with offset/limit pagination and optional course/status/year filter."""
    tenant_id = _tenant(current_user)
    
    # For lecturers, only show exams they teach (via course) or created
    lecturer_id = None
    if current_user.role == "lecturer":
        lecturer_id = current_user.id
    
    # For students, get their enrolled course IDs
    student_course_ids = None
    if current_user.role == "student":
        enrollment_stmt = select(Enrollment.course_id).where(
            Enrollment.student_id == current_user.id,
            Enrollment.status.in_(["active", "completed"])
        )
        enrollment_result = await db.execute(enrollment_stmt)
        student_course_ids = [row[0] for row in enrollment_result.all()]
        # If student has no enrollments, return empty list
        if not student_course_ids:
            return Response(
                success=True, 
                message="No exams found", 
                data=[], 
                pagination={
                    "page": page,
                    "per_page": per_page,
                    "total": 0,
                    "pages": 0,
                    "has_next": False,
                    "has_prev": False
                }, 
                request=request
            )
    
    # Calculate offset from page
    offset = (page - 1) * per_page

    # Use offset/limit pagination
    exams, _ = await service.list(
        limit=per_page,
        offset=offset,
        tenant_id=tenant_id,
        lecturer_id=lecturer_id,
        student_course_ids=student_course_ids,
        course_id=course_id,
        status=status,
        year=year
    )

    total_count = await service.count(tenant_id=tenant_id, lecturer_id=lecturer_id, student_course_ids=student_course_ids, status=status)

    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page

    return Response(
        success=True,
        message="Exams retrieved",
        data=[e.to_dict() for e in exams],
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        request=request
    )


@router.get("/years")
async def get_exam_years(
    request: Request,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    """Get list of unique years from exam start_times."""
    tenant_id = _tenant(current_user)
    years = await service.get_years(tenant_id=tenant_id)
    return Response(
        success=True,
        message="Exam years retrieved",
        data=years,
        request=request
    )


@router.get("/{exam_id}")
async def get_exam(
    exam_id: uuid.UUID,
    request: Request,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    exam = await service.get(exam_id, _tenant(current_user))
    if not exam:
        return Response(success=False, error="Exam not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Exam retrieved", data=exam.to_dict(), request=request)


@router.put("/{exam_id}")
async def update_exam(
    exam_id: uuid.UUID,
    exam_in: ExamUpdate,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    exam = await service.get(exam_id, _tenant(current_user))
    if not exam:
        return Response(success=False, error="Exam not found", request=request, status_code=status.HTTP_404_NOT_FOUND)

    # Store old course info for dashboard refresh
    old_course_id = exam.course_id

    # Handle start_time timezone conversion if provided
    if exam_in.start_time:
        exam_in.start_time = exam_in.start_time.astimezone(timezone.utc)

    # Auto-update exam status based on start_time and duration
    if exam_in.start_time and (exam_in.duration_hours is not None or exam_in.duration_minutes is not None):
        new_start_time = exam_in.start_time
        new_duration = exam.duration if exam.duration else Decimal("0")

        if exam_in.duration_hours is not None or exam_in.duration_minutes is not None:
            new_hours = exam_in.duration_hours if exam_in.duration_hours is not None else 0
            new_minutes = exam_in.duration_minutes if exam_in.duration_minutes is not None else 0
            new_duration = Decimal(new_hours) + Decimal(new_minutes) / Decimal(60)

        now = datetime.now(timezone.utc)
        comparison_start_time = new_start_time
        if comparison_start_time.tzinfo is None:
            comparison_start_time = comparison_start_time.replace(tzinfo=timezone.utc)

        if new_start_time and new_duration:
            end_time = comparison_start_time + timedelta(hours=float(new_duration))

            if now < comparison_start_time:
                exam_in.status = "not_started"
            elif now >= comparison_start_time and now < end_time:
                exam_in.status = "in_progress"
            elif now >= end_time:
                exam_in.status = "finished"

    updated = await service.update(exam, exam_in)

    # Refresh lecturer dashboards in background
    if old_course_id and old_course_id != updated.course_id:
        old_course_stmt = select(Course).where(Course.id == old_course_id)
        old_course_result = await service.db.execute(old_course_stmt)
        old_course = old_course_result.scalar_one_or_none()
        if old_course and old_course.lecturer_id:
            refresh_dashboard_task.delay(str(old_course.lecturer_id))
    if updated.course_id:
        new_course_stmt = select(Course).where(Course.id == updated.course_id)
        new_course_result = await service.db.execute(new_course_stmt)
        new_course = new_course_result.scalar_one_or_none()
        if new_course and new_course.lecturer_id:
            refresh_dashboard_task.delay(str(new_course.lecturer_id))

    return Response(success=True, message="Exam updated", data=updated.to_dict(), request=request)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: uuid.UUID,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = ExamService(db)
    exam = await service.get(exam_id, _tenant(current_user))
    if not exam:
        return Response(success=False, error="Exam not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    
    # Store course info before deletion for dashboard refresh
    course_id = exam.course_id
    
    await service.delete(exam)
    
    # Refresh lecturer dashboard in background
    if course_id:
        course_stmt = select(Course).where(Course.id == course_id)
        course_result = await service.db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            refresh_dashboard_task.delay(str(course.lecturer_id))
    
    return Response(success=True, message="Exam deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
