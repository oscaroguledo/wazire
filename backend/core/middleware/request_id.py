from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has an `X-Request-ID` header for tracing.

    - If the client provided `X-Request-ID`, it's preserved.
    - Otherwise a short random hex token is generated and attached to
      `request.state.request_id` for downstream handlers.
    - The header is always included on the response.
    """

    async def dispatch(self, request: Request, call_next):
        header_name = "X-Request-ID"
        rid = request.headers.get(header_name) or None
        if not rid:
            import secrets

            rid = secrets.token_hex(8)
        request.state.request_id = rid
        response = await call_next(request)
        # ensure header is present on responses
        response.headers[header_name] = rid
        return response
