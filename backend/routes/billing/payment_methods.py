"""Payment method CRUD routes under /api/v1/billing/payment-methods."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import create_auth_dependency, get_token_service, require_admin
from core.utils.response import Response
from services.billings.payment_methods import PaymentMethodService

router = APIRouter(prefix="/billing/payment-methods", tags=["billing"])


@router.get("/")
async def list_payment_methods(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    offset = (page - 1) * per_page
    items, total = await svc.list(
        limit=per_page,
        offset=offset,
        tenant_id=current_user.tenant_id,
    )
    return Response(
        success=True,
        message="Payment methods retrieved",
        data=[m.to_dict() for m in items],
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.get("/{method_id}")
async def get_payment_method(
    method_id: uuid.UUID,
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    method = await svc.get(method_id, tenant_id=current_user.tenant_id)
    if not method:
        return Response(success=False, error="Payment method not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Payment method retrieved", data=method.to_dict(), request=request)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    method = await svc.create(body, tenant_id=current_user.tenant_id, created_by=current_user.id)
    return Response(success=True, message="Payment method created", data=method.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.put("/{method_id}")
async def update_payment_method(
    method_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    method = await svc.get(method_id, tenant_id=current_user.tenant_id)
    if not method:
        return Response(success=False, error="Payment method not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await svc.update(method, body, updated_by=current_user.id)
    return Response(success=True, message="Payment method updated", data=updated.to_dict(), request=request)


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    method_id: uuid.UUID,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    method = await svc.get(method_id, tenant_id=current_user.tenant_id)
    if not method:
        return Response(success=False, error="Payment method not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await svc.delete(method)
    return Response(success=True, message="Payment method deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{method_id}/set-default")
async def set_default_payment_method(
    method_id: uuid.UUID,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = PaymentMethodService(db)
    method = await svc.set_default(method_id, tenant_id=current_user.tenant_id)
    if not method:
        return Response(success=False, error="Payment method not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Default payment method updated", data=method.to_dict(), request=request)
