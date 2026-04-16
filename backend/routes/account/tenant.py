from __future__ import annotations

from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, authenticated_dep, admin_only_dep
from services.account.tenant import TenantService
from schemas.account.tenant import TenantCreate, TenantUpdate, TenantRead

router = APIRouter(prefix="/tenants", tags=["tenants"])


# Authentication dependencies


def get_tenant_service(
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service)
) -> TenantService:
    return TenantService(db, token_service=token_service)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Create a new tenant (admin only)."""
    # An admin can only have one institution
    if current_user.tenant_id:
        return Response(
            success=False,
            error="You already have an institution. An admin can only manage one institution.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if tenant name already exists
    existing_tenant = await service.get_by_name(tenant_in.name)
    if existing_tenant:
        return Response(
            success=False,
            error="Tenant name already exists",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if domain already exists (if provided)
    if tenant_in.domain:
        domain_tenant = await service.get_by_domain(tenant_in.domain)
        if domain_tenant:
            return Response(
                success=False,
                error="Domain already exists",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    # Always link the creating admin
    tenant_in.admin_user_ids = [current_user.id]
    tenant = await service.create(tenant_in)
    return Response(
        success=True,
        message="Tenant created successfully",
        data=TenantRead.model_validate(tenant),
        request=request,
        status_code=status.HTTP_201_CREATED
    )


@router.get("/")
async def list_tenants(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    cursor: Optional[str] = None,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """List tenants where current user is an admin using keyset pagination."""
    # Use keyset pagination
    tenants, next_cursor = await service.list_for_admin(
        admin_user_id=current_user.id,
        limit=per_page,
        cursor=cursor
    )
    
    return Response(
        success=True, 
        message="Tenants retrieved successfully", 
        data=[TenantRead.model_validate(t) for t in tenants], 
        pagination={
            "next_cursor": next_cursor,
            "has_next": next_cursor is not None,
            "per_page": per_page
        }, 
        request=request
    )


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Get tenant by ID (admin only)."""
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return Response(
        success=True,
        message="Tenant retrieved successfully",
        data=TenantRead.model_validate(tenant),
        request=request
    )


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: TenantUpdate,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Update tenant (admin only)."""
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Check if domain already exists (if being updated)
    if tenant_in.domain and tenant_in.domain != tenant.domain:
        domain_tenant = await service.get_by_domain(tenant_in.domain)
        if domain_tenant:
            return Response(
                success=False,
                error="Domain already exists",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    updated_tenant = await service.update(tenant, tenant_in)
    return Response(
        success=True,
        message="Tenant updated successfully",
        data=TenantRead.model_validate(updated_tenant),
        request=request
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Delete tenant (admin only)."""
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Check if tenant has users, courses, or exams before deletion
    stats = await service.get_tenant_stats(tenant_id)
    if stats.get("total_users", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated users. Please delete or reassign all users first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if stats.get("total_courses", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated courses. Please delete all courses first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if stats.get("total_exams", 0) > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated exams. Please delete all exams first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    await service.delete(tenant)
    return Response(
        success=True,
        message="Tenant deleted successfully",
        request=request
    )


@router.get("/{tenant_id}/users")
async def get_tenant_users(
    tenant_id: uuid.UUID,
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Get users in a tenant (admin only)."""
    tenant = await service.get(tenant_id)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    users = await service.get_tenant_users(tenant_id, limit=per_page, offset=(page - 1) * per_page)
    total_users = len(users)  # This should be replaced with actual count query
    
    return Response(
        success=True,
        message="Tenant users retrieved successfully",
        data=users,
        pagination=(page, per_page, total_users, str(request.url)),
        request=request
    )


@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: TenantRead = admin_only_dep,
    service: TenantService = Depends(get_tenant_service)
):
    """Get tenant statistics (admin only)."""
    # Check if user has access to this tenant
    if current_user.role == "admin" and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access statistics for your own tenant"
        )
    
    stats = await service.get_tenant_stats(tenant_id)
    
    return Response(
        success=True,
        message="Tenant statistics retrieved successfully",
        data=stats,
        request=request
    )