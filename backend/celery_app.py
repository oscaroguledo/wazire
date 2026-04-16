from __future__ import annotations

from celery import Celery

from core.config import get_settings

settings = get_settings()

# Build broker URL with authentication if password is provided
broker_url = settings.CELERY_BROKER_URL or "redis://redis:6379/0"
if settings.REDIS_PASSWORD and "redis:" in broker_url and "@" not in broker_url:
    # Add password to Redis URL: redis://:password@host:port/db
    broker_url = broker_url.replace("redis://", f"redis://:{settings.REDIS_PASSWORD}@", 1)

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
    
    # Critical production settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Max 3 retries per task
    task_time_limit=3600,  # Hard timeout: 1 hour per task
    task_soft_time_limit=3000,  # Soft timeout: 50 minutes (allows cleanup)
    result_expires=3600,  # Task results expire after 1 hour (prevent memory leak)
    task_acks_late=True,  # Ack only after task completes (better reliability)
    worker_prefetch_multiplier=1,  # Disable prefetch (better for long tasks)
    
    # Monitoring and metrics
    task_track_started=True,  # Track task start time
    task_send_sent_event=True,  # Send task-sent events
    worker_send_sent_event=True,  # Send worker-sent events
    
    # Dead letter queue for failed tasks
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    task_remote_error_tracebacks=True,  # Include tracebacks in error reports
    
    beat_schedule={
        "update-exam-status-every-minute": {
            "task": "tasks.scheduler.update_exam_statuses_task",
            "schedule": settings.CELERY_EXAM_STATUS_UPDATE_INTERVAL,
        },
        "send-queued-emails-every-minute": {
            "task": "tasks.email.send_queued_emails_task",
            "schedule": settings.CELERY_EMAIL_SEND_INTERVAL,
        },
    },
)

celery_app.autodiscover_tasks(["tasks"])
