from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.middleware.auth import (
    get_token_service,
    create_auth_dependency,
    require_admin,
    require_lecturer_or_admin,
    require_admin_or_superadmin,
)
from models.account.users import User, UserRole
from services.analytics.dashboard import DashboardService
from schemas.analytics.dashboard import (
    LecturerDashboardRead,
    AdminDashboardRead,
    StudentDashboardRead,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# -------------------------------------------------------------------------
# GET / - Get current user's dashboard (read-only)
# -------------------------------------------------------------------------

@router.get("/", status_code=status.HTTP_200_OK)
async def get_my_dashboard(
    request: Request,
    current_user: User = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard data for the currently authenticated user.

    Read-only: returns 404 if no dashboard row exists yet.
    Dashboard rows are created/updated exclusively by the REFRESH_DASHBOARD
    Kafka worker handler (OLAP/OLTP separation).
    """
    service = DashboardService(db)
    try:
        if current_user.role == UserRole.LECTURER:
            dashboard_model = await service.get_lecturer_dashboard(current_user.id)
        elif current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            dashboard_model = await service.get_admin_dashboard(current_user.tenant_id)
        else:
            dashboard_model = await service.get_student_dashboard(current_user.id)

        if dashboard_model is None:
            return Response(
                success=False,
                error="Dashboard not yet available. It will be populated shortly.",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------------
# GET /lecturer/{lecturer_id} - Get lecturer dashboard (read-only)
# -------------------------------------------------------------------------

@router.get("/lecturer/{lecturer_id}", status_code=status.HTTP_200_OK)
async def get_lecturer_dashboard(
    lecturer_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard for a specific lecturer (read-only).

    - Lecturers can only view their own dashboard.
    - Admins can view any lecturer's dashboard.
    """
    service = DashboardService(db)
    try:
        if current_user.role == UserRole.LECTURER and current_user.id != lecturer_id:
            return Response(
                success=False,
                error="Can only view your own dashboard",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        dashboard_model = await service.get_lecturer_dashboard(lecturer_id)
        if dashboard_model is None:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch lecturer dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------------
# GET /admin/{tenant_id} - Get admin dashboard (read-only, keyed by tenant)
# -------------------------------------------------------------------------

@router.get("/admin/{tenant_id}", status_code=status.HTTP_200_OK)
async def get_admin_dashboard(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard for a specific tenant (admin only, read-only)."""
    service = DashboardService(db)
    try:
        if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            return Response(
                success=False,
                error="Admin access required",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        dashboard_model = await service.get_admin_dashboard(tenant_id)
        if dashboard_model is None:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch admin dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------------
# GET /student/{student_id} - Get student dashboard (read-only)
# -------------------------------------------------------------------------

@router.get("/student/{student_id}", status_code=status.HTTP_200_OK)
async def get_student_dashboard(
    student_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard for a specific student (read-only).

    - Students can only view their own dashboard.
    - Admins/lecturers can view any student's dashboard.
    """
    service = DashboardService(db)
    try:
        if (
            current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN)
            and current_user.id != student_id
        ):
            return Response(
                success=False,
                error="Can only view your own dashboard",
                request=request,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        dashboard_model = await service.get_student_dashboard(student_id)
        if dashboard_model is None:
            return Response(
                success=False,
                error="Dashboard not found",
                request=request,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(success=True, data=dashboard_model.to_dict(), request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch student dashboard: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# -------------------------------------------------------------------------
# GET /stats/tenant - Get tenant-specific stats (admin only, read-only)
# -------------------------------------------------------------------------

@router.get("/stats/tenant", status_code=status.HTTP_200_OK)
async def get_tenant_stats(
    request: Request,
    current_user: User = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for the current user's tenant (admin only, read-only)."""
    service = DashboardService(db)
    try:
        stats = await service.compute_admin_stats(tenant_id=current_user.tenant_id)
        return Response(success=True, data=stats, request=request)
    except Exception as e:
        return Response(
            success=False,
            error=f"Failed to fetch tenant stats: {str(e)}",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
