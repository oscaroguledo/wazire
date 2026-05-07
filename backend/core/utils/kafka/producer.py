"""Kafka producer — class-based shared service with SASL support and retries."""
from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from core.config import get_settings
from core.utils.logger import logger


class KafkaProducerService:
    """Shared, resilient Kafka producer service."""

    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._lock = asyncio.Lock()

    def _topic(self, name: str) -> str:
        prefix = get_settings().KAFKA_TOPIC_PREFIX
        return f"{prefix}-{name}" if prefix else name

    def _build_producer(self) -> AIOKafkaProducer:
        settings = get_settings()
        brokers = settings.KAFKA_BOOTSTRAP_SERVERS or "localhost:9092"

        kwargs: Dict[str, Any] = dict(
            bootstrap_servers=brokers,
            acks="all",
            enable_idempotence=True,
            max_batch_size=16384,
            linger_ms=5,
            request_timeout_ms=30_000,
            retry_backoff_ms=500,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        protocol = (settings.KAFKA_SECURITY_PROTOCOL or "PLAINTEXT").upper()

        if protocol in ("SASL_PLAINTEXT", "SASL_SSL"):
            kwargs["security_protocol"] = protocol
            kwargs["sasl_mechanism"] = settings.KAFKA_SASL_MECHANISM or "PLAIN"
            kwargs["sasl_plain_username"] = settings.KAFKA_USERNAME or ""
            kwargs["sasl_plain_password"] = settings.KAFKA_PASSWORD or ""

        if protocol in ("SSL", "SASL_SSL"):
            kwargs["ssl_context"] = ssl.create_default_context()

        return AIOKafkaProducer(**kwargs)

    async def start(self) -> None:
        async with self._lock:
            if self._producer is not None:
                return
            settings = get_settings()
            brokers = settings.KAFKA_BOOTSTRAP_SERVERS or "localhost:9092"

            kwargs: Dict[str, Any] = dict(
                bootstrap_servers=brokers,
                acks="all",
                enable_idempotence=True,
                max_batch_size=16384,
                linger_ms=5,
                request_timeout_ms=30_000,
                retry_backoff_ms=500,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            protocol = (settings.KAFKA_SECURITY_PROTOCOL or "PLAINTEXT").upper()

            if protocol in ("SASL_PLAINTEXT", "SASL_SSL"):
                kwargs["security_protocol"] = protocol
                kwargs["sasl_mechanism"] = settings.KAFKA_SASL_MECHANISM or "PLAIN"
                kwargs["sasl_plain_username"] = settings.KAFKA_USERNAME or ""
                kwargs["sasl_plain_password"] = settings.KAFKA_PASSWORD or ""

            if protocol in ("SSL", "SASL_SSL"):
                kwargs["ssl_context"] = ssl.create_default_context()

            self._producer = AIOKafkaProducer(**kwargs)
            await self._producer.start()
            logger.info("Kafka producer started (brokers=%s)", settings.KAFKA_BOOTSTRAP_SERVERS)

    async def stop(self) -> None:
        async with self._lock:
            if self._producer is None:
                return
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
            except Exception:
                logger.exception("Error stopping Kafka producer")
            finally:
                self._producer = None

    async def publish(self, topic: str, event: str, data: Dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not running")
        payload = {"event": event, "data": data}
        prefix = get_settings().KAFKA_TOPIC_PREFIX
        full_topic = f"{prefix}-{topic}" if prefix else topic
        await self._producer.send_and_wait(full_topic, value=payload)

    async def publish_safe(self, topic: str, event: str, data: Dict[str, Any]) -> bool:
        try:
            await self.publish(topic, event, data)
            return True
        except (KafkaConnectionError, KafkaTimeoutError) as exc:
            logger.error("Kafka publish failed (topic=%s event=%s): %s", topic, event, exc)
        except Exception:
            logger.exception("Unexpected error publishing Kafka event (topic=%s event=%s)", topic, event)
        return False


# Module-level singleton adapter for backwards compatibility
# Only the class-based `KafkaProducerService` is exported from this module.
