from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, authenticated_dep, admin_only_dep, lecturer_or_admin_dep, admin_or_superadmin_dep
from models.account.users import User, UserRole
from services.analytics.dashboard import DashboardService
from schemas.analytics.dashboard import (
    LecturerDashboardRead,
    AdminDashboardRead,
    StudentDashboardRead,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])




# -------------------------------------------------------------------------
# GET / - Get current user's dashboard
# -------------------------------------------------------------------------

@router.get("/", status_code=status.HTTP_200_OK)
async def get_my_dashboard(
    request: Request,
    current_user: User = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    """Get dashboard data for the currently authenticated user."""
    try:
        # Get the raw dashboard model and call to_dict()
        dashboard_model = await service.get_or_create_lecturer_dashboard(current_user.id) if current_user.role == UserRole.LECTURER else \
                          await service.get_or_create_admin_dashboard(current_user.id, current_user.tenant_id) if current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) else \
                          await service.get_or_create_student_dashboard(current_user.id)
        return Response(success=True, data=dashboard_model.to_dict() if dashboard_model else None, request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -------------------------------------------------------------------------
# GET /lecturer/{lecturer_id} - Get lecturer dashboard (admin/lecturer only)
# -------------------------------------------------------------------------

@router.get("/lecturer/{lecturer_id}", status_code=status.HTTP_200_OK)
async def get_lecturer_dashboard(
    lecturer_id: uuid.UUID,
    request: Request,
    current_user: User = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    """Get dashboard for a specific lecturer.
    
    - Lecturers can only view their own dashboard
    - Admins can view any lecturer's dashboard
    """
    try:
        # Access control
        if current_user.role == UserRole.LECTURER and current_user.id != lecturer_id:
            return Response(
                success=False,
                error="Can only view your own dashboard",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get raw dashboard model and call to_dict()
        dashboard_model = await service.get_or_create_lecturer_dashboard(lecturer_id)
        if not dashboard_model:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch lecturer dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -------------------------------------------------------------------------
# GET /admin/{admin_id} - Get admin dashboard (admin only)
# -------------------------------------------------------------------------

@router.get("/admin/{admin_id}", status_code=status.HTTP_200_OK)
async def get_admin_dashboard(
    admin_id: uuid.UUID,
    request: Request,
    current_user: User = admin_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    """Get dashboard for a specific admin (superadmin only)."""
    try:
        # Access control
        if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            return Response(
                success=False,
                error="Admin access required",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get raw dashboard model and call to_dict()
        dashboard_model = await service.get_or_create_admin_dashboard(admin_id)
        if not dashboard_model:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch admin dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -------------------------------------------------------------------------
# GET /student/{student_id} - Get student dashboard (self or admin)
# -------------------------------------------------------------------------

@router.get("/student/{student_id}", status_code=status.HTTP_200_OK)
async def get_student_dashboard(
    student_id: uuid.UUID,
    request: Request,
    current_user: User = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    """Get dashboard for a specific student.
    
    - Students can only view their own dashboard
    - Admins/lecturers can view any student's dashboard
    """
    try:
        # Access control
        if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN) and current_user.id != student_id:
            return Response(
                success=False,
                error="Can only view your own dashboard",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get raw dashboard model and call to_dict()
        dashboard_model = await service.get_or_create_student_dashboard(student_id)
        if not dashboard_model:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch student dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -------------------------------------------------------------------------
# GET /stats/tenant - Get tenant-specific stats (admin only)
# -------------------------------------------------------------------------

@router.get("/stats/tenant", status_code=status.HTTP_200_OK)
async def get_tenant_stats(
    request: Request,
    current_user: User = admin_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    """Get statistics for the current user's tenant (admin only)."""
    try:
        stats = await service.compute_admin_stats(tenant_id=current_user.tenant_id)
        return Response(success=True, data=stats, request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch tenant stats: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
