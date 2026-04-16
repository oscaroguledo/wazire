from fastapi import APIRouter, Request

from core.utils.logger import logger
from core.utils.response import Response

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """Health check endpoint with standardized response format."""
    logger.debug("Health check requested")
    return Response(
        success=True,
        message="Service is healthy",
        data={"status": "ok", "service": "wazire-api"},
        request=request
    )
