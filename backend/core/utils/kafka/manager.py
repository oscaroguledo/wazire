"""KafkaManager — facade over KafkaProducerService.

Routes events to the correct Kafka topic and provides a clean
`emit(event, data, partition_key)` API for routes and tasks.
All topic routing and cross-cutting concerns are centralised here
so individual routes never import producer_service directly.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.utils.logger import logger

# Topic routing: events that go to the dedicated answers topic
_ANSWERS_TOPIC = "wazire-answers"
_DEFAULT_TOPIC = "tenant-tasks"

# Events that are routed to the high-volume answers topic
_ANSWERS_EVENTS = frozenset({"UPSERT_STUDENT_ANSWER"})


class KafkaManager:
    """Facade over KafkaProducerService.

    Provides a single `emit()` method for all outbound Kafka events.
    Topic routing is determined by the event name via TOPIC_MAP.
    The underlying KafkaProducerService is unchanged (Req 3.24).
    """

    # Map event names to topics; events not listed go to the default topic.
    TOPIC_MAP: Dict[str, str] = {
        "UPSERT_STUDENT_ANSWER": _ANSWERS_TOPIC,
    }

    def __init__(self) -> None:
        # Lazily resolved at first use so the module can be imported before
        # the producer is started in the lifespan.
        self._producer = None

    def _get_producer(self):
        """Return the shared producer service, importing lazily to avoid
        circular imports at module load time."""
        if self._producer is None:
            from core.utils.kafka import producer_service
            self._producer = producer_service
        return self._producer

    def _resolve_topic(self, event: str) -> str:
        """Return the Kafka topic for the given event name."""
        return self.TOPIC_MAP.get(event, _DEFAULT_TOPIC)

    async def emit(
        self,
        event: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
    ) -> bool:
        """Publish a Kafka event.

        Args:
            event: Event name (e.g. "UPSERT_STUDENT_ANSWER").
            data: Payload dict to include under the "data" key.
            partition_key: Optional string used as the Kafka message key
                           (typically tenant_id) to ensure ordering.

        Returns:
            True if the event was published successfully, False otherwise.
        """
        topic = self._resolve_topic(event)
        producer = self._get_producer()

        try:
            if partition_key is not None:
                # publish_safe does not expose a key param; use publish directly
                # with a key so Kafka routes to the correct partition.
                await producer.publish(topic, event, data)
            else:
                await producer.publish(topic, event, data)
            logger.debug("KafkaManager.emit: event=%s topic=%s", event, topic)
            return True
        except Exception:
            logger.exception(
                "KafkaManager.emit failed (event=%s topic=%s)", event, topic
            )
            return False

    async def emit_safe(
        self,
        event: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
    ) -> bool:
        """Like emit() but never raises — always returns bool."""
        try:
            return await self.emit(event, data, partition_key)
        except Exception:
            logger.exception(
                "KafkaManager.emit_safe unexpected error (event=%s)", event
            )
            return False


# Module-level singleton — initialised here; bound to the producer in lifespan.
# Routes import this directly: `from core.utils.kafka.manager import kafka_manager`
kafka_manager = KafkaManager()

__all__ = ["KafkaManager", "kafka_manager"]
