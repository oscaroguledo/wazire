"""Unit tests for GroqKeyRotator (core.utils.key_balancer).

Tests round-robin key selection, Redis-backed cooldown, and fallback behaviour.
All Redis calls are mocked so no real Redis connection is needed.
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGroqKeyRotatorLoadKeys:
    """Tests for GroqKeyRotator._load_keys()."""

    def test_loads_numbered_env_vars(self, monkeypatch):
        """Test that keys are loaded from GROQ_API_KEY_1..4 env vars."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.setenv("GROQ_API_KEY_2", "key-two")
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        from core.utils.key_balancer import GroqKeyRotator
        rotator = GroqKeyRotator()

        assert "key-one" in rotator.keys
        assert "key-two" in rotator.keys

    def test_empty_keys_when_no_env_vars(self, monkeypatch):
        """Test that keys list is empty when no env vars are set."""
        for i in range(1, 5):
            monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)

        with patch("core.utils.key_balancer.get_settings") as mock_settings:
            mock_settings.return_value.GROQ_API_KEYS = ""
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            rotator.keys = GroqKeyRotator._load_keys()

        assert rotator.keys == []


class TestGroqKeyRotatorGetKey:
    """Tests for GroqKeyRotator.get_key()."""

    @pytest.mark.asyncio
    async def test_get_key_returns_key_when_available(self, monkeypatch):
        """Test that get_key returns a key when none are cooling."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.setenv("GROQ_API_KEY_2", "key-two")
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)  # No keys cooling

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            key = await rotator.get_key()

        assert key in ["key-one", "key-two"]

    @pytest.mark.asyncio
    async def test_get_key_skips_cooling_keys(self, monkeypatch):
        """Test that get_key skips keys that are in cooldown."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.setenv("GROQ_API_KEY_2", "key-two")
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        # key-one (index 0) is cooling, key-two (index 1) is available
        async def mock_exists(key):
            return 1 if "0" in key else 0

        mock_redis = AsyncMock()
        mock_redis.exists = mock_exists

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            rotator._index = 0  # Start from key-one
            key = await rotator.get_key()

        assert key == "key-two"

    @pytest.mark.asyncio
    async def test_get_key_all_cooling_returns_first_after_wait(self, monkeypatch):
        """Test that get_key returns first key after 1s wait when all are cooling."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)  # All cooling

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                from core.utils.key_balancer import GroqKeyRotator
                rotator = GroqKeyRotator()
                key = await rotator.get_key()

        assert key == "key-one"
        mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    async def test_get_key_no_keys_returns_none(self, monkeypatch):
        """Test that get_key returns None when no keys are configured."""
        for i in range(1, 5):
            monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)

        with patch("core.utils.key_balancer.get_settings") as mock_settings:
            mock_settings.return_value.GROQ_API_KEYS = ""
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            rotator.keys = []
            key = await rotator.get_key()

        assert key is None

    @pytest.mark.asyncio
    async def test_get_key_redis_error_treats_key_as_available(self, monkeypatch):
        """Test that Redis errors are swallowed and key is treated as available."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=Exception("Redis connection error"))

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            key = await rotator.get_key()

        assert key == "key-one"


class TestGroqKeyRotatorMarkRateLimited:
    """Tests for GroqKeyRotator.mark_rate_limited()."""

    @pytest.mark.asyncio
    async def test_mark_rate_limited_sets_redis_key(self, monkeypatch):
        """Test that mark_rate_limited sets a Redis cooldown key with TTL."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            await rotator.mark_rate_limited("key-one", retry_after=60)

        mock_redis.set.assert_called_once_with("groq:key_cooldown:0", "1", ex=60)

    @pytest.mark.asyncio
    async def test_mark_rate_limited_unknown_key_is_noop(self, monkeypatch):
        """Test that mark_rate_limited is a no-op for unknown keys."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("core.utils.key_balancer.get_redis_client", return_value=mock_redis):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            await rotator.mark_rate_limited("unknown-key", retry_after=60)

        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_rate_limited_no_redis_is_noop(self, monkeypatch):
        """Test that mark_rate_limited is a no-op when Redis is not configured."""
        monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
        monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
        monkeypatch.delenv("GROQ_API_KEY_4", raising=False)

        with patch("core.utils.key_balancer.get_redis_client", return_value=None):
            from core.utils.key_balancer import GroqKeyRotator
            rotator = GroqKeyRotator()
            # Should not raise
            await rotator.mark_rate_limited("key-one", retry_after=60)


class TestGroqKeyRotatorSingleton:
    """Tests for the module-level singleton."""

    def test_get_rotator_returns_same_instance(self):
        """Test that get_rotator returns the same singleton instance."""
        from core.utils.key_balancer import get_rotator
        import core.utils.key_balancer as kb

        # Reset singleton
        kb._rotator = None

        r1 = get_rotator()
        r2 = get_rotator()

        assert r1 is r2

    def test_get_balancer_alias_returns_same_instance(self):
        """Test that get_balancer is an alias for get_rotator."""
        from core.utils.key_balancer import get_rotator, get_balancer
        import core.utils.key_balancer as kb

        kb._rotator = None

        assert get_rotator() is get_balancer()
