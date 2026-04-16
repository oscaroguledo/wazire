from functools import wraps
from typing import Callable
from fastapi import HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.utils.logger import logger


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}: {exc.detail}")
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "success": False,
            "error": "Rate limit exceeded. Please try again later.",
            "limit": exc.detail
        }
    )


# Apply the custom handler
limiter.request_filter = lambda request: True


def rate_limit(limit: str, key_func: Callable = None):
    """
    Rate limiting decorator for endpoints.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
        key_func: Optional custom key function for rate limiting
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                return await func(*args, **kwargs)

            try:
                # Apply rate limit
                limiter.hit(request, limit)
            except RateLimitExceeded as e:
                raise rate_limit_exceeded_handler(request, e)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Predefined rate limits for different endpoint types
STRICT_RATE = "10/minute"  # For sensitive operations
MODERATE_RATE = "30/minute"  # For standard operations
LENIENT_RATE = "100/minute"  # For read operations
