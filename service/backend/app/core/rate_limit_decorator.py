"""
Rate limiting decorator for FastAPI endpoints.
"""

import os
from functools import wraps
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_rate_limit import check_rate_limit
from app.core.database import get_db


def rate_limit(max_attempts: int = 5, window_seconds: int = 900):
    """
    Decorator to apply rate limiting to FastAPI endpoints.

    Args:
        max_attempts: Maximum number of attempts allowed
        window_seconds: Time window in seconds

    Usage:
        @rate_limit(max_attempts=5, window_seconds=900)
        async def endpoint_function(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip rate limiting during tests
            if os.getenv("TESTING_MODE"):
                return await func(*args, **kwargs)

            # Find the request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Try to get request from kwargs
                request = kwargs.get('request')

            if not request:
                # Can't apply rate limit without request object
                return await func(*args, **kwargs)

            # Get client IP address
            ip_address = request.client.host if request.client else "unknown"

            # Check rate limit
            allowed, remaining, retry_after = await check_rate_limit(
                identifier=ip_address,
                max_attempts=max_attempts,
                window_seconds=window_seconds,
                prefix=f"ratelimit:{func.__name__}"
            )

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many attempts",
                        "retry_after": retry_after,
                        "message": f"Too many attempts. Please try again in {retry_after} seconds."
                    }
                )

            # Add rate limit info to response headers
            response = await func(*args, **kwargs)

            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(max_attempts)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(retry_after)

            return response

        return wrapper
    return decorator
