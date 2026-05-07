"""Kafka event handler and publisher helpers for outbound email."""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.utils.logger import logger
from core.utils.kafka import producer_service
from core.config import get_settings
from services.notifications import brevo


# Topic used by scheduler and tasks for tenant-related background jobs
TOPIC = "tenant-tasks"


async def queue_send_email(
    to: str,
    subject: str,
    body: Optional[str] = None,
    template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
) -> bool:
    """Enqueue an email send request onto Kafka.

    The worker (consumer) will call `handle_send_email` to actually send.
    Returns True if publish succeeded (best-effort), False otherwise.
    """
    data: Dict[str, Any] = {
        "to": to,
        "subject": subject,
    }
    if body is not None:
        data["body"] = body
    if template is not None:
        data["template"] = template
    if template_vars is not None:
        data["template_vars"] = template_vars

    ok = await producer_service.publish_safe(TOPIC, "SEND_EMAIL", data)
    if not ok:
        logger.error("Failed to queue SEND_EMAIL to=%s subject=%s", to, subject)
    return ok


async def handle_send_email(data: Dict[str, Any]) -> None:
    """Process a `SEND_EMAIL` Kafka event and send via Brevo.

    Supported payload keys:
    - `to` (required)
    - `subject`
    - `body` (raw HTML)
    - `template` (one of: `verify_email`, `invoice`, `delete_tenant`)
    - `template_vars` (dict injected into template)
    """
    to = data.get("to")
    if not to:
        logger.warning("SEND_EMAIL: missing recipient — data=%s", data)
        return

    subject = data.get("subject", "(no subject)")
    body = data.get("body")
    template = data.get("template")
    vars_ = data.get("template_vars") or {}

    try:
        settings = get_settings()
        # If templates are requested, use the convenience helpers
        if template:
            if template == "verify_email":
                verify_url = vars_.get("verify_url") or vars_.get("url")
                full_name = vars_.get("full_name")
                await brevo.send_verification_email(to, verify_url, full_name)
                logger.info("Sent verification email to=%s", to)
                return

            if template == "invoice":
                invoice_html = vars_.get("invoice_html") or vars_.get("invoice_html_snippet", "")
                invoice_number = vars_.get("invoice_number", "")
                await brevo.send_invoice_email(to, invoice_html, invoice_number)
                logger.info("Sent invoice email to=%s invoice=%s", to, invoice_number)
                return

            if template == "delete_tenant":
                tenant_name = vars_.get("tenant_name", "")
                await brevo.send_delete_tenant_email(to, tenant_name)
                logger.info("Sent tenant-delete email to=%s tenant=%s", to, tenant_name)
                return

        # Fallback: raw HTML body via Brevo send_email
        if body:
            await brevo.send_email(subject, to, body)
            logger.info("Sent raw HTML email to=%s subject=%s", to, subject)
            return

        # Nothing to send
        logger.warning("SEND_EMAIL: nothing to send (to=%s) — data=%s", to, data)
    except Exception:
        logger.exception("SEND_EMAIL failed (to=%s)", to)
        raise


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "SEND_EMAIL": handle_send_email,
}
