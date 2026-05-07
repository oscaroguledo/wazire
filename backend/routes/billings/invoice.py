from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import require_admin, get_token_service
from core.utils.response import Response
from services.billings.invoice import InvoiceService
from tasks.email import queue_send_email

router = APIRouter(prefix="/billings", tags=["billings"])


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin(get_token_service())),
):
    svc = InvoiceService(db)
    inv = await svc.mark_paid(invoice_id, updated_by=current_user.id)
    if not inv:
        return Response(success=False, error="Invoice not found", status_code=status.HTTP_404_NOT_FOUND)

    # Queue invoice email to invoice creator if available
    try:
        if inv.created_by:
            # Try to fetch the user email
            from sqlalchemy import select
            from models.account.users import User
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
