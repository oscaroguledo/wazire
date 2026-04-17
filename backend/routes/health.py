from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.utils.logger import logger
from core.utils.response import Response
from core.database import get_db
from core.config import get_settings
from core.utils.celery_monitor import CeleryMonitor

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
            redis_client = redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
            health_data["dependencies"]["redis"] = "healthy"
        else:
            health_data["dependencies"]["redis"] = "not_configured"
    except Exception as e:
        logger.error(f"Health check - redis unhealthy: {e}")
        health_data["dependencies"]["redis"] = "unhealthy"
        health_data["status"] = "degraded"
    
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


@router.get("/celery/status")
async def celery_status(request: Request):
    """Get Celery worker and task monitoring status."""
    try:
        from celery_app import celery_app
        monitor = CeleryMonitor(celery_app)
        
        active_tasks = monitor.get_active_tasks()
        scheduled_tasks = monitor.get_scheduled_tasks()
        worker_stats = monitor.get_worker_stats()
        
        return Response(
            success=True,
            message="Celery status retrieved",
            data={
                "active_tasks": active_tasks,
                "scheduled_tasks": scheduled_tasks,
                "worker_stats": worker_stats,
            },
            request=request
        )
    except Exception as e:
        logger.error(f"Failed to get Celery status: {e}")
        return Response(
            success=False,
            error=f"Failed to retrieve Celery status: {str(e)}",
            request=request,
            status_code=500
        )


@router.get("/celery/task/{task_id}")
async def get_task_status(task_id: str, request: Request):
    """Get status of a specific Celery task."""
    try:
        from celery_app import celery_app
        monitor = CeleryMonitor(celery_app)
        
        task_status = monitor.get_task_status(task_id)
        
        return Response(
            success=True,
            message="Task status retrieved",
            data=task_status,
            request=request
        )
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return Response(
            success=False,
            error=f"Failed to retrieve task status: {str(e)}",
            request=request,
            status_code=500
        )
