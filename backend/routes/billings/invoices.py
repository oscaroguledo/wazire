"""Invoice CRUD routes under /api/v1/billing/invoices."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import create_auth_dependency, get_token_service, require_admin
from core.utils.response import Response
from models.billings.invoice import InvoiceStatus
from services.billings.invoice import InvoiceService

router = APIRouter(prefix="/billing/invoices", tags=["billing"])


@router.get("/")
async def list_invoices(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    invoice_status: Optional[InvoiceStatus] = Query(None, alias="status"),
    tenant_id: Optional[uuid.UUID] = Query(None),
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """List invoices. Admins can filter by tenant; others see their own tenant."""
    from models.account.users import UserRole

    effective_tenant_id = tenant_id
    if getattr(current_user, "role", None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        effective_tenant_id = current_user.tenant_id

    svc = InvoiceService(db)
    offset = (page - 1) * per_page
    items, total = await svc.list(
        limit=per_page,
        offset=offset,
        tenant_id=effective_tenant_id,
        status=invoice_status,
    )
    return Response(
        success=True,
        message="Invoices retrieved",
        data=[i.to_dict() for i in items],
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    from models.account.users import UserRole

    svc = InvoiceService(db)
    tenant_id = None if getattr(current_user, "role", None) in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    inv = await svc.get(invoice_id, tenant_id=tenant_id)
    if not inv:
        return Response(success=False, error="Invoice not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Invoice retrieved", data=inv.to_dict(), request=request)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Create an invoice manually (admin only)."""
    svc = InvoiceService(db)
    tenant_id = body.pop("tenant_id", None) or current_user.tenant_id
    inv = await svc.create(body, tenant_id=uuid.UUID(str(tenant_id)), created_by=current_user.id)
    return Response(success=True, message="Invoice created", data=inv.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Update an invoice (admin only)."""
    svc = InvoiceService(db)
    inv = await svc.get(invoice_id)
    if not inv:
        return Response(success=False, error="Invoice not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await svc.update(inv, body, updated_by=current_user.id)
    return Response(success=True, message="Invoice updated", data=updated.to_dict(), request=request)


@router.post("/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Mark an invoice as paid (admin only)."""
    svc = InvoiceService(db)
    inv = await svc.mark_paid(invoice_id, updated_by=current_user.id)
    if not inv:
        return Response(success=False, error="Invoice not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Invoice marked as paid", data=inv.to_dict(), request=request)
