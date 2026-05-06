from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import Optional, List

from core.database import get_db
from core.utils.response import Response, offset
from core.utils.logger import logger
from core.middleware.error_handler import NotFoundError, ForbiddenError
from models.account.users import User, UserRole
from models.academic.course import Course
from models.academic.enrollment import Enrollment
from schemas.academic.enrollment import (
    EnrollmentCreate, EnrollmentUpdate,
    EnrollmentListParams, EnrollmentStatus, Semester,
)
from core.middleware.auth import get_token_service, create_auth_dependency, require_lecturer_or_admin
from services.academic.enrollment import EnrollmentService
from tasks.submission import refresh_dashboard_task
import traceback

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


@router.get("/")
async def list_enrollment(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    lecturer_id: Optional[uuid.UUID] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    semester: Optional[Semester] = Query(None),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = EnrollmentService(db)
        tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
        params = EnrollmentListParams(page=page, per_page=per_page, search=search, student_id=student_id, course_id=course_id, lecturer_id=lecturer_id, status=enrollment_status, semester=semester)
        items, total = await service.list_enrollments(params, tenant_id=tenant_id)
        return Response(success=True, data=[i.to_dict() for i in items], page=page, per_page=per_page, total=total, request=request)
    except Exception as e:
        logger.error(f"list_enrollments error: {e}\n{traceback.format_exc()}")
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/check/")
async def check_enrollment(
    request: Request,
    student_id: uuid.UUID = Query(...),
    course_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    if current_user.role == UserRole.STUDENT and str(current_user.id) != str(student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only check your own enrollment status")
    try:
        result = await service.check_enrollment(student_id, course_id, tenant_id=tenant_id)
        return Response(success=True, data=result.to_dict(), request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/student/{student_id}")
async def get_student_enrollments(
    request: Request,
    student_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    if current_user.role == UserRole.STUDENT and str(current_user.id) != str(student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only access your own enrollments")
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, student_id=str(student_id), status=enrollment_status)
    try:
        items, total = await service.list_enrollments(params, tenant_id=tenant_id)
        return Response(success=True, data=[i.to_dict() for i in items], page=page, per_page=per_page, total=total, request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/course/{course_id}")
async def get_course_enrollments(
    request: Request,
    course_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    semester: Optional[Semester] = Query(None),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, course_id=str(course_id), status=enrollment_status, semester=semester, year=year)
    try:
        items, total = await service.list_enrollments(params, tenant_id=tenant_id)
        return Response(success=True, data=[i.to_dict() for i in items], page=page, per_page=per_page, total=total, request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/lecturer/{lecturer_id}")
async def get_lecturer_enrollments(
    request: Request,
    lecturer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    if current_user.role == UserRole.LECTURER and current_user.id != lecturer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only access your own course enrollments")
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, lecturer_id=lecturer_id, status=enrollment_status)
    try:
        items, total = await service.list_enrollments(params, tenant_id=tenant_id)
        return Response(success=True, data=[i.to_dict() for i in items], page=page, per_page=per_page, total=total, request=request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{enrollment_id}")
async def get_enrollment(
    request: Request,
    enrollment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    try:
        enrollment = await service.get_enrollment(enrollment_id, tenant_id=tenant_id)
        if current_user.role == UserRole.STUDENT and str(enrollment.student_id) != str(current_user.id):
            raise ForbiddenError("Can only access your own enrollments")
        elif current_user.role == UserRole.LECTURER and str(enrollment.course.lecturer_id) != str(current_user.id):
            raise ForbiddenError("Can only access enrollments for your courses")
        return Response(success=True, data=enrollment.to_dict(), request=request)
    except ValueError as e:
        raise NotFoundError(str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def enroll_student(
    request: Request,
    enrollment_data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer_or_admin(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    try:
        enrollment = await service.enroll_student(enrollment_data, current_user, tenant_id=tenant_id)
        refresh_dashboard_task.delay(str(enrollment_data.student_id))
        course_result = await db.execute(select(Course).where(Course.id == enrollment_data.course_id))
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            refresh_dashboard_task.delay(str(course.lecturer_id))
        return Response(success=True, data=enrollment.to_dict(), request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{enrollment_id}")
async def update_enrollment(
    request: Request,
    enrollment_id: uuid.UUID,
    enrollment_data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    try:
        existing = await service.get_enrollment(enrollment_id, tenant_id=tenant_id)
        if current_user.role == UserRole.STUDENT and str(existing.student_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update your own enrollments")
        elif current_user.role == UserRole.LECTURER and str(existing.course.lecturer_id) != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update enrollments for your courses")
        enrollment = await service.update_enrollment(enrollment_id, enrollment_data, tenant_id=tenant_id)
        return Response(success=True, data=enrollment.to_dict(), request=request)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_enrollment(
    enrollment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer_or_admin(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    try:
        enrollment_result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
        enrollment = enrollment_result.scalar_one_or_none()
        await service.remove_enrollment(enrollment_id, current_user, tenant_id=tenant_id)
        if enrollment:
            refresh_dashboard_task.delay(str(enrollment.student_id))
            if enrollment.course and enrollment.course.lecturer_id:
                refresh_dashboard_task.delay(str(enrollment.course.lecturer_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class BulkEnrollmentRequest(BaseModel):
    enrollments: List[EnrollmentCreate]


@router.post("/bulk/", status_code=status.HTTP_201_CREATED)
async def bulk_enroll_students(
    request: Request,
    bulk_request: BulkEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer_or_admin(get_token_service())),
):
    service = EnrollmentService(db)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    try:
        enrollments = await service.bulk_enroll(bulk_request.enrollments, current_user, tenant_id=tenant_id)
        return Response(success=True, data=[e.to_dict() for e in enrollments], request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
