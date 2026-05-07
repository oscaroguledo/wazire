"""Payment gateway webhook handlers.

Endpoints:
- POST /api/v1/billing/webhooks/paystack  — Paystack charge events
- POST /api/v1/billing/webhooks/monnify   — Monnify payment events

Both endpoints:
1. Verify the HMAC signature using the respective secret key.
2. On a successful payment event, mark the Invoice as PAID and call
   ``SemesterService.mark_billed()`` atomically.
3. Return HTTP 200 to acknowledge receipt (Paystack/Monnify retry on non-200).
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db
from core.utils.logger import logger
from core.utils.response import Response
from models.billings.invoice import InvoiceStatus
from services.billings.invoice import InvoiceService
from services.billings.semesters import SemesterService

router = APIRouter(prefix="/billing/webhooks", tags=["billing-webhooks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_paystack_signature(body: bytes, signature: str, secret_key: str) -> bool:
    """Return True if the Paystack X-Paystack-Signature header matches the body."""
    expected = hmac.new(secret_key.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_monnify_signature(body: bytes, signature: str, secret_key: str) -> bool:
    """Return True if the Monnify monnify-signature header matches the body.

    Monnify uses HMAC-SHA512 over the raw request body.
    """
    expected = hmac.new(secret_key.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _mark_invoice_paid_and_semester_billed(
    db: AsyncSession,
    payment_reference: str,
    paid_at: datetime,
) -> bool:
    """Atomically mark an invoice as PAID and its semester as billed.

    Returns True on success, False if the invoice was not found.
    """
    invoice_svc = InvoiceService(db)
    semester_svc = SemesterService(db)

    invoice = await invoice_svc.get_by_reference(payment_reference)
    if not invoice:
        logger.warning(
            "Webhook: invoice with payment_reference='%s' not found", payment_reference
        )
        return False

    if invoice.status == InvoiceStatus.PAID:
        # Idempotent — already processed
        logger.info(
            "Webhook: invoice %s already marked PAID (idempotent)", invoice.id
        )
        return True

    # Update invoice
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = paid_at
    db.add(invoice)

    # Update semester (if linked)
    if invoice.semester_id:
        semester = await semester_svc.mark_billed(invoice.semester_id, billed_at=paid_at)
        if semester:
            db.add(semester)

    # Single atomic commit for both invoice and semester
    await db.commit()
    logger.info(
        "Webhook: invoice %s marked PAID (reference=%s semester=%s)",
        invoice.id, payment_reference, invoice.semester_id,
    )
    return True


# ---------------------------------------------------------------------------
# Paystack webhook
# ---------------------------------------------------------------------------

@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Paystack webhook events.

    Verifies the ``X-Paystack-Signature`` header using ``PAYSTACK_SECRET_KEY``.
    On ``charge.success``, marks the matching Invoice as PAID and the linked
    Semester as billed.

    Always returns HTTP 200 so Paystack does not retry unnecessarily.
    """
    settings = get_settings()
    body = await request.body()

    # Signature verification
    secret_key = settings.PAYSTACK_SECRET_KEY
    if secret_key:
        signature = request.headers.get("x-paystack-signature", "")
        if not signature:
            logger.warning("Paystack webhook: missing X-Paystack-Signature header")
            return Response(
                success=False,
                error="Missing signature",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not _verify_paystack_signature(body, signature, secret_key):
            logger.warning("Paystack webhook: invalid signature")
            return Response(
                success=False,
                error="Invalid signature",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    else:
        logger.warning(
            "Paystack webhook: PAYSTACK_SECRET_KEY not configured — skipping signature check"
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Paystack webhook: invalid JSON body")
        return Response(
            success=False,
            error="Invalid JSON",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    event = payload.get("event", "")
    data = payload.get("data", {})

    logger.info("Paystack webhook received: event=%s", event)

    if event == "charge.success":
        reference = data.get("reference")
        if not reference:
            logger.warning("Paystack charge.success: missing reference in payload")
            return Response(success=True, message="Acknowledged (no reference)", request=request)

        paid_at = datetime.now(timezone.utc)
        # Try to parse Paystack's paid_at timestamp
        raw_paid_at = data.get("paid_at") or data.get("paidAt")
        if raw_paid_at:
            try:
                paid_at = datetime.fromisoformat(raw_paid_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        found = await _mark_invoice_paid_and_semester_billed(db, reference, paid_at)
        if not found:
            # Return 200 anyway — Paystack should not retry for unknown references
            return Response(success=True, message="Acknowledged (invoice not found)", request=request)

    # Acknowledge all other events with 200
    return Response(success=True, message="Webhook received", request=request)


# ---------------------------------------------------------------------------
# Monnify webhook
# ---------------------------------------------------------------------------

@router.post("/monnify")
async def monnify_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Monnify webhook events.

    Verifies the ``monnify-signature`` header using ``MONNIFY_SECRET_KEY``.
    On a successful payment event (``SUCCESSFUL_TRANSACTION``), marks the
    matching Invoice as PAID and the linked Semester as billed.

    Always returns HTTP 200 so Monnify does not retry unnecessarily.
    """
    settings = get_settings()
    body = await request.body()

    # Signature verification
    secret_key = settings.MONNIFY_SECRET_KEY
    if secret_key:
        signature = request.headers.get("monnify-signature", "")
        if not signature:
            logger.warning("Monnify webhook: missing monnify-signature header")
            return Response(
                success=False,
                error="Missing signature",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not _verify_monnify_signature(body, signature, secret_key):
            logger.warning("Monnify webhook: invalid signature")
            return Response(
                success=False,
                error="Invalid signature",
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    else:
        logger.warning(
            "Monnify webhook: MONNIFY_SECRET_KEY not configured — skipping signature check"
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Monnify webhook: invalid JSON body")
        return Response(
            success=False,
            error="Invalid JSON",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    event_type = payload.get("eventType", "")
    event_data = payload.get("eventData", {})

    logger.info("Monnify webhook received: eventType=%s", event_type)

    # Monnify uses SUCCESSFUL_TRANSACTION for completed payments
    if event_type == "SUCCESSFUL_TRANSACTION":
        # Monnify's paymentReference is the reference we set during initiation
        reference = event_data.get("paymentReference") or event_data.get("transactionReference")
        if not reference:
            logger.warning("Monnify SUCCESSFUL_TRANSACTION: missing paymentReference in payload")
            return Response(success=True, message="Acknowledged (no reference)", request=request)

        paid_at = datetime.now(timezone.utc)
        raw_paid_at = event_data.get("completedOn") or event_data.get("paidOn")
        if raw_paid_at:
            try:
                # Monnify timestamps may be epoch millis or ISO strings
                if isinstance(raw_paid_at, (int, float)):
                    paid_at = datetime.fromtimestamp(raw_paid_at / 1000, tz=timezone.utc)
                else:
                    paid_at = datetime.fromisoformat(str(raw_paid_at).replace("Z", "+00:00"))
            except (ValueError, AttributeError, OSError):
                pass

        found = await _mark_invoice_paid_and_semester_billed(db, reference, paid_at)
        if not found:
            return Response(success=True, message="Acknowledged (invoice not found)", request=request)

    return Response(success=True, message="Webhook received", request=request)
