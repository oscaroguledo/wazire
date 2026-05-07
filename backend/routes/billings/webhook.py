from __future__ import annotations

import uuid
from typing import Optional
import hmac
import hashlib

from fastapi import APIRouter, Depends, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.middleware.auth import get_token_service, create_auth_dependency
from core.utils.response import Response
from core.config import get_settings
from services.billings.invoice import InvoiceService
from tasks.email import queue_send_email
from models.account.users import User

router = APIRouter(prefix="/billings", tags=["billings"])


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(create_auth_dependency(get_token_service())),
):
    """Mark an invoice PAID.

    Permission: allow admins or the user who originally created the invoice.
    """
    svc = InvoiceService(db)
    inv = await svc.get(invoice_id)
    if not inv:
        return Response(success=False, error="Invoice not found", status_code=status.HTTP_404_NOT_FOUND)

    # Allow admins to mark paid; also allow the creating user to mark their own invoice
    try:
        from models.account.users import UserRole
        if getattr(current_user, "role", None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            # Not an admin — only allow if user created the invoice
            if str(current_user.id) != str(inv.created_by):
                return Response(success=False, error="Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    except Exception:
        # If role checking fails for any reason, deny access
        return Response(success=False, error="Forbidden", status_code=status.HTTP_403_FORBIDDEN)

    inv = await svc.mark_paid(invoice_id, updated_by=current_user.id)
    if not inv:
        return Response(success=False, error="Failed to mark invoice as paid", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Queue invoice email to invoice creator if available
    try:
        if inv.created_by:
            res = await db.execute(select(User).where(User.id == inv.created_by))
            user = res.scalar_one_or_none()
            if user and user.email:
                await queue_send_email(
                    to=user.email,
                    subject=f"Invoice #{inv.id} paid",
                    template="invoice",
                    template_vars={
                        "invoice_html": f"<p>Invoice {inv.id} marked PAID.</p>",
                        "invoice_number": str(inv.id),
                    },
                )
    except Exception:
        # best-effort
        pass

    return Response(success=True, message="Invoice marked as paid", data=inv.to_dict())


@router.post("/invoices/{invoice_id}/webhook")
async def invoice_payment_webhook(
    invoice_id: uuid.UUID,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Payment-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint for external payment providers to notify invoice payments.

    Expects `X-Payment-Signature` header to match `PAYMENT_WEBHOOK_SECRET` from settings.
    Marks invoice PAID and queues the invoice email.
    """
    settings = get_settings()
    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", None)
    if secret:
        body = await request.body()
        # Secret may be a SecretStr — extract raw value
        try:
            secret_val = secret.get_secret_value()
        except Exception:
            secret_val = str(secret)

        expected = hmac.new(secret_val.encode(), body, hashlib.sha256).hexdigest()
        header_val = x_signature or ""
        # Accept common prefixes like 'sha256=...'
        if header_val.startswith("sha256="):
            header_val = header_val.split("=", 1)[1]

        if not hmac.compare_digest(expected, header_val):
            return Response(success=False, error="Invalid signature", status_code=status.HTTP_401_UNAUTHORIZED)

    svc = InvoiceService(db)
    inv = await svc.mark_paid(invoice_id)
    if not inv:
        return Response(success=False, error="Invoice not found", status_code=status.HTTP_404_NOT_FOUND)

    # Queue email to creator (best-effort)
    try:
        if inv.created_by:
            res = await db.execute(select(User).where(User.id == inv.created_by))
            user = res.scalar_one_or_none()
            if user and user.email:
                await queue_send_email(
                    to=user.email,
                    subject=f"Invoice #{inv.id} paid",
                    template="invoice",
                    template_vars={
                        "invoice_html": f"<p>Invoice {inv.id} paid via webhook.</p>",
                        "invoice_number": str(inv.id),
                    },
                )
    except Exception:
        pass

    return Response(success=True, message="Invoice marked as paid via webhook", data=inv.to_dict())
