"""Health check endpoint.

Returns a structured JSON response probing DB, Redis, and Kafka connectivity.
Always returns HTTP 200 so that load-balancers and Docker health checks can
distinguish between "service is up but degraded" and "service is completely down".

Response shape (per spec requirement 2.137):
    {
        "status": "ok",
        "db":     "ok" | "error",
        "redis":  "ok" | "error",
        "kafka":  "ok" | "error"
    }
"""

from fastapi import APIRouter, Request
from sqlalchemy import text

from core.utils.logger import logger
from core.database import get_db
from core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """Probe DB, Redis, and Kafka; always return HTTP 200 with structured status."""
    settings = get_settings()

    result = {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
        "kafka": "ok",
    }

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            break
    except Exception as exc:
        logger.error("Health check — DB unhealthy: %s", exc)
        result["db"] = "error"
        result["status"] = "degraded"

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis

        redis_url = settings.REDIS_URL
        if redis_url:
            kwargs: dict = {"decode_responses": True}
            if settings.REDIS_PASSWORD:
                kwargs["password"] = settings.REDIS_PASSWORD
                if "@" not in redis_url:
                    redis_url = redis_url.replace(
                        "redis://", f"redis://:{settings.REDIS_PASSWORD}@"
                    )
            client = aioredis.from_url(redis_url, **kwargs)
            await client.ping()
            await client.aclose()
        else:
            result["redis"] = "error"
            result["status"] = "degraded"
    except Exception as exc:
        logger.error("Health check — Redis unhealthy: %s", exc)
        result["redis"] = "error"
        result["status"] = "degraded"

    # ── Kafka ─────────────────────────────────────────────────────────────────
    try:
        from aiokafka.admin import AIOKafkaAdminClient

        brokers = settings.kafka_bootstrap_list()
        if brokers:
            admin = AIOKafkaAdminClient(bootstrap_servers=brokers)
            await admin.start()
            await admin.close()
        else:
            result["kafka"] = "error"
            result["status"] = "degraded"
    except Exception as exc:
        logger.error("Health check — Kafka unhealthy: %s", exc)
        result["kafka"] = "error"
        result["status"] = "degraded"

    # Always HTTP 200 — callers inspect the body to determine degraded state
    return result
