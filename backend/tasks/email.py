"""Kafka event handler for outbound email."""
from __future__ import annotations

from typing import Any, Dict

from core.utils.logger import logger


async def handle_send_email(data: Dict[str, Any]) -> None:
    """Send a transactional email.

    Expected data keys: to, subject, body
    """
    to = data.get("to")
    subject = data.get("subject", "(no subject)")
    body = data.get("body", "")

    if not to:
        logger.warning("SEND_EMAIL: missing recipient — data=%s", data)
        return

    try:
        # TODO: replace with real SMTP / SES / SendGrid integration
        logger.info("Sending email to=%s subject=%s", to, subject)
    except Exception:
        logger.exception("SEND_EMAIL failed (to=%s)", to)
        raise
