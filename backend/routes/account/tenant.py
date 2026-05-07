from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Depends, status, Query
from typing import Optional
from core.middleware.error_handler import ForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response, offset
from core.utils.token import TokenService
from core.middleware.auth import get_token_service, require_admin
from services.account.tenant import TenantService
from services.account.user import UserService
from schemas.account.tenant import TenantCreate, TenantUpdate, TenantRead, TenantDelete
from schemas.account.users import UserRead
from models.account.users import User
from models.academic.course import Course
from models.academic.exam import Exam
from sqlalchemy import select, func as sqlfunc
from tasks.email import queue_send_email

router = APIRouter(prefix="/tenants", tags=["tenants"])





@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    request: Request,
    current_user: UserRead = Depends(require_admin(get_token_service())),
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
    tenant = await service.create(tenant_in)
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
    current_user: UserRead = Depends(require_admin(get_token_service())),
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
    current_user: UserRead = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
    tenant_code: Optional[str] = Query(None, description="Optional tenant code for additional lookup"),
):
    """Get tenant by ID (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id, tenant_code=tenant_code)
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
    current_user: UserRead = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Update tenant (admin only). Service handles domain uniqueness check."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id, tenant_code=tenant_in.tenant_code)
    if not tenant:
        return Response(
            success=False,
            error="Tenant not found",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    tenant_in.id = tenant_id
    updated = await service.update(tenant_in)
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
    current_user: UserRead = Depends(require_admin(get_token_service())),
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

    total_users = int((await db.execute(select(sqlfunc.count(User.id)).where(User.tenant_id == tenant_id))).scalar_one())
    total_courses = int((await db.execute(select(sqlfunc.count(Course.id)).where(Course.tenant_id == tenant_id))).scalar_one())
    total_exams = int((await db.execute(select(sqlfunc.count(Exam.id)).where(Exam.tenant_id == tenant_id))).scalar_one())
    if total_users > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated users. Please delete or reassign all users first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if total_courses > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated courses. Please delete all courses first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if total_exams > 0:
        return Response(
            success=False,
            error="Cannot delete tenant with associated exams. Please delete all exams first.",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    tenant_delete = TenantDelete(id=tenant_id, updated_by=current_user.id)
    await service.delete(tenant_delete)
    # Notify the acting admin that the tenant was deleted
    try:
        await queue_send_email(to=current_user.email, subject=f"Tenant deleted: {tenant.name}", template="delete_tenant", template_vars={"tenant_name": tenant.name})
    except Exception:
        # Best-effort: log and continue
        from core.utils.logger import logger
        logger.exception("Failed to queue tenant-deleted email for tenant %s", tenant_id)
    return Response(
        success=True,
        message="Tenant deleted successfully",
        request=request,
    )


@router.post("/{tenant_id}/restore")
async def restore_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    """Restore a soft-deleted tenant (admin only)."""
    service = TenantService(db, token_service=token_service)
    tenant = await service.get(tenant_id, is_deleted=True)
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
    tenant_delete = TenantDelete(id=tenant_id, updated_by=current_user.id)
    restored = await service.restore(tenant_delete)
    return Response(
        success=True,
        message="Tenant restored successfully",
        data=restored.to_dict(),
        request=request,
    )
