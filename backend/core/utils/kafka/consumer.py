"""Kafka consumer — manual commit, dead-letter logging, reconnect on error."""
from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any, Callable, Coroutine, Dict, Optional

from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaConnectionError, KafkaError

from core.config import get_settings
from core.utils.logger import logger

# Type alias for async event handlers
Handler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# Maximum consecutive broker errors before backing off
_MAX_ERRORS = 5
_BACKOFF_SECONDS = 10


def _build_consumer(topic: str, group_id: str) -> AIOKafkaConsumer:
    settings = get_settings()
    brokers = settings.KAFKA_BOOTSTRAP_SERVERS or "localhost:9092"

    kwargs: Dict[str, Any] = dict(
        bootstrap_servers=brokers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        session_timeout_ms=30_000,
        heartbeat_interval_ms=10_000,
        max_poll_interval_ms=300_000,
        fetch_max_wait_ms=500,
    )

    protocol = (settings.KAFKA_SECURITY_PROTOCOL or "PLAINTEXT").upper()

    if protocol in ("SASL_PLAINTEXT", "SASL_SSL"):
        kwargs["security_protocol"] = protocol
        kwargs["sasl_mechanism"] = settings.KAFKA_SASL_MECHANISM or "PLAIN"
        kwargs["sasl_plain_username"] = settings.KAFKA_USERNAME or ""
        kwargs["sasl_plain_password"] = settings.KAFKA_PASSWORD or ""

    if protocol in ("SSL", "SASL_SSL"):
        kwargs["ssl_context"] = ssl.create_default_context()

    return AIOKafkaConsumer(topic, **kwargs)


class KafkaConsumerService:
    """Resilient Kafka consumer with manual commit and dead-letter logging."""

    TOPIC = "tenant-tasks"
    GROUP_ID = "wazire-worker"

    def __init__(self) -> None:
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._handlers: Dict[str, Handler] = {}
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._load_handlers()
        self._consumer = _build_consumer(self.TOPIC, self.GROUP_ID)
        await self._consumer.start()
        self._running = True
        self._task = asyncio.get_event_loop().create_task(self._run_loop())
        logger.info(
            "Kafka consumer started (topic=%s group=%s brokers=%s)",
            self.TOPIC, self.GROUP_ID, get_settings().KAFKA_BOOTSTRAP_SERVERS,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception:
                logger.exception("Error stopping Kafka consumer")
        logger.info("Kafka consumer stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        consecutive_errors = 0
        while self._running:
            try:
                await self._consume_once()
                consecutive_errors = 0
            except asyncio.CancelledError:
                break
            except KafkaConnectionError as exc:
                consecutive_errors += 1
                logger.error(
                    "Kafka connection error (%d/%d): %s",
                    consecutive_errors, _MAX_ERRORS, exc,
                )
                if consecutive_errors >= _MAX_ERRORS:
                    logger.warning("Too many Kafka errors — backing off %ds", _BACKOFF_SECONDS)
                    await asyncio.sleep(_BACKOFF_SECONDS)
                    consecutive_errors = 0
            except Exception:
                logger.exception("Unexpected error in Kafka consumer loop")
                await asyncio.sleep(1)

    async def _consume_once(self) -> None:
        assert self._consumer is not None
        async for msg in self._consumer:
            if not self._running:
                break
            await self._handle_message(msg)

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    async def _handle_message(self, msg: Any) -> None:
        tp = TopicPartition(msg.topic, msg.partition)
        try:
            raw = msg.value.decode("utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            logger.error(
                "Failed to decode Kafka message (offset=%d): %s", msg.offset, exc
            )
            await self._commit(msg)
            return

        event = payload.get("event")
        data = payload.get("data") or {}
        handler = self._handlers.get(event)

        if handler is None:
            logger.warning("No handler for event '%s' (offset=%d)", event, msg.offset)
            await self._commit(msg)
            return

        try:
            await handler(data)
        except Exception:
            # Dead-letter: log full context so nothing is silently lost
            logger.exception(
                "Handler failed for event '%s' (offset=%d partition=%d) — data=%s",
                event, msg.offset, msg.partition, data,
            )
            # Still commit so the consumer doesn't get stuck on a poison pill.
            # For critical events, implement a dead-letter topic here.

        await self._commit(msg)

    async def _commit(self, msg: Any) -> None:
        try:
            tp = TopicPartition(msg.topic, msg.partition)
            await self._consumer.commit({tp: msg.offset + 1})
        except Exception:
            logger.exception("Failed to commit offset (offset=%d)", msg.offset)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def _load_handlers(self) -> None:
        """Import task modules and register event handlers."""
        try:
            from tasks.submission import handle_grade_submission_attempt, handle_refresh_dashboard
            from tasks.question import handle_detect_answer, handle_parse_and_create
            from tasks.email import handle_send_email
            from tasks.exam import handle_update_exam_status, handle_send_queued_emails

            self._handlers = {
                "GRADE_SUBMISSION_ATTEMPT": handle_grade_submission_attempt,
                "REFRESH_DASHBOARD": handle_refresh_dashboard,
                "DETECT_ANSWER": handle_detect_answer,
                "PARSE_AND_CREATE": handle_parse_and_create,
                "SEND_EMAIL": handle_send_email,
                "UPDATE_EXAM_STATUS": handle_update_exam_status,
                "SEND_QUEUED_EMAILS": handle_send_queued_emails,
            }
            logger.info("Registered %d Kafka event handlers", len(self._handlers))
        except Exception:
            logger.exception("Failed to load Kafka event handlers")


# Only the class-based `KafkaConsumerService` is exported from this module.
