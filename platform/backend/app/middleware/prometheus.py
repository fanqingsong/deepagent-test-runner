"""
Prometheus metrics middleware for FastAPI applications.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Response, Request
from app.core.config import settings
import time
from functools import wraps


# Custom metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

active_connections = Gauge(
    "active_connections",
    "Active database connections"
)


class PrometheusMiddleware:
    """Middleware to track HTTP requests with Prometheus metrics."""

    def __init__(self, app: FastAPI):
        self.app = app

    async def __call__(self, request: Request, call_next):
        """Process request and record metrics."""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract request info
        method = request.method
        path = request.url.path
        status = response.status_code

        # Normalize endpoint (remove query parameters)
        endpoint = path.split('?')[0]

        # Update metrics
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        return response


def setup_prometheus(app: FastAPI) -> None:
    """Configure Prometheus metrics collection."""
    if not settings.PROMETHEUS_ENABLED:
        return

    # Auto-instrument FastAPI for in-progress tracking
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        env_var_name="PROMETHEUS_MULTIPROC_DIR",
        inprogress_name="fastapi_inprogress",
        inprogress_labels=True,
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    # Add custom middleware for detailed metrics
    app.middleware("http")(PrometheusMiddleware(app))
