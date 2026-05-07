"""Billing plan CRUD routes under /api/v1/billing/plans."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import create_auth_dependency, get_token_service, require_admin
from core.utils.response import Response
from services.billings.billing_plans import BillingPlanService

router = APIRouter(prefix="/billing/plans", tags=["billing"])


@router.get("/")
async def list_billing_plans(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    from models.account.users import UserRole

    effective_tenant_id = tenant_id
    if getattr(current_user, "role", None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        effective_tenant_id = current_user.tenant_id

    svc = BillingPlanService(db)
    offset = (page - 1) * per_page
    items, total = await svc.list(
        limit=per_page,
        offset=offset,
        tenant_id=effective_tenant_id,
        is_active=is_active,
    )
    return Response(
        success=True,
        message="Billing plans retrieved",
        data=[p.to_dict() for p in items],
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.get("/{plan_id}")
async def get_billing_plan(
    plan_id: uuid.UUID,
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    from models.account.users import UserRole

    svc = BillingPlanService(db)
    tenant_id = None if getattr(current_user, "role", None) in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    plan = await svc.get(plan_id, tenant_id=tenant_id)
    if not plan:
        return Response(success=False, error="Billing plan not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Billing plan retrieved", data=plan.to_dict(), request=request)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_billing_plan(
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = BillingPlanService(db)
    tenant_id = body.pop("tenant_id", None) or current_user.tenant_id
    plan = await svc.create(body, tenant_id=uuid.UUID(str(tenant_id)), created_by=current_user.id)
    return Response(success=True, message="Billing plan created", data=plan.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.put("/{plan_id}")
async def update_billing_plan(
    plan_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = BillingPlanService(db)
    plan = await svc.get(plan_id)
    if not plan:
        return Response(success=False, error="Billing plan not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await svc.update(plan, body, updated_by=current_user.id)
    return Response(success=True, message="Billing plan updated", data=updated.to_dict(), request=request)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_plan(
    plan_id: uuid.UUID,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = BillingPlanService(db)
    plan = await svc.get(plan_id)
    if not plan:
        return Response(success=False, error="Billing plan not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await svc.delete(plan)
    return Response(success=True, message="Billing plan deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
