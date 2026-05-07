"""Standalone scheduler process.

Run with:
    python scheduler.py

Publishes periodic Kafka events consumed by the worker (consumer.py).
Uses the shared producer from core.utils.kafka so SASL/SSL config is
applied consistently.
"""
from __future__ import annotations

import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import get_settings
from core.utils.kafka import producer_service
from core.utils.logger import logger

TOPIC = "tenant-tasks"


async def _trigger_exam_update() -> None:
    ok = await producer_service.publish_safe(TOPIC, "UPDATE_EXAM_STATUS", {})
    if not ok:
        logger.error("Failed to publish UPDATE_EXAM_STATUS")


async def _trigger_send_queued_emails() -> None:
    ok = await producer_service.publish_safe(TOPIC, "SEND_QUEUED_EMAILS", {})
    if not ok:
        logger.error("Failed to publish SEND_QUEUED_EMAILS")


async def run() -> None:
    settings = get_settings()

    await producer_service.start()
    logger.info("Scheduler producer started")

    scheduler = AsyncIOScheduler()

    exam_interval = settings.SCHEDULER_EXAM_STATUS_UPDATE_INTERVAL or 1
    email_interval = settings.SCHEDULER_EMAIL_SEND_INTERVAL or 1

    scheduler.add_job(_trigger_exam_update, "interval", minutes=exam_interval, id="exam_status")
    scheduler.add_job(_trigger_send_queued_emails, "interval", minutes=email_interval, id="queued_emails")

    scheduler.start()
    logger.info(
        "Scheduler running (exam_interval=%dm email_interval=%dm)",
        exam_interval, email_interval,
    )

    stop_event = asyncio.Event()

    def _handle_signal(*_):
        logger.info("Scheduler received shutdown signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown(wait=False)
        await producer_service.stop()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(run())
