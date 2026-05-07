"""Unit tests for core/utils/logger.py."""
import pytest
from io import StringIO
from unittest.mock import patch

from core.utils.logger import Logger, get_logger, logger


class TestLogger:
    def test_default_level_is_debug(self):
        log = Logger()
        assert log.level == "DEBUG"

    def test_custom_level(self):
        log = Logger(level="WARNING")
        assert log.level == "WARNING"
        assert log.levelno == 30

    def test_should_log_at_or_above_level(self):
        log = Logger(level="WARNING")
        assert log._should_log("WARNING") is True
        assert log._should_log("ERROR") is True
        assert log._should_log("DEBUG") is False

    def test_format_includes_level_and_name(self):
        log = Logger(name="test-app", level="INFO")
        formatted = log._format("INFO", "hello world")
        assert "INFO" in formatted
        assert "test-app" in formatted
        assert "hello world" in formatted

    def test_render_with_args(self):
        log = Logger()
        result = log._render("Hello {}", "world")
        assert result == "Hello world"

    def test_render_with_kwargs(self):
        log = Logger()
        result = log._render("Hello {name}", name="Alice")
        assert result == "Hello Alice"

    def test_render_bad_format_returns_original(self):
        log = Logger()
        result = log._render("Hello {bad_key}", "extra_arg")
        assert "Hello" in result

    def test_debug_prints_when_level_allows(self):
        log = Logger(level="DEBUG")
        with patch("builtins.print") as mock_print:
            log.debug("test message")
            mock_print.assert_called_once()

    def test_info_suppressed_when_level_is_warning(self):
        log = Logger(level="WARNING")
        with patch("builtins.print") as mock_print:
            log.info("suppressed")
            mock_print.assert_not_called()

    def test_warning_prints(self):
        log = Logger(level="WARNING")
        with patch("builtins.print") as mock_print:
            log.warning("warn msg")
            mock_print.assert_called_once()

    def test_error_prints(self):
        log = Logger(level="ERROR")
        with patch("builtins.print") as mock_print:
            log.error("error msg")
            mock_print.assert_called_once()

    def test_critical_prints(self):
        log = Logger(level="CRITICAL")
        with patch("builtins.print") as mock_print:
            log.critical("critical msg")
            mock_print.assert_called_once()

    def test_exception_includes_exc_info(self):
        log = Logger(level="DEBUG")
        exc = ValueError("test error")
        with patch("builtins.print") as mock_print:
            log.exception("something failed", exc_info=exc)
            call_args = mock_print.call_args[0][0]
            assert "test error" in call_args

    def test_exception_without_exc_info(self):
        log = Logger(level="DEBUG")
        with patch("builtins.print") as mock_print:
            log.exception("something failed")
            mock_print.assert_called_once()


class TestGetLogger:
    def test_returns_logger_instance(self):
        log = get_logger("my-app", "INFO")
        assert isinstance(log, Logger)
        assert log.name == "my-app"
        assert log.level == "INFO"

    def test_module_logger_exists(self):
        assert isinstance(logger, Logger)
