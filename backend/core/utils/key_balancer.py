"""GroqKeyRotator — Redis-backed cross-process Groq API key rotation.

Reads up to 4 keys from GROQ_API_KEY_1 … GROQ_API_KEY_4 (falling back to
the legacy GROQ_API_KEYS comma-separated list).

Redis keys used:
  groq:key_cooldown:{index}  — set with TTL=retry_after_seconds when a key
                               is rate-limited; presence means "cooling down".

Round-robin selection skips cooling keys.  If all keys are cooling, waits 1s
and returns the first key as a last resort.

A module-level singleton is exposed via ``get_rotator()``.

Backward-compatibility shim: ``get_balancer()`` returns the same singleton so
existing callers that import ``get_balancer`` continue to work.
"""
from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from core.config import get_settings
from core.database import get_redis_client


class GroqKeyRotator:
    """Redis-backed round-robin Groq API key rotator with per-key cooldown.

    All worker replicas share cooldown state via Redis, so no replica sends
    requests to a rate-limited key.
    """

    def __init__(self) -> None:
        self.keys: List[str] = self._load_keys()
        self._index: int = 0  # in-process round-robin cursor

    # ------------------------------------------------------------------
    # Key loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_keys() -> List[str]:
        """Load up to 4 keys from GROQ_API_KEY_1…4, then fall back to
        the legacy GROQ_API_KEYS comma-separated env var."""
        keys: List[str] = []

        # Prefer numbered env vars (GROQ_API_KEY_1 … GROQ_API_KEY_4)
        for i in range(1, 5):
            val = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
            if val:
                keys.append(val)

        if not keys:
            # Fall back to legacy comma-separated list
            settings = get_settings()
            raw = getattr(settings, "GROQ_API_KEYS", None) or ""
            keys = [k.strip() for k in raw.split(",") if k.strip()]

        return keys

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_key(self) -> Optional[str]:
        """Return the next available (non-cooling) key using round-robin.

        If all keys are currently cooling down, waits 1 second and returns
        the first key as a last resort so grading is never permanently blocked.
        """
        if not self.keys:
            return None

        redis = get_redis_client()
        n = len(self.keys)

        # Try each key starting from the current round-robin position
        for _ in range(n):
            idx = self._index % n
            self._index = (self._index + 1) % n

            if redis is not None:
                try:
                    cooling = await redis.exists(f"groq:key_cooldown:{idx}")
                    if cooling:
                        continue  # skip this key — it's rate-limited
                except Exception:
                    pass  # Redis error → treat key as available

            return self.keys[idx]

        # All keys are cooling — wait 1s and return the first key
        await asyncio.sleep(1.0)
        return self.keys[0]

    async def mark_rate_limited(self, key: str, retry_after: int = 60) -> None:
        """Mark a key as rate-limited for ``retry_after`` seconds.

        Sets ``groq:key_cooldown:{index}`` in Redis with the given TTL so all
        worker replicas know to skip this key until the cooldown expires.
        """
        redis = get_redis_client()
        if redis is None or not key:
            return
        try:
            idx = self.keys.index(key)
        except ValueError:
            return
        try:
            await redis.set(f"groq:key_cooldown:{idx}", "1", ex=retry_after)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Legacy KeyBalancer compatibility shim
    # ------------------------------------------------------------------

    async def get_best_key(self) -> Optional[str]:
        """Alias for get_key() — preserves backward compatibility with
        callers that used the old KeyBalancer.get_best_key() API."""
        return await self.get_key()

    async def incr_usage(self, key: str, amount: int = 1) -> None:
        """No-op shim — usage tracking is now handled via cooldown flags."""
        pass


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_rotator: Optional[GroqKeyRotator] = None


def get_rotator() -> GroqKeyRotator:
    """Return the module-level GroqKeyRotator singleton."""
    global _rotator
    if _rotator is None:
        _rotator = GroqKeyRotator()
    return _rotator


# Backward-compatibility alias so existing code that imports get_balancer
# continues to work without modification.
def get_balancer() -> GroqKeyRotator:
    """Backward-compatibility alias for get_rotator()."""
    return get_rotator()
