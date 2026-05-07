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
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import get_settings
from core.utils.kafka import producer_service
from core.utils.logger import logger
from core.database import get_db

TOPIC = "tenant-tasks"


async def _trigger_exam_update() -> None:
    ok = await producer_service.publish_safe(TOPIC, "UPDATE_EXAM_STATUS", {})
    if not ok:
        logger.error("Failed to publish UPDATE_EXAM_STATUS")


async def _trigger_send_queued_emails() -> None:
    ok = await producer_service.publish_safe(TOPIC, "SEND_QUEUED_EMAILS", {})
    if not ok:
        logger.error("Failed to publish SEND_QUEUED_EMAILS")


async def _trigger_preload_questions() -> None:
    """Detect exams starting within the next ~15 minutes and emit PRELOAD_QUESTIONS.

    Skips exams whose Redis preloaded sentinel key already exists so we don't
    double-emit for the same exam window.
    """
    from sqlalchemy import select
    from models.academic.exam import Exam, ExamStatus
    from core.database import get_redis_client

    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(minutes=15)

    redis = get_redis_client()

    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        stmt = (
            select(Exam)
            .where(
                Exam.start_time >= window_start,
                Exam.start_time <= window_end,
                Exam.status == ExamStatus.NOT_STARTED,
            )
        )
        result = await db.execute(stmt)
        exams = result.scalars().all()

        for exam in exams:
            exam_id = str(exam.id)
            sentinel_key = f"exam:{exam_id}:preloaded"

            # Skip if already preloaded
            if redis is not None:
                try:
                    already = await redis.exists(sentinel_key)
                    if already:
                        logger.debug("PRELOAD_QUESTIONS: exam %s already preloaded, skipping", exam_id)
                        continue
                except Exception:
                    logger.warning("Redis check failed for exam %s — emitting anyway", exam_id)

            duration_seconds = int(float(exam.duration) * 3600) if exam.duration else 3600
            ok = await producer_service.publish_safe(
                TOPIC,
                "PRELOAD_QUESTIONS",
                {
                    "exam_id": exam_id,
                    "duration_seconds": duration_seconds,
                    "tenant_id": str(exam.tenant_id),
                },
            )
            if ok:
                logger.info("PRELOAD_QUESTIONS emitted for exam %s", exam_id)
            else:
                logger.error("Failed to publish PRELOAD_QUESTIONS for exam %s", exam_id)

    except Exception:
        logger.exception("_trigger_preload_questions failed")
    finally:
        await db_gen.aclose()


async def _trigger_billing() -> None:
    """Detect ended unbilled semesters and emit INITIATE_BILLING for each.

    Queries ``billings.semesters`` for rows where:
    - ``end_date <= now()``
    - ``is_billed = False``
    - ``status = 'ended'``

    For each matching semester:
    1. Count active students for the tenant.
    2. Create an ``Invoice`` record with ``status='pending'``.
    3. Emit ``INITIATE_BILLING`` so the worker calls the payment gateway.
    """
    from sqlalchemy import select, func as sqlfunc
    from models.account.users import Semester, SemesterStatus, User, UserRole
    from models.billings.invoice import Invoice, InvoiceStatus
    from core.database import get_db

    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Find ended, unbilled semesters
        result = await db.execute(
            select(Semester).where(
                Semester.end_date <= now,
                Semester.is_billed.is_(False),
                Semester.status == SemesterStatus.ENDED,
            )
        )
        semesters = result.scalars().all()

        if not semesters:
            logger.debug("Billing job: no unbilled ended semesters found")
            return

        for semester in semesters:
            try:
                # Count active students for this tenant
                student_count_result = await db.execute(
                    select(sqlfunc.count()).select_from(User).where(
                        User.tenant_id == semester.tenant_id,
                        User.role == UserRole.STUDENT,
                        User.is_active.is_(True),
                    )
                )
                student_count = int(student_count_result.scalar_one())

                fee_per_student = semester.fee_per_student or 2000
                total_amount = student_count * fee_per_student

                description = f"{semester.label} — {student_count:,} students × ₦{fee_per_student:,}"

                # Create the invoice
                invoice = Invoice(
                    tenant_id=semester.tenant_id,
                    semester_id=semester.id,
                    description=description,
                    student_count=student_count,
                    amount_per_student=fee_per_student,
                    total_amount=total_amount,
                    status=InvoiceStatus.PENDING,
                )
                db.add(invoice)
                await db.flush()  # get invoice.id

                # Emit INITIATE_BILLING
                ok = await producer_service.publish_safe(
                    TOPIC,
                    "INITIATE_BILLING",
                    {
                        "invoice_id": str(invoice.id),
                        "tenant_id": str(semester.tenant_id),
                        "semester_id": str(semester.id),
                    },
                )
                if ok:
                    logger.info(
                        "INITIATE_BILLING emitted (semester=%s tenant=%s invoice=%s students=%d)",
                        semester.id, semester.tenant_id, invoice.id, student_count,
                    )
                else:
                    logger.error(
                        "Failed to publish INITIATE_BILLING for semester %s", semester.id
                    )

            except Exception:
                logger.exception("Billing job: failed to process semester %s", semester.id)
                continue

        await db.commit()

    except Exception:
        await db.rollback()
        logger.exception("_trigger_billing failed")
    finally:
        await db_gen.aclose()


async def _trigger_force_submit_exams() -> None:
    """Detect expired in-progress exams and emit FORCE_SUBMIT_EXAM for each.

    An exam is considered expired when start_time + duration <= now() and
    its status is still 'in_progress'.
    """
    from sqlalchemy import select
    from models.academic.exam import Exam, ExamStatus

    now = datetime.now(timezone.utc)

    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        result = await db.execute(
            select(Exam).where(Exam.status == ExamStatus.IN_PROGRESS)
        )
        exams = result.scalars().all()

        for exam in exams:
            if not exam.start_time or not exam.duration:
                continue

            start = exam.start_time
            if start.tzinfo is None:
                # Defensive: skip naive timestamps (they should be rejected at
                # schema layer per task 8.8, but guard here too)
                logger.error(
                    "FORCE_SUBMIT: exam %s has naive start_time — skipping", exam.id
                )
                continue

            end = start + timedelta(hours=float(exam.duration))
            if now >= end:
                ok = await producer_service.publish_safe(
                    TOPIC,
                    "FORCE_SUBMIT_EXAM",
                    {
                        "exam_id": str(exam.id),
                        "tenant_id": str(exam.tenant_id),
                    },
                )
                if ok:
                    logger.info("FORCE_SUBMIT_EXAM emitted for exam %s", exam.id)
                else:
                    logger.error("Failed to publish FORCE_SUBMIT_EXAM for exam %s", exam.id)

    except Exception:
        logger.exception("_trigger_force_submit_exams failed")
    finally:
        await db_gen.aclose()


async def run() -> None:
    settings = get_settings()

    await producer_service.start()
    logger.info("Scheduler producer started")

    scheduler = AsyncIOScheduler()

    exam_interval = settings.SCHEDULER_EXAM_STATUS_UPDATE_INTERVAL or 1
    email_interval = settings.SCHEDULER_EMAIL_SEND_INTERVAL or 1
    preload_interval = int(getattr(settings, "SCHEDULER_PRELOAD_QUESTIONS_INTERVAL", None) or 2)
    force_submit_interval = int(getattr(settings, "SCHEDULER_FORCE_SUBMIT_INTERVAL", None) or 2)
    billing_interval = int(getattr(settings, "SCHEDULER_BILLING_INTERVAL", None) or 60)

    scheduler.add_job(_trigger_exam_update, "interval", minutes=exam_interval, id="exam_status")
    scheduler.add_job(_trigger_send_queued_emails, "interval", minutes=email_interval, id="queued_emails")
    scheduler.add_job(_trigger_preload_questions, "interval", minutes=preload_interval, id="preload_questions")
    scheduler.add_job(_trigger_force_submit_exams, "interval", minutes=force_submit_interval, id="force_submit_exams")
    scheduler.add_job(_trigger_billing, "interval", minutes=billing_interval, id="billing")
    # Outbox publishing has been removed per configuration — database triggers
    # and a Postgres LISTEN/pg_notify listener are used to forward DB changes
    # to Kafka instead.

    scheduler.start()
    logger.info(
        "Scheduler running (exam_interval=%dm email_interval=%dm "
        "preload_interval=%dm force_submit_interval=%dm billing_interval=%dm)",
        exam_interval, email_interval, preload_interval, force_submit_interval, billing_interval,
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
