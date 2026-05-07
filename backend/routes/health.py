from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.utils.logger import logger
from core.utils.response import Response
from core.database import get_db
from core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """Health check endpoint with dependency verification."""
    logger.debug("Health check requested")
    
    health_data = {
        "status": "ok",
        "service": "wazire-api",
        "dependencies": {}
    }
    
    # Check database connectivity
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            health_data["dependencies"]["database"] = "healthy"
            await db.close()
            break
    except Exception as e:
        logger.error(f"Health check - database unhealthy: {e}")
        health_data["dependencies"]["database"] = "unhealthy"
        health_data["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        import redis.asyncio as redis
        settings = get_settings()
        redis_url = settings.REDIS_URL
        if redis_url:
            # If REDIS_PASSWORD is set, include it in the URL and pass as password
            if settings.REDIS_PASSWORD:
                # Insert password into URL if not already present
                if "@" not in redis_url:
                    redis_url = redis_url.replace("redis://", f"redis://:{settings.REDIS_PASSWORD}@")
                redis_client = redis.from_url(redis_url, decode_responses=True, password=settings.REDIS_PASSWORD)
            else:
                # Connect without password
                redis_client = redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
            health_data["dependencies"]["redis"] = "healthy"
        else:
            health_data["dependencies"]["redis"] = "not_configured"
    except Exception as e:
        logger.error(f"Health check - redis unhealthy: {e}")
        # Don't mark as degraded for Redis failures in development
        health_data["dependencies"]["redis"] = f"unhealthy: {str(e)}"
    
    # Determine overall status
    if health_data["status"] == "degraded":
        return Response(
            success=False,
            message="Service is degraded",
            data=health_data,
            request=request,
            status_code=503
        )
    
    return Response(
        success=True,
        message="Service is healthy",
        data=health_data,
        request=request
    )


