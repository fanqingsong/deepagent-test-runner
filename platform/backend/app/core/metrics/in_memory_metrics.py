"""
In-Memory Metrics Collector Implementation

Thread-safe in-memory implementation of metrics collector.
Suitable for development and single-instance deployments.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from collections import defaultdict
import statistics

from app.core.interfaces.metrics_collector_interface import (
    IMetricsCollector,
    TimingStats,
    MetricsSummary,
    TimingMetric,
    CounterMetric,
    GaugeMetric,
    ErrorMetric
)


class InMemoryMetricsCollector(IMetricsCollector):
    """
    In-memory implementation of metrics collector.

    Features:
    - Thread-safe metrics storage using locks
    - Timing statistics with percentiles (p50, p95, p99)
    - Counter aggregation
    - Error tracking by type and operation
    - Gauge value storage
    - Reset capability for testing

    Thread Safety:
        All public methods use threading.Lock for thread-safe operations.

    Example:
        >>> from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
        >>> metrics = InMemoryMetricsCollector()
        >>> metrics.record_timing("database.query", 45.2)
        >>> metrics.record_counter("http.requests", 1)
        >>> stats = metrics.get_timing_stats("database.query")
    """

    def __init__(self):
        """Initialize in-memory metrics storage."""
        # Thread-safe locks
        self._timing_lock = threading.Lock()
        self._counter_lock = threading.Lock()
        self._gauge_lock = threading.Lock()
        self._error_lock = threading.Lock()

        # Storage
        self._timing_data: Dict[str, List[float]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_timing(self, operation: str, duration_ms: float) -> None:
        """
        Record operation execution time.

        Args:
            operation: Operation name
            duration_ms: Execution duration in milliseconds
        """
        if duration_ms < 0:
            raise ValueError(f"Duration must be non-negative: {duration_ms}")

        with self._timing_lock:
            self._timing_data[operation].append(duration_ms)

    def record_counter(self, metric: str, value: int = 1) -> None:
        """
        Record counter increment.

        Args:
            metric: Metric name
            value: Increment value
        """
        if value < 0:
            raise ValueError(f"Counter increment must be non-negative: {value}")

        with self._counter_lock:
            self._counters[metric] += value

    def record_gauge(self, metric: str, value: float) -> None:
        """
        Record gauge value.

        Args:
            metric: Metric name
            value: Current gauge value
        """
        with self._gauge_lock:
            self._gauges[metric] = value

    def record_error(self, operation: str, error_type: str, error_message: str = "") -> None:
        """
        Record error occurrence.

        Args:
            operation: Operation where error occurred
            error_type: Type of error
            error_message: Optional error message
        """
        with self._error_lock:
            self._errors[operation][error_type] += 1

    def get_timing_stats(self, operation: str) -> Optional[TimingStats]:
        """
        Get timing statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            TimingStats or None if no data available
        """
        with self._timing_lock:
            timings = self._timing_data.get(operation)

            if not timings or len(timings) == 0:
                return None

            # Calculate statistics
            timings_sorted = sorted(timings)
            count = len(timings_sorted)

            stats = TimingStats(
                operation=operation,
                count=count,
                min_ms=timings_sorted[0],
                max_ms=timings_sorted[-1],
                avg_ms=statistics.mean(timings_sorted),
                p50_ms=self._calculate_percentile(timings_sorted, 50),
                p95_ms=self._calculate_percentile(timings_sorted, 95),
                p99_ms=self._calculate_percentile(timings_sorted, 99)
            )

            return stats

    def get_all_timing_stats(self) -> Dict[str, TimingStats]:
        """
        Get timing statistics for all operations.

        Returns:
            Dictionary mapping operation names to TimingStats
        """
        with self._timing_lock:
            stats = {}
            for operation in self._timing_data.keys():
                operation_stats = self.get_timing_stats(operation)
                if operation_stats:
                    stats[operation] = operation_stats
            return stats

    def get_counter_value(self, metric: str) -> int:
        """
        Get current counter value.

        Args:
            metric: Metric name

        Returns:
            Current counter value (0 if not found)
        """
        with self._counter_lock:
            return self._counters.get(metric, 0)

    def get_all_counters(self) -> Dict[str, int]:
        """
        Get all counter values.

        Returns:
            Dictionary mapping metric names to values
        """
        with self._counter_lock:
            return dict(self._counters)

    def get_gauge_value(self, metric: str) -> Optional[float]:
        """
        Get current gauge value.

        Args:
            metric: Metric name

        Returns:
            Current gauge value or None if not found
        """
        with self._gauge_lock:
            return self._gauges.get(metric)

    def get_all_gauges(self) -> Dict[str, float]:
        """
        Get all gauge values.

        Returns:
            Dictionary mapping metric names to values
        """
        with self._gauge_lock:
            return dict(self._gauges)

    def get_error_counts(self, operation: Optional[str] = None) -> Dict[str, int]:
        """
        Get error counts by type.

        Args:
            operation: Optional operation filter

        Returns:
            Dictionary mapping error types to counts
        """
        with self._error_lock:
            if operation:
                # Return errors for specific operation
                return dict(self._errors.get(operation, {}))
            else:
                # Aggregate errors across all operations
                aggregated = defaultdict(int)
                for op_errors in self._errors.values():
                    for error_type, count in op_errors.items():
                        aggregated[error_type] += count
                return dict(aggregated)

    def get_metrics_summary(self) -> MetricsSummary:
        """
        Get comprehensive metrics summary.

        Returns:
            MetricsSummary containing all metrics
        """
        # Get timing stats
        timing_stats = self.get_all_timing_stats()

        # Get counters
        counters = self.get_all_counters()

        # Get gauges
        gauges = self.get_all_gauges()

        # Get errors
        with self._error_lock:
            errors_by_operation = {
                op: dict(err_types)
                for op, err_types in self._errors.items()
            }

        # Calculate total recordings
        total_recordings = (
            sum(len(timings) for timings in self._timing_data.values()) +
            sum(self._counters.values()) +
            sum(sum(err_types.values()) for err_types in self._errors.values())
        )

        return MetricsSummary(
            timing_stats=timing_stats,
            counter_values=counters,
            gauge_values=gauges,
            error_counts=errors_by_operation,
            total_recordings=total_recordings
        )

    def reset_metrics(self) -> None:
        """Reset all metrics (primarily for testing)."""
        with self._timing_lock:
            self._timing_data.clear()

        with self._counter_lock:
            self._counters.clear()

        with self._gauge_lock:
            self._gauges.clear()

        with self._error_lock:
            self._errors.clear()

    def reset_operation_metrics(self, operation: str) -> None:
        """
        Reset metrics for a specific operation.

        Args:
            operation: Operation name to reset
        """
        # Reset timing data
        with self._timing_lock:
            if operation in self._timing_data:
                del self._timing_data[operation]

        # Reset errors for this operation
        with self._error_lock:
            if operation in self._errors:
                del self._errors[operation]

    @staticmethod
    def _calculate_percentile(sorted_data: List[float], percentile: int) -> float:
        """
        Calculate percentile value from sorted data.

        Args:
            sorted_data: Sorted list of values
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not sorted_data:
            return 0.0

        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = min(lower + 1, len(sorted_data) - 1)

        if lower == upper:
            return sorted_data[lower]

        # Linear interpolation
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def get_operation_count(self, operation: str) -> int:
        """
        Get the number of recorded timings for an operation.

        Args:
            operation: Operation name

        Returns:
            Number of recorded timings
        """
        with self._timing_lock:
            return len(self._timing_data.get(operation, []))

    def get_all_operations(self) -> List[str]:
        """
        Get list of all operations with recorded timings.

        Returns:
            List of operation names
        """
        with self._timing_lock:
            return list(self._timing_data.keys())

    def get_top_slowest_operations(self, limit: int = 10) -> List[TimingStats]:
        """
        Get the slowest operations by average duration.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of TimingStats ordered by avg_ms descending
        """
        all_stats = list(self.get_all_timing_stats().values())
        all_stats.sort(key=lambda x: x.avg_ms, reverse=True)
        return all_stats[:limit]

    def get_most_errors(self, limit: int = 10) -> Dict[str, Dict[str, int]]:
        """
        Get operations with the most errors.

        Args:
            limit: Maximum number of operations to return

        Returns:
            Dictionary mapping operation names to error counts
        """
        with self._error_lock:
            # Sort by total error count
            ops_with_errors = [
                (op, sum(err_types.values()))
                for op, err_types in self._errors.items()
            ]
            ops_with_errors.sort(key=lambda x: x[1], reverse=True)

            return {
                op: dict(self._errors[op])
                for op, _ in ops_with_errors[:limit]
            }
