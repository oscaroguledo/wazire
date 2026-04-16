from __future__ import annotations

from celery import Celery

from core.config import get_settings

settings = get_settings()

broker_url = settings.CELERY_BROKER_URL or "redis://redis:6379/0"
result_backend = settings.CELERY_RESULT_BACKEND or broker_url

celery_app = Celery(
    "wazire",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "update-exam-status-every-minute": {
            "task": "tasks.scheduler_tasks.update_exam_statuses_task",
            "schedule": 60.0,
        },
        "send-queued-emails-every-minute": {
            "task": "tasks.email_tasks.send_queued_emails_task",
            "schedule": 60.0,
        },
    },
)

celery_app.autodiscover_tasks(["tasks"])
