from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TenantMiddleware(BaseHTTPMiddleware):
    """Simple middleware that reads `X-Tenant-ID` header and attaches it
    to `request.state.tenant_id` for downstream dependencies and handlers.

    The header is optional; absence means no tenant context (e.g. public
    endpoints or system-level operations).
    """

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("x-tenant")
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
