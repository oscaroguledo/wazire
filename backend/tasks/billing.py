"""Kafka event handlers for billing operations.

Handles the ``INITIATE_BILLING`` event emitted by the end-of-semester
scheduler job.  The handler calls ``PaymentGatewayService.initiate()`` and
stores the resulting ``payment_url`` and ``payment_reference`` on the Invoice.
"""
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from core.utils.logger import logger
from tasks.utils import with_db


async def handle_initiate_billing(data: Dict[str, Any]) -> None:
    """Process an ``INITIATE_BILLING`` Kafka event.

    Expected payload keys:
    - ``invoice_id`` (required): UUID of the Invoice to initiate payment for.
    - ``tenant_id`` (required): UUID of the tenant being billed.
    - ``semester_id`` (optional): UUID of the semester this invoice covers.
    - ``payment_gateway`` (optional): ``"paystack"`` or ``"monnify"``.
      Defaults to Paystack if ``PAYSTACK_SECRET_KEY`` is configured.

    On success:
    - Calls ``PaymentGatewayService.initiate(invoice)``
    - Stores ``payment_url`` and ``payment_reference`` on the Invoice record

    On failure:
    - Logs the error and re-raises so the consumer can dead-letter the message.
    """
    invoice_id_raw = data.get("invoice_id")
    tenant_id_raw = data.get("tenant_id")

    if not invoice_id_raw:
        logger.warning("INITIATE_BILLING: missing invoice_id — data=%s", data)
        return

    try:
        invoice_id = UUID(str(invoice_id_raw))
    except (ValueError, AttributeError) as exc:
        logger.error("INITIATE_BILLING: invalid invoice_id '%s' — %s", invoice_id_raw, exc)
        return

    async def _run(db):
        from services.billings.invoice import InvoiceService
        from services.billing.payment_gateway import PaymentGatewayService, PaymentGatewayError

        svc = InvoiceService(db)
        invoice = await svc.get(invoice_id)
        if not invoice:
            logger.warning("INITIATE_BILLING: invoice %s not found", invoice_id)
            return

        # Honour the gateway hint from the payload if provided
        gateway_hint = data.get("payment_gateway")
        if gateway_hint and not invoice.payment_gateway:
            invoice.payment_gateway = gateway_hint

        try:
            gw_svc = PaymentGatewayService()
            result = await gw_svc.initiate(invoice)
        except PaymentGatewayError as exc:
            logger.error(
                "INITIATE_BILLING: gateway initiation failed (invoice=%s): %s",
                invoice_id, exc,
            )
            raise  # re-raise so consumer dead-letters the message

        # Persist the gateway response on the invoice
        await svc.update_payment_details(
            invoice_id,
            payment_url=result.payment_url,
            payment_reference=result.payment_reference,
            payment_gateway=result.gateway,
        )
        logger.info(
            "INITIATE_BILLING: payment initiated (invoice=%s gateway=%s reference=%s)",
            invoice_id, result.gateway, result.payment_reference,
        )

    try:
        await with_db(_run)
    except Exception:
        logger.exception("INITIATE_BILLING handler failed (invoice=%s)", invoice_id_raw)
        raise  # re-raise so consumer can dead-letter the message


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "INITIATE_BILLING": handle_initiate_billing,
}
