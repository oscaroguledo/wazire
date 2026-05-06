from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Depends, status
from core.middleware.error_handler import ForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, admin_only_dep
from core.dependencies.pagination import get_pagination, PaginationParams, PaginationResponse
from services.account.tenant import TenantService
from schemas.account.tenant import TenantCreate, TenantUpdate, TenantRead

router = APIRouter(prefix="/tenants", tags=["tenants"])





@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Create a new tenant (admin only)."""
    if current_user.tenant_id:
        return Response(
            success=False,
            error="You already have an institution. An admin can only manage one institution.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Always link the creating admin; service handles uniqueness checks
    service = TenantService(db, token_service=token_service)
    tenant_in.admin_user_ids = [current_user.id]
    tenant = await service.create(tenant_in, created_by=current_user.id)
    return Response(
        success=True,
        message="Tenant created successfully",
        data=tenant.to_dict(),
        request=request,
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/")
async def list_tenants(
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Get the current admin's tenant."""
    if not current_user.tenant_id:
        return Response(
            success=True,
            message="No tenant assigned",
            data=None,
            request=request,
        )
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(current_user.tenant_id)
    return Response(
        success=True,
        message="Tenant retrieved successfully",
        data=tenant.to_dict() if tenant else None,
        request=request,
    )


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Get tenant by ID (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        success=True,
        message="Tenant retrieved successfully",
        data=tenant.to_dict(),
        request=request,
    )


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: TenantUpdate,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Update tenant (admin only). Service handles domain uniqueness check."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    updated = await service.update(tenant, tenant_in, updated_by=current_user.id)
    return Response(
        success=True,
        message="Tenant updated successfully",
        data=updated.to_dict(),
        request=request,
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Soft-delete tenant (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    stats = await service.get_tenant_stats(tenant_id)
    if stats.get("total_users", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated users. Please delete or reassign all users first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if stats.get("total_courses", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated courses. Please delete all courses first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if stats.get("total_exams", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated exams. Please delete all exams first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    await service.delete(tenant, deleted_by=current_user.id)
    return Response(
        success=True,
        message="Tenant deleted successfully",
        request=request,
    )


@router.post("/{tenant_id}/restore")
async def restore_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Restore a soft-deleted tenant (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id, include_deleted=True)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if not tenant.is_deleted:
        return Response(
            success=False,
            error="Tenant is not deleted",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    restored = await service.restore(tenant, restored_by=current_user.id)
    return Response(
        success=True,
        message="Tenant restored successfully",
        data=restored.to_dict(),
        request=request,
    )


@router.get("/{tenant_id}/users")
async def get_tenant_users(
    tenant_id: uuid.UUID,
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Get users in a tenant (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    users, total = await service.get_tenant_users(
        tenant_id, limit=pagination.limit, offset=pagination.offset
    )
    return Response(
        success=True,
        message="Tenant users retrieved successfully",
        data=users,
        pagination=PaginationResponse.create(pagination.page, pagination.per_page, total),
        request=request,
    )


@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Get tenant statistics (admin only)."""
    service = TenantService(db, token_service=token_service)
    if current_user.role == "admin" and current_user.tenant_id != tenant_id:
        raise ForbiddenError("Access denied: You can only access statistics for your own tenant")

    stats = await service.get_tenant_stats(tenant_id)
    return Response(
        success=True,
        message="Tenant statistics retrieved successfully",
        data=stats,
        request=request,
    )
