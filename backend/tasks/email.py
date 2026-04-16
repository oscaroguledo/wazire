from __future__ import annotations

from typing import Any, Dict

from celery.utils.log import get_task_logger

from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.email.send_email_task")
def send_email_task(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Queueable email sender task.

    This is currently a scheduler-friendly stub and can be replaced with
    SMTP/provider integration without changing callers.
    """
    logger.info("Email queued to=%s subject=%s", to_email, subject)
    return {"queued": True, "to_email": to_email, "subject": subject}


@celery_app.task(name="tasks.email.send_queued_emails_task")
def send_queued_emails_task() -> Dict[str, Any]:
    """Periodic email scheduler hook executed by Celery beat."""
    logger.info("Periodic email scheduler tick")
    return {"processed": 0}
