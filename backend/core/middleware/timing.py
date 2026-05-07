import asyncio
import time
from datetime import datetime

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.utils.logger import logger


# Paths exempt from the hard 1 s timeout (large uploads, webhook ingestion).
_TIMEOUT_EXEMPT_PREFIXES = (
    "/api/v1/academic/exams/",                      # /scan — multipart upload
    "/api/v1/academic/questions/upload-exam-paper",
    "/api/v1/billing/webhooks/",
)


def _fmt_duration(ms: float) -> str:
    """Format a duration the same way chi does: µs / ms / s with one decimal."""
    if ms < 1:
        return f"{ms * 1000:.1f}µs"
    if ms < 1000:
        return f"{ms:.1f}ms"
    return f"{ms / 1000:.2f}s"


class TimingMiddleware(BaseHTTPMiddleware):
    """Chi-style request logger + hard per-request timeout.

    Every completed request is logged as a single line:

        2026/05/07 11:42:01 | 200 |     142.3ms | POST   /api/v1/auth/login
        2026/05/07 11:42:02 | 404 |       0.8ms | GET    /api/v1/academic/courses/bad-id
        2026/05/07 11:42:03 | 504 |    1000.0ms | GET    /api/v1/academic/submissions/  TIMEOUT

    Requests that exceed ``timeout_seconds`` (default 1 s, set via
    ``API_TIMEOUT_SECONDS`` env var) are cancelled and return HTTP 504.
    Exempt paths (large uploads, webhooks) skip the hard timeout.
    """

    def __init__(self, app, timeout_seconds: float = 1.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        timed_out = False

        exempt = any(path.startswith(p) for p in _TIMEOUT_EXEMPT_PREFIXES)

        if exempt:
            response = await call_next(request)
        else:
            try:
                response = await asyncio.wait_for(
                    call_next(request),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                timed_out = True
                response = JSONResponse(
                    status_code=504,
                    content={
                        "success": False,
                        "error": "Request timed out. Please try again.",
                        "timeout_ms": int(self.timeout_seconds * 1000),
                    },
                )

        elapsed_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code
        ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        duration_str = _fmt_duration(elapsed_ms)
        suffix = "  TIMEOUT" if timed_out else ""

        # chi-style: timestamp | status | duration (right-aligned 12 chars) | METHOD  path
        logger.info(
            "%s | %d | %12s | %-7s %s%s",
            ts,
            status_code,
            duration_str,
            method,
            path,
            suffix,
        )

        return response
