import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from core.utils.logger import logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Log timing information for all API requests.
    
    Logs the method, path, and total time taken for each request.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Log timing information
        logger.info(f"[TIMING] {request.method} {request.url.path} - {duration_ms:.2f}ms {'Slow' if duration_ms >= 900 else 'Fast'}")
        
        return response
