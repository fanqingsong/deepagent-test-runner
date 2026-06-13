"""
Metrics Collector Interface

Defines the abstraction for performance metrics collection following SOLID principles.
This interface enables different implementations (in-memory, Redis, Prometheus, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class TimingMetric:
    """Timing metric data structure."""
    operation: str
    duration_ms: float
    timestamp: float


@dataclass
class CounterMetric:
    """Counter metric data structure."""
    metric: str
    value: int
    timestamp: float


@dataclass
class GaugeMetric:
    """Gauge metric data structure."""
    metric: str
    value: float
    timestamp: float


@dataclass
class ErrorMetric:
    """Error metric data structure."""
    operation: str
    error_type: str
    error_message: str
    timestamp: float


@dataclass
class TimingStats:
    """Timing statistics for an operation."""
    operation: str
    count: int
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class MetricsSummary:
    """Overall metrics summary."""
    timing_stats: Dict[str, TimingStats]
    counter_values: Dict[str, int]
    gauge_values: Dict[str, float]
    error_counts: Dict[str, Dict[str, int]]
    total_recordings: int


class IMetricsCollector(ABC):
    """
    Interface for metrics collection.

    This interface defines the contract for collecting and managing performance metrics.
    Implementations can store metrics in-memory, Redis, or push to external systems.

    Principles:
    - Interface Segregation: Focused on metrics collection only
    - Dependency Inversion: High-level services depend on this abstraction
    - Single Responsibility: Only concerned with metrics collection
    """

    @abstractmethod
    def record_timing(self, operation: str, duration_ms: float) -> None:
        """
        Record operation execution time.

        Args:
            operation: Operation name (e.g., 'database.test_run.create')
            duration_ms: Execution duration in milliseconds
        """
        pass

    @abstractmethod
    def record_counter(self, metric: str, value: int = 1) -> None:
        """
        Record counter increment.

        Args:
            metric: Metric name (e.g., 'http.requests.total')
            value: Increment value (default: 1)
        """
        pass

    @abstractmethod
    def record_gauge(self, metric: str, value: float) -> None:
        """
        Record gauge value.

        Args:
            metric: Metric name (e.g., 'database.connections.active')
            value: Current gauge value
        """
        pass

    @abstractmethod
    def record_error(self, operation: str, error_type: str, error_message: str = "") -> None:
        """
        Record error occurrence.

        Args:
            operation: Operation where error occurred
            error_type: Type of error (e.g., 'ValueError', 'TimeoutError')
            error_message: Optional error message
        """
        pass

    @abstractmethod
    def get_timing_stats(self, operation: str) -> Optional[TimingStats]:
        """
        Get timing statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            TimingStats or None if no data available
        """
        pass

    @abstractmethod
    def get_all_timing_stats(self) -> Dict[str, TimingStats]:
        """
        Get timing statistics for all operations.

        Returns:
            Dictionary mapping operation names to TimingStats
        """
        pass

    @abstractmethod
    def get_counter_value(self, metric: str) -> int:
        """
        Get current counter value.

        Args:
            metric: Metric name

        Returns:
            Current counter value
        """
        pass

    @abstractmethod
    def get_all_counters(self) -> Dict[str, int]:
        """
        Get all counter values.

        Returns:
            Dictionary mapping metric names to values
        """
        pass

    @abstractmethod
    def get_gauge_value(self, metric: str) -> Optional[float]:
        """
        Get current gauge value.

        Args:
            metric: Metric name

        Returns:
            Current gauge value or None if not found
        """
        pass

    @abstractmethod
    def get_all_gauges(self) -> Dict[str, float]:
        """
        Get all gauge values.

        Returns:
            Dictionary mapping metric names to values
        """
        pass

    @abstractmethod
    def get_error_counts(self, operation: Optional[str] = None) -> Dict[str, int]:
        """
        Get error counts by type.

        Args:
            operation: Optional operation filter

        Returns:
            Dictionary mapping error types to counts
        """
        pass

    @abstractmethod
    def get_metrics_summary(self) -> MetricsSummary:
        """
        Get comprehensive metrics summary.

        Returns:
            MetricsSummary containing all metrics
        """
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset all metrics (primarily for testing)."""
        pass

    @abstractmethod
    def reset_operation_metrics(self, operation: str) -> None:
        """
        Reset metrics for a specific operation.

        Args:
            operation: Operation name to reset
        """
        pass
