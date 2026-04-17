from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import uuid
from typing import Optional, List

from core.database import get_db
from core.utils.response import Response
from core.utils.logger import logger
from core.middleware.error_handler import NotFoundError, BadRequestError, ForbiddenError
from core.dependencies.pagination import get_pagination, PaginationParams, PaginationResponse
from models.account.users import User, UserRole
from models.academic.course import Course
from models.academic.enrollment import Enrollment
from schemas.academic.enrollment import (
    EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse,
    EnrollmentListResponse, EnrollmentListParams, EnrollmentStatus, EnrollmentCheckResponse,
    BulkEnrollmentRequest, Semester
)
from core.dependencies.common import authenticated_dep, get_token_service, lecturer_or_admin_dep
from services.academic.enrollment import EnrollmentService
from tasks.submission import refresh_dashboard_task

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


@router.get("/")
async def list_enrollment(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    search: Optional[str] = Query(None, description="Search term"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    lecturer_id: Optional[uuid.UUID] = Query(None, description="Filter by lecturer ID"),
    enrollment_status: Optional[EnrollmentStatus] = Query(None, description="Filter by status"),
    semester: Optional[Semester] = Query(None, description="Filter by semester"),
    current_user: User = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    """List enrollments with standardized pagination and filters."""
    try:
        enrollment_service = EnrollmentService(db)

        # Get tenant_id from current_user (admins can access all tenants)
        tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

        # Build params object
        params = EnrollmentListParams(
            page=pagination.page,
            per_page=pagination.per_page,
            search=search,
            student_id=student_id,
            course_id=course_id,
            lecturer_id=lecturer_id,
            status=enrollment_status,
            semester=semester
        )

        # Get enrollments with pagination
        items, total = await enrollment_service.list_enrollments(params, tenant_id=tenant_id)

        # Create pagination metadata
        pagination_meta = PaginationResponse.create(
            page=pagination.page,
            per_page=pagination.per_page,
            total=total
        )

        # Convert to response format
        items_dicts = [item.to_dict() for item in items]
        
        return Response(success=True, data=items_dicts, pagination=pagination_meta.model_dump(), request=request)
    except Exception as e:
        logger.error(f"list_enrollments error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(success=False, error=f"Failed to fetch enrollments: {str(e)}", request=request, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.get("/{enrollment_id}")
async def get_enrollment(
    enrollment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Get a specific enrollment by ID.
    
    - Students can only see their own enrollments
    - Lecturers can only see enrollments for their courses
    - Admins can see all enrollments
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    try:
        enrollment = await enrollment_service.get_enrollment(enrollment_id, tenant_id=tenant_id)
        
        # Role-based access check
        if current_user.role == UserRole.STUDENT and str(enrollment.student_id) != str(current_user.id):
            raise ForbiddenError("Can only access your own enrollments")
        elif current_user.role == UserRole.LECTURER and str(enrollment.course.lecturer_id) != str(current_user.id):
            raise ForbiddenError("Can only access enrollments for your courses")
        
        return Response(success=True, data=enrollment.to_dict(), request=request, status_code=status.HTTP_200_OK)
    except ValueError as e:
        raise NotFoundError(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch enrollment: {str(e)}"
        )

@router.post("/", status_code=status.HTTP_201_CREATED)
async def enroll_student(
    request: Request,
    enrollment_data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = lecturer_or_admin_dep
):
    """
    Enroll a student in a course.
    
    - Only lecturers can enroll students in their courses
    - Lecturers can only enroll students in courses they teach
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    logger.debug(f"enroll_student called by {current_user.email} (role: {current_user.role})")
    logger.debug(f"enrollment_data: student_id={enrollment_data.student_id}, course_id={enrollment_data.course_id}")

    try:
        enrollment = await enrollment_service.enroll_student(enrollment_data, current_user, tenant_id=tenant_id)
        
        # Refresh dashboards in background
        student_uuid = uuid.UUID(enrollment_data.student_id)
        # Get course to find lecturer
        course_stmt = select(Course).where(Course.id == uuid.UUID(enrollment_data.course_id))
        course_result = await db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        
        # Refresh student dashboard in background (enqueue Celery task)
        refresh_dashboard_task.delay(str(student_uuid))
        # Refresh lecturer dashboard if course has a lecturer (enqueue Celery task)
        if course and course.lecturer_id:
            refresh_dashboard_task.delay(str(course.lecturer_id))
        
        return Response(success=True, data=enrollment.to_dict(), request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        error_msg = str(e)
        print(f"[DEBUG] ValueError: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        print(f"[DEBUG] Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enroll student: {str(e)}"
        )

@router.put("/{enrollment_id}")
async def update_enrollment(
    enrollment_id: uuid.UUID,
    enrollment_data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Update an enrollment.
    
    - Students can only update their own enrollment status (e.g., drop course)
    - Lecturers can update enrollments for their courses (grades, status)
    - Admins can update any enrollment
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    try:
        # Get existing enrollment for access check
        existing_enrollment = await enrollment_service.get_enrollment(enrollment_id, tenant_id=tenant_id)
        
        # Role-based access check
        if current_user.role == UserRole.STUDENT and str(existing_enrollment.student_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own enrollments"
            )
        elif current_user.role == UserRole.LECTURER and str(existing_enrollment.course.lecturer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update enrollments for your courses"
            )

        enrollment = await enrollment_service.update_enrollment(enrollment_id, enrollment_data, tenant_id=tenant_id)
        return Response(success=True, data=enrollment.to_dict(), request=request, status_code=status.HTTP_200_OK)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update enrollment: {str(e)}"
        )

@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_enrollment(
    enrollment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = lecturer_or_admin_dep
):
    """
    Remove a student from a course.
    
    - Only lecturers can remove students from courses
    - Lecturers can only remove students from courses they teach
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    try:
        # Get enrollment before deletion to get student and lecturer IDs
        enrollment_stmt = select(Enrollment).where(Enrollment.id == uuid.UUID(enrollment_id))
        enrollment_result = await db.execute(enrollment_stmt)
        enrollment = enrollment_result.scalar_one_or_none()

        await enrollment_service.remove_enrollment(enrollment_id, current_user, tenant_id=tenant_id)
        
        # Refresh dashboards in background
        if enrollment:
            # Refresh student dashboard in background (enqueue Celery task)
                refresh_dashboard_task.delay(str(enrollment.student_id))
                # Refresh lecturer dashboard in background (enqueue Celery task)
                if enrollment.course and enrollment.course.lecturer_id:
                    refresh_dashboard_task.delay(str(enrollment.course.lecturer_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove enrollment: {str(e)}"
        )

@router.get("/student/{student_id}")
async def get_student_enrollments(
    student_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Get enrollments for a specific student.
    
    - Students can only see their own enrollments
    - Lecturers can only see enrollments for their courses
    - Admins can see all student enrollments
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    # Role-based access check
    if current_user.role == UserRole.STUDENT and str(current_user.id) != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only access your own enrollments"
        )

    params = EnrollmentListParams(
        page=page,
        per_page=per_page,
        search=search,
        student_id=student_id,
        status=enrollment_status
    )

    try:
        items, total = await enrollment_service.list_enrollments(params, tenant_id=tenant_id)
        # Convert models to dicts
        items_dicts = [item.to_dict() for item in items]
        
        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        has_next = page < pages
        has_prev = page > 1
        
        return Response(success=True, data={
            "items": items_dicts,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch student enrollments: {str(e)}"
        )

@router.get("/course/{course_id}")
async def get_course_enrollments(
    course_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    semester: Optional[Semester] = Query(None, description="Filter by semester"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Filter by academic year"),
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Get enrollments for a specific course.
    
    - Students can see enrollments for their enrolled courses
    - Lecturers can see enrollments for their courses
    - Admins can see all course enrollments
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    params = EnrollmentListParams(
        page=page,
        per_page=per_page,
        search=search,
        course_id=course_id,
        status=enrollment_status,
        semester=semester,
        year=year
    )

    try:
        items, total = await enrollment_service.list_enrollments(params, tenant_id=tenant_id)
        # Convert models to dicts
        items_dicts = [item.to_dict() for item in items]
        
        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        has_next = page < pages
        has_prev = page > 1
        
        return Response(success=True, data={
            "items": items_dicts,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course enrollments: {str(e)}"
        )

@router.get("/lecturer/{lecturer_id}")
async def get_lecturer_enrollments(
    lecturer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    enrollment_status: Optional[EnrollmentStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Get enrollments for courses taught by a specific lecturer.
    
    - Lecturers can only see their own course enrollments
    - Admins can see all lecturer enrollments
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    # Role-based access check
    if current_user.role == UserRole.LECTURER and current_user.id != lecturer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only access your own course enrollments"
        )

    params = EnrollmentListParams(
        page=page,
        per_page=per_page,
        search=search,
        lecturer_id=lecturer_id,
        status=enrollment_status
    )

    try:
        items, total = await enrollment_service.list_enrollments(params, tenant_id=tenant_id)
        # Convert models to dicts
        items_dicts = [item.to_dict() for item in items]
        
        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        has_next = page < pages
        has_prev = page > 1
        
        
        return Response(success=True,data={
            "items": items_dicts,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lecturer enrollments: {str(e)}"
        )

@router.post("/bulk/", status_code=status.HTTP_201_CREATED)
async def bulk_enroll_students(
    bulk_request: BulkEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = lecturer_or_admin_dep
):
    """
    Bulk enroll multiple students in courses.
    
    - Only lecturers can bulk enroll students in courses
    - Lecturers can only enroll students in courses they teach
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    try:
        enrollments = await enrollment_service.bulk_enroll(bulk_request.enrollments, current_user, tenant_id=tenant_id)
        return Response(success=True, data=[e.to_dict() for e in enrollments], request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk enroll students: {str(e)}"
        )

@router.get("/check/")
async def check_enrollment(
    student_id: uuid.UUID = Query(..., description="Student ID"),
    course_id: uuid.UUID = Query(..., description="Course ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = authenticated_dep
):
    """
    Check if a student is enrolled in a course.
    
    - Students can only check their own enrollment status
    - Lecturers can check enrollment for their courses
    - Admins can check any enrollment
    """
    enrollment_service = EnrollmentService(db)

    # Get tenant_id from current_user (admins can access all tenants)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id

    # Role-based access check
    if current_user.role == UserRole.STUDENT and str(current_user.id) != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only check your own enrollment status"
        )

    try:
        result = await enrollment_service.check_enrollment(student_id, course_id, tenant_id=tenant_id)
        return Response(success=True, data=result.to_dict(), request=request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check enrollment: {str(e)}"
        )
