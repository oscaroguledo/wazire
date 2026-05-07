from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status, Request
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.middleware.auth import get_token_service, create_auth_dependency, require_lecturer_or_admin
from services.academic.courses import CourseService
from schemas.academic.course import CourseCreate, CourseUpdate
from schemas.account.users import UserRead
from models.account.users import UserRole, User
from models.academic.enrollment import Enrollment, EnrollmentStatus
from tasks.submission import emit_refresh_dashboard

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    """Create a new course (admin or lecturer)."""
    tenant_id = current_user.tenant_id
    if not tenant_id:
        return Response(success=False, error="No tenant assigned to your account", request=request, status_code=status.HTTP_403_FORBIDDEN)

    course_data = course_in.model_copy()

    # Admin can override tenant_id; lecturer is always assigned to their own tenant
    if course_data.tenant_id and current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
        tenant_id = course_data.tenant_id

    # Lecturers are automatically assigned as the lecturer of the course they create
    if current_user.role == UserRole.LECTURER:
        course_data.lecturer_id = current_user.id

    if not course_data.name or not course_data.name.strip():
        return Response(success=False, error="Course name is required", request=request, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    if not course_data.course_code or not course_data.course_code.strip():
        return Response(success=False, error="Course code is required", request=request, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    course = await service.create(course_data, tenant_id=tenant_id)
    
    # Refresh lecturer dashboard — await so publish failures are observable
    if course.lecturer_id:
        await emit_refresh_dashboard(str(course.lecturer_id))
    
    return Response(success=True, message="Course created", data=course.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.get("/")
async def list_courses(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    lecturer_id: Optional[uuid.UUID] = None,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    """List courses. Lecturers only see their own courses."""
    tenant_id = current_user.tenant_id
    offset = (page - 1) * per_page

    # Lecturers always see only their own courses — ignore any passed lecturer_id
    effective_lecturer_id = lecturer_id
    if current_user.role == UserRole.LECTURER:
        effective_lecturer_id = current_user.id

    items, total_count = await service.list(
        limit=per_page,
        offset=offset,
        tenant_id=tenant_id,
        lecturer_id=effective_lecturer_id,
    )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return Response(
        success=True,
        message="Courses retrieved",
        data=[item.to_dict() for item in items],
        page=page,
        per_page=per_page,
        total=total_count,
        request=request,
    )


@router.get("/{course_id}")
async def get_course(
    course_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    tenant_id = current_user.tenant_id
    course_data = await service.get(course_id, tenant_id)
    if not course_data:
        return Response(success=False, error="Course not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Course retrieved", data=course_data.to_dict(), request=request)


@router.put("/{course_id}")
async def update_course(
    course_id: uuid.UUID,
    course_in: CourseUpdate,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    tenant_id = current_user.tenant_id
    course_model = await service._get_model(course_id, tenant_id)
    if not course_model:
        return Response(success=False, error="Course not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    
    # Store old lecturer_id for dashboard refresh
    old_lecturer_id = course_model.lecturer_id
    
    updated = await service.update(course_model, course_in)
    
    # Refresh dashboards — await so publish failures are observable
    if old_lecturer_id and old_lecturer_id != updated.lecturer_id:
        await emit_refresh_dashboard(str(old_lecturer_id))
    if updated.lecturer_id:
        await emit_refresh_dashboard(str(updated.lecturer_id))
    
    return Response(success=True, message="Course updated", data=updated.to_dict(), request=request)


@router.get("/{course_id}/students")
async def get_course_students(
    course_id: uuid.UUID,
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Return all students enrolled in a course.

    Scoped to the requesting user's tenant. Restricted to admins and lecturers.
    Returns: student_id, first_name, last_name, enrollment.status for each enrolled student.
    """
    service = CourseService(db)
    tenant_id = current_user.tenant_id

    # Verify the course exists and belongs to the tenant
    course = await service.get(course_id, tenant_id)
    if not course:
        return Response(
            success=False,
            error="Course not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    offset = (page - 1) * per_page

    # Base filter: enrollments for this course scoped to tenant
    base_filter = [Enrollment.course_id == course_id]
    if tenant_id:
        base_filter.append(Enrollment.tenant_id == tenant_id)

    # Count total enrolled students
    count_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(*base_filter)
    )
    total = int(count_result.scalar_one())

    # Paginated query joining User for name fields
    stmt = (
        select(Enrollment, User)
        .join(User, User.id == Enrollment.student_id)
        .where(*base_filter)
        .order_by(User.last_name, User.first_name)
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    data = [
        {
            "student_id": str(enrollment.student_id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "enrollment_status": enrollment.status.value if enrollment.status else None,
        }
        for enrollment, user in rows
    ]

    return Response(
        success=True,
        message="Course students retrieved",
        data=data,
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    service = CourseService(db)
    tenant_id = current_user.tenant_id
    course_model = await service._get_model(course_id, tenant_id)
    if not course_model:
        return Response(success=False, error="Course not found or you don't have permission to delete it", request=request, status_code=status.HTTP_404_NOT_FOUND)
    
    # Store lecturer_id before deletion for dashboard refresh
    lecturer_id = course_model.lecturer_id
    
    await service.delete(course_model)
    
    # Refresh lecturer dashboard — await so publish failures are observable
    if lecturer_id:
        await emit_refresh_dashboard(str(lecturer_id))
    
    return Response(success=True, message="Course deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
