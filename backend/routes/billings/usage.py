"""Usage CRUD routes under /api/v1/billing/usage."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import create_auth_dependency, get_token_service, require_admin
from core.utils.response import Response
from services.billings.usage import UsageService

router = APIRouter(prefix="/billing/usage", tags=["billing"])


@router.get("/")
async def list_usage(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = UsageService(db)
    offset = (page - 1) * per_page
    items, total = await svc.list(
        limit=per_page,
        offset=offset,
        tenant_id=current_user.tenant_id,
    )
    return Response(
        success=True,
        message="Usage records retrieved",
        data=[u.to_dict() for u in items],
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.get("/current")
async def get_current_usage(
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get the current usage record for the authenticated user's tenant."""
    svc = UsageService(db)
    usage = await svc.get_for_tenant(current_user.tenant_id)
    if not usage:
        return Response(success=False, error="No usage record found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Current usage retrieved", data=usage.to_dict(), request=request)


@router.get("/{usage_id}")
async def get_usage(
    usage_id: uuid.UUID,
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = UsageService(db)
    usage = await svc.get(usage_id, tenant_id=current_user.tenant_id)
    if not usage:
        return Response(success=False, error="Usage record not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Usage record retrieved", data=usage.to_dict(), request=request)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_usage(
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = UsageService(db)
    usage = await svc.create(body, tenant_id=current_user.tenant_id, created_by=current_user.id)
    return Response(success=True, message="Usage record created", data=usage.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.put("/{usage_id}")
async def update_usage(
    usage_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = UsageService(db)
    usage = await svc.get(usage_id, tenant_id=current_user.tenant_id)
    if not usage:
        return Response(success=False, error="Usage record not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await svc.update(usage, body, updated_by=current_user.id)
    return Response(success=True, message="Usage record updated", data=updated.to_dict(), request=request)
