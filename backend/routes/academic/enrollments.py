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
from tasks.submission import emit_refresh_dashboard
import traceback

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


@router.get("/")
async def list_enrollment(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    lecturer_id: Optional[uuid.UUID] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    semester: Optional[Semester] = Query(None),
    current_user: User = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = EnrollmentService(db)
        tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
        params = EnrollmentListParams(page=page, per_page=per_page, search=search, student_id=student_id, course_id=course_id, lecturer_id=lecturer_id, status=enrollment_status, semester=semester)
        items, total = await service.list(params, tenant_id=tenant_id)
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only check your own enrollment status")
    try:
        result = await service.check(student_id, course_id, tenant_id=tenant_id)
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only access your own enrollments")
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, student_id=student_id, status=enrollment_status)
    try:
        items, total = await service.list(params, tenant_id=tenant_id)
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, course_id=course_id, status=enrollment_status, semester=semester, year=year)
    try:
        items, total = await service.list(params, tenant_id=tenant_id)
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    if current_user.role == UserRole.LECTURER and current_user.id != lecturer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only access your own course enrollments")
    params = EnrollmentListParams(page=page, per_page=per_page, search=search, lecturer_id=lecturer_id, status=enrollment_status)
    try:
        items, total = await service.list(params, tenant_id=tenant_id)
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    try:
        enrollment = await service.get(enrollment_id, tenant_id=tenant_id)
        if current_user.role == UserRole.STUDENT and enrollment.student_id != current_user.id:
            raise ForbiddenError("Can only access your own enrollments")
        elif current_user.role == UserRole.LECTURER and enrollment.course.lecturer_id != current_user.id:
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    try:
        enrollment = await service.create(enrollment_data, current_user, tenant_id=tenant_id)
        await emit_refresh_dashboard(str(enrollment_data.student_id))
        course_result = await db.execute(select(Course).where(Course.id == enrollment_data.course_id))
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            await emit_refresh_dashboard(str(course.lecturer_id))
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    try:
        existing = await service.get(enrollment_id, tenant_id=tenant_id)
        if current_user.role == UserRole.STUDENT and existing.student_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update your own enrollments")
        elif current_user.role == UserRole.LECTURER and existing.course.lecturer_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update enrollments for your courses")
        enrollment = await service.update(enrollment_id, enrollment_data, tenant_id=tenant_id)
        # Emit dashboard refreshes if status or course/student association affects dashboards
        try:
            await emit_refresh_dashboard(str(enrollment.student_id))
            if enrollment.course and enrollment.course.lecturer_id:
                await emit_refresh_dashboard(str(enrollment.course.lecturer_id))
        except Exception:
            logger.exception("update_enrollment: failed to emit dashboard refreshes")
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    try:
        enrollment_result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
        enrollment = enrollment_result.scalar_one_or_none()
        await service.remove(enrollment_id, current_user, tenant_id=tenant_id)
        if enrollment:
            await emit_refresh_dashboard(str(enrollment.student_id))
            if enrollment.course and enrollment.course.lecturer_id:
                await emit_refresh_dashboard(str(enrollment.course.lecturer_id))
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
    tenant_id = None if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    try:
        enrollments = await service.bulk_create(bulk_request.enrollments, current_user, tenant_id=tenant_id)
        # Emit refresh for each created enrollment (students + lecturers)
        lecturers = set()
        for e in enrollments:
            try:
                await emit_refresh_dashboard(str(e.student_id))
                if e.course and e.course.lecturer_id:
                    lecturers.add(str(e.course.lecturer_id))
            except Exception:
                logger.exception("bulk_enroll_students: failed to emit refresh for student %s", e.student_id)
        for l in lecturers:
            try:
                await emit_refresh_dashboard(l)
            except Exception:
                logger.exception("bulk_enroll_students: failed to emit refresh for lecturer %s", l)
        return Response(success=True, data=[e.to_dict() for e in enrollments], request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
