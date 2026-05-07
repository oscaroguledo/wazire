"""Kafka consumer — manual commit, dead-letter logging, reconnect on error."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import ssl
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaConnectionError, KafkaError

from core.config import get_settings
from core.utils.logger import logger

# Type alias for async event handlers
Handler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# Maximum consecutive broker errors before backing off
_MAX_ERRORS = 5
_BACKOFF_SECONDS = 10

# Dead-letter topic name
_DEAD_LETTER_TOPIC = "wazire-dead-letter"

# Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]

# Task modules that export a HANDLERS dict — add new modules here to register
# their events without touching consumer.py.
_TASK_MODULES: List[str] = [
    "tasks.submission",
    "tasks.exam",
    "tasks.question",
    "tasks.email",
]


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
    # Configurable via KAFKA_CONSUMER_GROUP_ID env var; default "wazire-worker"
    GROUP_ID: str = os.environ.get("KAFKA_CONSUMER_GROUP_ID", "wazire-worker")

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

        # Retry loop: up to _MAX_RETRIES attempts with exponential backoff.
        # Offset is committed only after a successful handler run or after the
        # message is forwarded to the dead-letter topic.
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                await handler(data)
                # Success — commit offset and return
                await self._commit(msg)
                return
            except Exception as exc:
                last_exc = exc
                backoff = _RETRY_BACKOFF_SECONDS[attempt] if attempt < len(_RETRY_BACKOFF_SECONDS) else _RETRY_BACKOFF_SECONDS[-1]
                logger.warning(
                    "Handler failed for event '%s' (offset=%d partition=%d attempt=%d/%d) — "
                    "retrying in %ds: %s",
                    event, msg.offset, msg.partition, attempt + 1, _MAX_RETRIES, backoff, exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)

        # All retries exhausted — forward to dead-letter topic and commit offset
        # so the consumer is not stuck on a poison pill.
        logger.error(
            "Handler exhausted %d retries for event '%s' (offset=%d partition=%d) — "
            "forwarding to dead-letter topic '%s'. data=%s",
            _MAX_RETRIES, event, msg.offset, msg.partition, _DEAD_LETTER_TOPIC, data,
        )
        await self._forward_to_dead_letter(msg, event, data, last_exc)
        await self._commit(msg)

    async def _forward_to_dead_letter(
        self,
        msg: Any,
        event: str,
        data: Dict[str, Any],
        exc: Optional[Exception],
    ) -> None:
        """Forward a failed message to the dead-letter topic with full metadata."""
        from core.utils.kafka import producer_service

        dead_letter_payload = {
            "original_topic": msg.topic,
            "original_partition": msg.partition,
            "original_offset": msg.offset,
            "event": event,
            "data": data,
            "error_message": str(exc) if exc else "unknown",
            "timestamp": time.time(),
        }
        try:
            await producer_service.publish_safe(
                _DEAD_LETTER_TOPIC, "DEAD_LETTER", dead_letter_payload
            )
            logger.info(
                "Forwarded event '%s' (offset=%d) to dead-letter topic '%s'",
                event, msg.offset, _DEAD_LETTER_TOPIC,
            )
        except Exception:
            # Dead-letter publish itself failed — log everything so ops can replay manually
            logger.exception(
                "CRITICAL: failed to forward event '%s' (offset=%d) to dead-letter topic. "
                "Original payload: %s",
                event, msg.offset, dead_letter_payload,
            )

    async def _commit(self, msg: Any) -> None:
        try:
            tp = TopicPartition(msg.topic, msg.partition)
            await self._consumer.commit({tp: msg.offset + 1})
        except Exception:
            logger.exception("Failed to commit offset (offset=%d)", msg.offset)

    # ------------------------------------------------------------------
    # Handler registration — dispatcher pattern
    # ------------------------------------------------------------------

    def _load_handlers(self) -> None:
        """Discover and merge HANDLERS dicts from all task modules.

        Each module in _TASK_MODULES may export a module-level ``HANDLERS``
        dict mapping event name → async handler coroutine.  This method
        imports every listed module and merges their dicts so that
        consumer.py never needs to be edited when a new event type is added.
        """
        merged: Dict[str, Handler] = {}
        for module_path in _TASK_MODULES:
            try:
                mod = importlib.import_module(module_path)
                handlers: Dict[str, Handler] = getattr(mod, "HANDLERS", {})
                if not isinstance(handlers, dict):
                    logger.warning(
                        "Task module %s has a non-dict HANDLERS attribute — skipping",
                        module_path,
                    )
                    continue
                overlap = set(merged) & set(handlers)
                if overlap:
                    logger.warning(
                        "Handler conflict in %s: events %s already registered — overwriting",
                        module_path, overlap,
                    )
                merged.update(handlers)
                logger.debug(
                    "Loaded %d handler(s) from %s: %s",
                    len(handlers), module_path, list(handlers),
                )
            except Exception:
                logger.exception("Failed to load handlers from task module %s", module_path)

        self._handlers = merged
        logger.info(
            "Registered %d Kafka event handler(s): %s",
            len(self._handlers), sorted(self._handlers),
        )


# Only the class-based `KafkaConsumerService` is exported from this module.
