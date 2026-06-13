"""
Metrics Module

Provides comprehensive performance metrics collection for the application.

Components:
- InMemoryMetricsCollector: Thread-safe in-memory metrics storage
- Metrics decorators: Automatic instrumentation via decorators
- Metrics middleware: HTTP request metrics collection

Usage:
    from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
    from app.core.metrics.metrics_decorators import track_timing, track_metrics

    # Create collector
    collector = InMemoryMetricsCollector()

    # Use decorators
    @track_timing("database.query", collector)
    async def query_data():
        # ... implementation
        pass

    # Use context manager
    with track_operation("custom.operation", collector):
        # ... code to time
        pass
"""

from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
from app.core.metrics.metrics_decorators import (
    track_timing,
    track_errors,
    track_metrics,
    track_counter,
    track_operation
)

__all__ = [
    "InMemoryMetricsCollector",
    "track_timing",
    "track_errors",
    "track_metrics",
    "track_counter",
    "track_operation",
]
