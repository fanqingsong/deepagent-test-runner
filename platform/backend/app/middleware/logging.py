"""
Structured logging middleware with correlation ID support.
"""

import logging
import structlog
import uuid
from typing import AsyncGenerator

from fastapi import Request
from app.core.config import settings


# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create logger
logger = structlog.get_logger(__name__)


class LoggingMiddleware:
    """Middleware to add request ID and structured logging."""

    async def __call__(self, request: Request, call_next) -> AsyncGenerator:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Bind correlation ID to logger context
        log = logger.bind(correlation_id=correlation_id)

        # Log request
        log.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)
            log.info(
                "request_completed",
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
            )
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except Exception as e:
            log.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                method=request.method,
                path=request.url.path,
            )
            raise
