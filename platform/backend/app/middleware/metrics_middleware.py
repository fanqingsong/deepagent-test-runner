"""
Metrics Middleware

FastAPI middleware for automatic HTTP request metrics collection.
Tracks request timing, counts, errors, and endpoint performance.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.interfaces.metrics_collector_interface import IMetricsCollector

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP request metrics.

    Features:
    - Request timing by endpoint and method
    - Request counts by status code
    - Error tracking by endpoint
    - Active request gauge
    - Response size tracking

    Metrics Collected:
    - http.requests.{method}.{path}: Request timing
    - http.requests.total: Total request count
    - http.requests.active: Currently active requests (gauge)
    - http.requests.status.{status_code}: Count by status
    - http.errors.{error_type}: Error occurrences

    Example:
        >>> from app.middleware.metrics_middleware import MetricsMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(MetricsMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        metrics_collector: IMetricsCollector,
        track_paths: bool = True,
        track_status_codes: bool = True,
        track_errors: bool = True
    ):
        """
        Initialize metrics middleware.

        Args:
            app: ASGI application
            metrics_collector: Metrics collector instance
            track_paths: Track metrics by path (default: True)
            track_status_codes: Track status code counts (default: True)
            track_errors: Track errors (default: True)
        """
        super().__init__(app)
        self.metrics_collector = metrics_collector
        self.track_paths = track_paths
        self.track_status_codes = track_status_codes
        self.track_errors = track_errors

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response
        """
        # Start timing
        start_time = time.perf_counter()

        # Increment active requests gauge
        self.metrics_collector.record_counter("http.requests.active", 1)

        # Get request info
        method = request.method
        path = request.url.path

        try:
            # Process request
            response: Response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record timing by endpoint
            if self.track_paths:
                operation_name = f"http.requests.{method.lower()}.{self._sanitize_path(path)}"
                self.metrics_collector.record_timing(operation_name, duration_ms)

            # Record status code count
            if self.track_status_codes:
                status_metric = f"http.requests.status.{response.status_code}"
                self.metrics_collector.record_counter(status_metric, 1)

            # Record total requests
            self.metrics_collector.record_counter("http.requests.total", 1)

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record error timing
            if self.track_paths:
                operation_name = f"http.requests.{method.lower()}.{self._sanitize_path(path)}"
                self.metrics_collector.record_timing(operation_name, duration_ms)

            # Record error
            if self.track_errors:
                error_type = type(e).__name__
                self.metrics_collector.record_error(
                    f"http.requests.{method.lower()}",
                    error_type,
                    str(e)
                )

            # Re-raise exception
            raise

        finally:
            # Decrement active requests gauge
            self.metrics_collector.record_counter("http.requests.active", -1)

    @staticmethod
    def _sanitize_path(path: str) -> str:
        """
        Sanitize URL path for metric names.

        Replaces path parameters with placeholders and removes IDs.

        Args:
            path: URL path

        Returns:
            Sanitized path string
        """
        # Remove query parameters
        path = path.split("?")[0]

        # Replace common path parameters
        segments = path.split("/")
        sanitized_segments = []

        for segment in segments:
            # Replace numeric IDs
            if segment.isdigit():
                sanitized_segments.append(":id")
            # Replace UUIDs (simplified check)
            elif len(segment) == 36 and segment.count("-") == 4:
                sanitized_segments.append(":uuid")
            else:
                sanitized_segments.append(segment)

        return "/".join(sanitized_segments)


class DetailedMetricsMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware with detailed request/response metrics.

    Additional Features:
    - Request/response size tracking
    - User-agent tracking
    - Request size by endpoint
    - Slow request logging
    """

    def __init__(
        self,
        app: ASGIApp,
        metrics_collector: IMetricsCollector,
        slow_request_threshold_ms: float = 1000.0,
        log_slow_requests: bool = True
    ):
        """
        Initialize detailed metrics middleware.

        Args:
            app: ASGI application
            metrics_collector: Metrics collector instance
            slow_request_threshold_ms: Threshold for slow requests (default: 1000ms)
            log_slow_requests: Log slow requests (default: True)
        """
        super().__init__(app)
        self.metrics_collector = metrics_collector
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.log_slow_requests = log_slow_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with detailed metrics collection.
        """
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        # Track active requests by client
        self.metrics_collector.record_counter("http.requests.active", 1)

        try:
            # Process request
            response: Response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record timing
            operation_name = f"http.requests.{method.lower()}.{self._sanitize_path(path)}"
            self.metrics_collector.record_timing(operation_name, duration_ms)

            # Record status
            status_metric = f"http.requests.status.{response.status_code}"
            self.metrics_collector.record_counter(status_metric, 1)

            # Record total requests
            self.metrics_collector.record_counter("http.requests.total", 1)

            # Log slow requests
            if self.log_slow_requests and duration_ms > self.slow_request_threshold_ms:
                logger.warning(
                    f"Slow request detected: {method} {path} "
                    f"took {duration_ms:.2f}ms from {client_host}"
                )
                self.metrics_collector.record_counter("http.requests.slow", 1)

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record error
            operation_name = f"http.requests.{method.lower()}.{self._sanitize_path(path)}"
            self.metrics_collector.record_timing(operation_name, duration_ms)
            self.metrics_collector.record_error(
                operation_name,
                type(e).__name__,
                f"{method} {path}: {str(e)}"
            )

            raise

        finally:
            self.metrics_collector.record_counter("http.requests.active", -1)

    @staticmethod
    def _sanitize_path(path: str) -> str:
        """Sanitize URL path for metric names."""
        path = path.split("?")[0]
        segments = path.split("/")
        sanitized_segments = []

        for segment in segments:
            if segment.isdigit():
                sanitized_segments.append(":id")
            elif len(segment) == 36 and segment.count("-") == 4:
                sanitized_segments.append(":uuid")
            else:
                sanitized_segments.append(segment)

        return "/".join(sanitized_segments)
