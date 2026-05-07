"""Kafka event handlers for submission grading and dashboard refresh."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select

from core.database import get_db
from core.utils.logger import logger
from models.account.users import User, UserRole
from models.academic.submission import SubmissionAttempt
from sqlalchemy import select
from uuid import UUID

from .utils import with_db

TOPIC = "tenant-tasks"


async def handle_grade_submission_attempt(data: Dict[str, Any]) -> None:
    """Grade a submission attempt.

    Expected data keys: attempt_id, exam_id

    Idempotency: if the attempt already has a score set (i.e. it was graded in a
    previous delivery), the handler skips re-grading and returns immediately.
    This prevents score overwrites when Kafka redelivers a message after a crash
    between the DB commit and the offset commit.
    """
    attempt_id = data.get("attempt_id")
    exam_id = data.get("exam_id")

    if not attempt_id or not exam_id:
        logger.warning("GRADE_SUBMISSION_ATTEMPT: missing attempt_id or exam_id — data=%s", data)
        return


    async def _check_idempotency(db) -> bool:
        """Return True if the attempt is already graded (score is set)."""
        attempt = (await db.execute(
            select(SubmissionAttempt).where(SubmissionAttempt.id == UUID(attempt_id))
        )).scalar_one_or_none()
        if attempt is None:
            return False  # Not found — let the main handler log the warning
        return attempt.score is not None

    try:
        already_graded = await with_db(_check_idempotency)
    except Exception:
        logger.exception(
            "GRADE_SUBMISSION_ATTEMPT: idempotency check failed (attempt=%s) — proceeding with grading",
            attempt_id,
        )
        already_graded = False

    if already_graded:
        logger.info(
            "GRADE_SUBMISSION_ATTEMPT: attempt %s already graded — skipping redelivery (idempotent)",
            attempt_id,
        )
        return

    async def _run(db):
        from services.academic.submissions import SubmissionService
        svc = SubmissionService(db)
        await svc.grade_attempt_background(attempt_id, exam_id)

    try:
        await with_db(_run)
        logger.info("Graded attempt %s for exam %s", attempt_id, exam_id)
    except Exception:
        logger.exception("GRADE_SUBMISSION_ATTEMPT failed (attempt=%s exam=%s)", attempt_id, exam_id)
        raise  # re-raise so consumer can dead-letter log it


async def handle_refresh_dashboard(data: Dict[str, Any]) -> None:
    """Refresh a user's dashboard.

    Expected data keys: user_id
    """
    user_id_raw = data.get("user_id")
    if not user_id_raw:
        logger.warning("REFRESH_DASHBOARD: missing user_id — data=%s", data)
        return

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except ValueError:
        logger.error("REFRESH_DASHBOARD: invalid user_id '%s'", user_id_raw)
        return

    from .utils import with_db

    async def _run(db):
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            logger.warning("REFRESH_DASHBOARD: user %s not found", user_id)
            return

        from services.analytics.dashboard import DashboardService
        svc = DashboardService(db)

        if user.role == UserRole.LECTURER:
            await svc.get_or_create_lecturer_dashboard(user.id)
        elif user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            await svc.get_or_create_admin_dashboard(user.id, user.tenant_id)
        elif user.role == UserRole.STUDENT:
            await svc.get_or_create_student_dashboard(user.id)
        else:
            logger.warning("REFRESH_DASHBOARD: unknown role '%s' for user %s", user.role, user_id)

        logger.debug("Dashboard refreshed for user %s (role=%s)", user_id, user.role)

    try:
        await with_db(_run)
    except Exception:
        logger.exception("REFRESH_DASHBOARD failed (user=%s)", user_id)
        raise


async def emit_refresh_dashboard(user_id: str, tenant_id: Optional[str] = None) -> None:
    """Emit a REFRESH_DASHBOARD Kafka event with tenant_id as partition key.

    Awaiting ensures failures are observable and logged rather than silently
    dropped by a fire-and-forget ``asyncio.ensure_future`` call.
    """
    from core.utils.kafka.manager import kafka_manager
    success = await kafka_manager.emit(
        "REFRESH_DASHBOARD",
        {"user_id": user_id},
        partition_key=tenant_id,
    )
    if not success:
        logger.error(
            "emit_refresh_dashboard: failed to publish REFRESH_DASHBOARD for user=%s — "
            "dashboard may be stale; replay manually if needed",
            user_id,
        )


async def emit_grade_attempt(attempt_id: str, exam_id: str, tenant_id: Optional[str] = None) -> None:
    """Emit a GRADE_SUBMISSION_ATTEMPT Kafka event with tenant_id as partition key.

    Using tenant_id as the partition key ensures all grading events for a tenant
    are routed to the same partition and worker replica, making per-tenant
    asyncio.Semaphore effective across the worker fleet.
    """
    from core.utils.kafka.manager import kafka_manager
    success = await kafka_manager.emit(
        "GRADE_SUBMISSION_ATTEMPT",
        {"attempt_id": attempt_id, "exam_id": exam_id},
        partition_key=tenant_id,
    )
    if not success:
        logger.error(
            "emit_grade_attempt: failed to publish GRADE_SUBMISSION_ATTEMPT "
            "(attempt=%s exam=%s) — grading job may be lost; replay manually if needed",
            attempt_id, exam_id,
        )


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

#: Map of Kafka event name → handler coroutine for this module.
#: KafkaConsumerService discovers and merges these at startup.
HANDLERS: dict = {
    "GRADE_SUBMISSION_ATTEMPT": handle_grade_submission_attempt,
    "REFRESH_DASHBOARD": handle_refresh_dashboard,
}
