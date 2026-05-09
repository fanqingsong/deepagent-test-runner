"""
Prometheus metrics middleware for FastAPI applications.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Response
from app.core.config import settings


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


def setup_prometheus(app: FastAPI) -> None:
    """Configure Prometheus metrics collection."""
    if not settings.PROMETHEUS_ENABLED:
        return

    # Auto-instrument FastAPI
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        should_instrument_requests_cancellation=True,
        excluded_handlers=["/metrics"],
        env_var_name="PROMETHEUS_MULTIPROC_DIR",
        inprogress_name="fastapi_inprogress",
        inprogress_labels=True,
    )
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # Add custom metrics endpoint (alternative to instrumentator.expose)
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
