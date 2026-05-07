from __future__ import annotations

from typing import List, Optional
import os
import asyncio
from core.database import get_redis_client
from core.config import get_settings


class KeyBalancer:
    """Simple Redis-backed API-key balancer for rate/usage steering.

    Environment variable `GROQ_API_KEYS` may contain a comma-separated list
    of API keys. Redis keys used:
      - `groq:key_usage:{key_index}` -> integer usage counter (incremented by workers)

    This implementation picks the key with the smallest usage counter.
    If Redis is not configured, falls back to `GROQ_API_KEY` from settings.
    """

    def __init__(self):
        settings = get_settings()
        raw = settings.GROQ_API_KEYS
        if raw:
            self.keys: List[str] = [k.strip() for k in raw.split(",") if k.strip()]
        else:
            self.keys = [settings.GROQ_API_KEY] if getattr(settings, "GROQ_API_KEY", None) else []

    async def get_best_key(self) -> Optional[str]:
        if not self.keys:
            return None

        redis = get_redis_client()
        # If no redis, return first key
        if not redis:
            return self.keys[0]

        try:
            # Read all usage counters in a single MGET
            keys = [f"groq:key_usage:{i}" for i in range(len(self.keys))]
            vals = await redis.mget(*keys)
            # Convert bytes/None to ints (None->0)
            usages = []
            for v in vals:
                if v is None:
                    usages.append(0)
                else:
                    try:
                        usages.append(int(v))
                    except Exception:
                        usages.append(0)

            # Pick index with smallest usage
            best_idx = int(min(range(len(usages)), key=lambda i: usages[i]))
            return self.keys[best_idx]
        except Exception:
            # On any redis error, return first key
            return self.keys[0]

    async def incr_usage(self, key: str, amount: int = 1) -> None:
        """Increment usage counter for the provided key string (if found)."""
        redis = get_redis_client()
        if not redis or not key:
            return
        try:
            # find index
            try:
                idx = self.keys.index(key)
            except ValueError:
                return
            await redis.incrby(f"groq:key_usage:{idx}", amount)
            # Optionally set TTL so counters autoreset each minute
            await redis.expire(f"groq:key_usage:{idx}", 65)
        except Exception:
            return


_balancer: Optional[KeyBalancer] = None


def get_balancer() -> KeyBalancer:
    global _balancer
    if _balancer is None:
        _balancer = KeyBalancer()
    return _balancer
