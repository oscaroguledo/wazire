"""Unit tests for KafkaConsumerService dispatcher pattern.

Tests handler registration, dispatch by event type, dead-letter forwarding,
and retry logic — all with mocked Kafka infrastructure.

Test files MUST NOT import from main.py or worker.py.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestKafkaConsumerLoadHandlers:
    """Tests for KafkaConsumerService._load_handlers() dispatcher pattern."""

    def test_load_handlers_registers_all_expected_events(self):
        """Test that _load_handlers merges all HANDLERS dicts from task modules."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        svc._load_handlers()

        expected_events = {
            "GRADE_SUBMISSION_ATTEMPT",
            "REFRESH_DASHBOARD",
            "UPDATE_EXAM_STATUS",
            "SEND_QUEUED_EMAILS",
            "FORCE_SUBMIT_EXAM",
            "DETECT_ANSWER",
            "PARSE_AND_CREATE",
            "PRELOAD_QUESTIONS",
            "UPSERT_STUDENT_ANSWER",
            "SEND_EMAIL",
            "INITIATE_BILLING",
        }

        for event in expected_events:
            assert event in svc._handlers, (
                f"Event '{event}' not registered after _load_handlers()"
            )

    def test_load_handlers_all_handlers_are_callable(self):
        """Test that all registered handlers are callable coroutines."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        svc._load_handlers()

        for event, handler in svc._handlers.items():
            assert callable(handler), f"Handler for '{event}' is not callable"
            assert asyncio.iscoroutinefunction(handler), (
                f"Handler for '{event}' is not a coroutine function"
            )

    def test_load_handlers_handles_missing_module_gracefully(self):
        """Test that _load_handlers skips modules that fail to import."""
        from core.utils.kafka.consumer import KafkaConsumerService, _TASK_MODULES

        svc = KafkaConsumerService()

        # Patch _TASK_MODULES to include a non-existent module
        with patch("core.utils.kafka.consumer._TASK_MODULES", [
            "tasks.submission",
            "tasks.nonexistent_module_xyz",  # This will fail to import
        ]):
            # Should not raise — just log and skip the bad module
            svc._load_handlers()

        # submission handlers should still be registered
        assert "GRADE_SUBMISSION_ATTEMPT" in svc._handlers

    def test_load_handlers_skips_non_dict_handlers_attribute(self):
        """Test that _load_handlers skips modules with non-dict HANDLERS."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()

        mock_module = MagicMock()
        mock_module.HANDLERS = "not_a_dict"  # Invalid type

        with patch("importlib.import_module", return_value=mock_module):
            with patch("core.utils.kafka.consumer._TASK_MODULES", ["tasks.fake"]):
                svc._load_handlers()

        # No handlers should be registered from the bad module
        assert len(svc._handlers) == 0


class TestKafkaConsumerHandleMessage:
    """Tests for KafkaConsumerService._handle_message() dispatch and retry logic."""

    def _make_msg(self, event: str, data: dict, offset: int = 0) -> MagicMock:
        """Create a mock Kafka message."""
        msg = MagicMock()
        msg.topic = "tenant-tasks"
        msg.partition = 0
        msg.offset = offset
        msg.value = json.dumps({"event": event, "data": data}).encode("utf-8")
        return msg

    @pytest.mark.asyncio
    async def test_dispatches_to_correct_handler(self):
        """Test that _handle_message calls the correct handler for the event."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        mock_handler = AsyncMock()
        svc._handlers = {"TEST_EVENT": mock_handler}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        msg = self._make_msg("TEST_EVENT", {"key": "value"})
        await svc._handle_message(msg)

        mock_handler.assert_called_once_with({"key": "value"})

    @pytest.mark.asyncio
    async def test_commits_offset_after_successful_handler(self):
        """Test that offset is committed after successful handler execution."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        mock_handler = AsyncMock()
        svc._handlers = {"TEST_EVENT": mock_handler}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        msg = self._make_msg("TEST_EVENT", {}, offset=42)
        await svc._handle_message(msg)

        svc._consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_event_commits_and_returns(self):
        """Test that unknown events are skipped and offset is committed."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        svc._handlers = {}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        msg = self._make_msg("UNKNOWN_EVENT", {})
        await svc._handle_message(msg)

        # Offset should still be committed to avoid getting stuck
        svc._consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_handler_failure(self):
        """Test that handler is retried up to _MAX_RETRIES times on failure."""
        from core.utils.kafka.consumer import KafkaConsumerService, _MAX_RETRIES

        svc = KafkaConsumerService()
        mock_handler = AsyncMock(side_effect=RuntimeError("transient error"))
        svc._handlers = {"TEST_EVENT": mock_handler}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(svc, "_forward_to_dead_letter", new_callable=AsyncMock):
                msg = self._make_msg("TEST_EVENT", {})
                await svc._handle_message(msg)

        assert mock_handler.call_count == _MAX_RETRIES

    @pytest.mark.asyncio
    async def test_forwards_to_dead_letter_after_exhausted_retries(self):
        """Test that message is forwarded to dead-letter after all retries fail."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        mock_handler = AsyncMock(side_effect=RuntimeError("persistent error"))
        svc._handlers = {"TEST_EVENT": mock_handler}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(svc, "_forward_to_dead_letter", new_callable=AsyncMock) as mock_dl:
                msg = self._make_msg("TEST_EVENT", {})
                await svc._handle_message(msg)

        mock_dl.assert_called_once()

    @pytest.mark.asyncio
    async def test_commits_offset_after_dead_letter_forward(self):
        """Test that offset is committed even after dead-letter forwarding."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        mock_handler = AsyncMock(side_effect=RuntimeError("persistent error"))
        svc._handlers = {"TEST_EVENT": mock_handler}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(svc, "_forward_to_dead_letter", new_callable=AsyncMock):
                msg = self._make_msg("TEST_EVENT", {})
                await svc._handle_message(msg)

        # Offset must be committed so consumer is not stuck
        svc._consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_json_commits_and_returns(self):
        """Test that malformed JSON messages are skipped and offset committed."""
        from core.utils.kafka.consumer import KafkaConsumerService

        svc = KafkaConsumerService()
        svc._handlers = {}
        svc._consumer = AsyncMock()
        svc._consumer.commit = AsyncMock()

        msg = MagicMock()
        msg.topic = "tenant-tasks"
        msg.partition = 0
        msg.offset = 0
        msg.value = b"not valid json {"

        await svc._handle_message(msg)

        svc._consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_manual_offset_commit(self):
        """Test that enable_auto_commit is False (manual commit pattern)."""
        from core.utils.kafka.consumer import _build_consumer
        from unittest.mock import patch as p

        with p("core.utils.kafka.consumer.AIOKafkaConsumer") as mock_consumer_cls:
            mock_consumer_cls.return_value = MagicMock()
            with p("core.utils.kafka.consumer.get_settings") as mock_settings:
                mock_settings.return_value.KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
                mock_settings.return_value.KAFKA_SECURITY_PROTOCOL = "PLAINTEXT"
                _build_consumer("test-topic", "test-group")

            _, kwargs = mock_consumer_cls.call_args
            assert kwargs.get("enable_auto_commit") is False


class TestKafkaConsumerGroupId:
    """Tests for configurable KAFKA_CONSUMER_GROUP_ID."""

    def test_default_group_id(self):
        """Test that default GROUP_ID is 'wazire-worker'."""
        import os
        # Remove env var if set
        original = os.environ.pop("KAFKA_CONSUMER_GROUP_ID", None)
        try:
            # Re-import to pick up default
            import importlib
            import core.utils.kafka.consumer as consumer_mod
            importlib.reload(consumer_mod)
            assert consumer_mod.KafkaConsumerService.GROUP_ID == "wazire-worker"
        finally:
            if original is not None:
                os.environ["KAFKA_CONSUMER_GROUP_ID"] = original

    def test_custom_group_id_from_env(self, monkeypatch):
        """Test that GROUP_ID is read from KAFKA_CONSUMER_GROUP_ID env var."""
        monkeypatch.setenv("KAFKA_CONSUMER_GROUP_ID", "custom-group")

        import importlib
        import core.utils.kafka.consumer as consumer_mod
        importlib.reload(consumer_mod)

        assert consumer_mod.KafkaConsumerService.GROUP_ID == "custom-group"
