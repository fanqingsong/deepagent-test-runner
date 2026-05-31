"""
Centralized observability setup for metrics, logging, and tracing.
"""

from fastapi import FastAPI
from app.middleware.prometheus import setup_prometheus
from app.middleware.logging import LoggingMiddleware
from app.middleware.tracing import setup_tracing
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI) -> None:
    """
    Initialize all observability systems.

    Order matters:
    1. Tracing (must be first to instrument all requests)
    2. Prometheus (metrics collection)
    3. Logging (structured logging with correlation)
    """
    # 1. Setup distributed tracing
    if settings.JAEGER_ENABLED:
        setup_tracing(app)
        logger.info("Jaeger tracing enabled")
    else:
        logger.info("Jaeger tracing disabled")

    # 2. Setup Prometheus metrics
    if settings.PROMETHEUS_ENABLED:
        setup_prometheus(app)
        logger.info("Prometheus metrics enabled")
    else:
        logger.info("Prometheus metrics disabled")

    # 3. Setup structured logging middleware
    if settings.LOKI_ENABLED or settings.LOG_FORMAT == "json":
        from app.middleware.logging import LoggingMiddleware
        app.middleware("http")(LoggingMiddleware())
        logger.info(f"Structured logging enabled (format={settings.LOG_FORMAT})")
    else:
        logger.info("Structured logging disabled, using default logging")

    logger.info(f"Observability initialized: tracing={settings.JAEGER_ENABLED}, metrics={settings.PROMETHEUS_ENABLED}, loki={settings.LOKI_ENABLED}")
