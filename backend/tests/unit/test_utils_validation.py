"""Unit tests for core.utils.validation module.

Tests validation helper functions: UUID, date, number, duration, score, phone.
"""
import pytest
from datetime import datetime, timezone, timedelta
from core.utils.validation import (
    validate_uuid,
    validate_future_date,
    validate_positive_number,
    validate_duration,
    validate_score,
    validate_phone_number,
)


class TestValidateUUID:
    """Tests for validate_uuid."""

    def test_valid_uuid_returns_true(self):
        """Test that a valid UUID string returns True."""
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_invalid_uuid_returns_false(self):
        """Test that an invalid UUID string returns False."""
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("") is False
        assert validate_uuid("12345") is False

    def test_none_uuid_returns_false(self):
        """Test that None returns False."""
        assert validate_uuid(None) is False


class TestValidateFutureDate:
    """Tests for validate_future_date."""

    def test_future_date_returns_true(self):
        """Test that a future date returns True."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        assert validate_future_date(future) is True

    def test_past_date_returns_false(self):
        """Test that a past date returns False."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert validate_future_date(past) is False

    def test_none_returns_false(self):
        """Test that None returns False."""
        assert validate_future_date(None) is False

    def test_naive_datetime_treated_as_utc(self):
        """Test that naive datetime is treated as UTC."""
        future_naive = datetime.utcnow() + timedelta(hours=1)
        assert validate_future_date(future_naive) is True


class TestValidatePositiveNumber:
    """Tests for validate_positive_number."""

    def test_positive_int_returns_true(self):
        assert validate_positive_number(1) is True
        assert validate_positive_number(100) is True

    def test_positive_float_returns_true(self):
        assert validate_positive_number(0.1) is True

    def test_zero_returns_false(self):
        assert validate_positive_number(0) is False

    def test_negative_returns_false(self):
        assert validate_positive_number(-1) is False


class TestValidateDuration:
    """Tests for validate_duration."""

    def test_valid_duration_returns_true(self):
        assert validate_duration(1) is True
        assert validate_duration(24) is True
        assert validate_duration(2) is True

    def test_zero_duration_returns_false(self):
        assert validate_duration(0) is False

    def test_over_24_hours_returns_false(self):
        assert validate_duration(25) is False


class TestValidateScore:
    """Tests for validate_score."""

    def test_valid_score_returns_true(self):
        assert validate_score(0) is True
        assert validate_score(50) is True
        assert validate_score(100) is True

    def test_negative_score_returns_false(self):
        assert validate_score(-1) is False

    def test_over_100_returns_false(self):
        assert validate_score(101) is False


class TestValidatePhoneNumber:
    """Tests for validate_phone_number."""

    def test_valid_phone_returns_true(self):
        assert validate_phone_number("08012345678") is True
        assert validate_phone_number("+2348012345678") is True

    def test_empty_phone_returns_true(self):
        """Empty phone is considered valid (optional field)."""
        assert validate_phone_number("") is True

    def test_too_short_phone_returns_false(self):
        assert validate_phone_number("123") is False

    def test_too_long_phone_returns_false(self):
        assert validate_phone_number("1234567890123456") is False
