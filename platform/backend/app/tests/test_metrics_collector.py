"""
Metrics Collector Tests

Comprehensive tests for the metrics collection system.
"""

import pytest
import time
from typing import Dict, Any

from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
from app.core.interfaces.metrics_collector_interface import TimingStats, MetricsSummary


class TestInMemoryMetricsCollector:
    """Test suite for InMemoryMetricsCollector."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a fresh metrics collector for each test."""
        collector = InMemoryMetricsCollector()
        yield collector
        collector.reset_metrics()

    def test_record_timing_single(self, metrics_collector: InMemoryMetricsCollector):
        """Test recording a single timing metric."""
        metrics_collector.record_timing("test.operation", 100.5)

        stats = metrics_collector.get_timing_stats("test.operation")

        assert stats is not None
        assert stats.operation == "test.operation"
        assert stats.count == 1
        assert stats.min_ms == 100.5
        assert stats.max_ms == 100.5
        assert stats.avg_ms == 100.5

    def test_record_timing_multiple(self, metrics_collector: InMemoryMetricsCollector):
        """Test recording multiple timing metrics."""
        timings = [50.0, 100.0, 150.0, 200.0, 250.0]

        for timing in timings:
            metrics_collector.record_timing("test.operation", timing)

        stats = metrics_collector.get_timing_stats("test.operation")

        assert stats.count == 5
        assert stats.min_ms == 50.0
        assert stats.max_ms == 250.0
        assert stats.avg_ms == 150.0  # (50+100+150+200+250)/5

    def test_record_timing_percentiles(self, metrics_collector: InMemoryMetricsCollector):
        """Test percentile calculations."""
        # Create 100 timings from 1 to 100
        for i in range(1, 101):
            metrics_collector.record_timing("test.operation", float(i))

        stats = metrics_collector.get_timing_stats("test.operation")

        assert stats.p50_ms == 50.0  # 50th percentile
        assert stats.p95_ms == 95.0  # 95th percentile
        assert stats.p99_ms == 99.0  # 99th percentile

    def test_record_counter(self, metrics_collector: InMemoryMetricsCollector):
        """Test recording counter metrics."""
        metrics_collector.record_counter("test.metric", 5)
        metrics_collector.record_counter("test.metric", 3)

        assert metrics_collector.get_counter_value("test.metric") == 8

    def test_record_gauge(self, metrics_collector: InMemoryMetricsCollector):
        """Test recording gauge metrics."""
        metrics_collector.record_gauge("test.gauge", 42.5)
        metrics_collector.record_gauge("test.gauge", 99.9)

        assert metrics_collector.get_gauge_value("test.gauge") == 99.9

    def test_record_error(self, metrics_collector: InMemoryMetricsCollector):
        """Test recording error metrics."""
        metrics_collector.record_error("test.operation", "ValueError", "Test error")
        metrics_collector.record_error("test.operation", "ValueError", "Another error")
        metrics_collector.record_error("test.operation", "TimeoutError", "Timeout")

        error_counts = metrics_collector.get_error_counts("test.operation")

        assert error_counts["ValueError"] == 2
        assert error_counts["TimeoutError"] == 1

    def test_get_timing_stats_nonexistent(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting stats for non-existent operation."""
        stats = metrics_collector.get_timing_stats("nonexistent.operation")

        assert stats is None

    def test_get_all_timing_stats(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting all timing stats."""
        metrics_collector.record_timing("operation1", 100.0)
        metrics_collector.record_timing("operation2", 200.0)

        all_stats = metrics_collector.get_all_timing_stats()

        assert len(all_stats) == 2
        assert "operation1" in all_stats
        assert "operation2" in all_stats

    def test_get_all_counters(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting all counters."""
        metrics_collector.record_counter("metric1", 10)
        metrics_collector.record_counter("metric2", 20)

        all_counters = metrics_collector.get_all_counters()

        assert len(all_counters) == 2
        assert all_counters["metric1"] == 10
        assert all_counters["metric2"] == 20

    def test_get_all_gauges(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting all gauges."""
        metrics_collector.record_gauge("gauge1", 1.5)
        metrics_collector.record_gauge("gauge2", 2.5)

        all_gauges = metrics_collector.get_all_gauges()

        assert len(all_gauges) == 2
        assert all_gauges["gauge1"] == 1.5
        assert all_gauges["gauge2"] == 2.5

    def test_get_metrics_summary(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting comprehensive metrics summary."""
        # Record various metrics
        metrics_collector.record_timing("test.operation", 100.0)
        metrics_collector.record_counter("test.counter", 5)
        metrics_collector.record_gauge("test.gauge", 42.0)
        metrics_collector.record_error("test.operation", "ValueError", "Test error")

        summary = metrics_collector.get_metrics_summary()

        assert isinstance(summary, MetricsSummary)
        assert len(summary.timing_stats) == 1
        assert len(summary.counter_values) == 1
        assert len(summary.gauge_values) == 1
        assert len(summary.error_counts) == 1
        assert summary.total_recordings == 4

    def test_reset_metrics(self, metrics_collector: InMemoryMetricsCollector):
        """Test resetting all metrics."""
        # Record some metrics
        metrics_collector.record_timing("test.operation", 100.0)
        metrics_collector.record_counter("test.counter", 5)

        # Reset
        metrics_collector.reset_metrics()

        # Verify all cleared
        assert metrics_collector.get_timing_stats("test.operation") is None
        assert metrics_collector.get_counter_value("test.counter") == 0
        assert len(metrics_collector.get_all_gauges()) == 0
        assert len(metrics_collector.get_error_counts("test.operation")) == 0

    def test_reset_operation_metrics(self, metrics_collector: InMemoryMetricsCollector):
        """Test resetting metrics for specific operation."""
        # Record metrics for two operations
        metrics_collector.record_timing("operation1", 100.0)
        metrics_collector.record_timing("operation2", 200.0)
        metrics_collector.record_error("operation1", "ValueError", "Test")

        # Reset only operation1
        metrics_collector.reset_operation_metrics("operation1")

        # Verify operation1 cleared, operation2 still present
        assert metrics_collector.get_timing_stats("operation1") is None
        assert metrics_collector.get_timing_stats("operation2") is not None
        assert len(metrics_collector.get_error_counts("operation1")) == 0

    def test_get_operation_count(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting operation recording count."""
        for _ in range(5):
            metrics_collector.record_timing("test.operation", 100.0)

        count = metrics_collector.get_operation_count("test.operation")

        assert count == 5

    def test_get_all_operations(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting list of all operations."""
        metrics_collector.record_timing("operation1", 100.0)
        metrics_collector.record_timing("operation2", 200.0)
        metrics_collector.record_timing("operation3", 300.0)

        operations = metrics_collector.get_all_operations()

        assert len(operations) == 3
        assert "operation1" in operations
        assert "operation2" in operations
        assert "operation3" in operations

    def test_get_top_slowest_operations(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting slowest operations."""
        # Record operations with different average times
        for _ in range(3):
            metrics_collector.record_timing("fast", 10.0)

        for _ in range(3):
            metrics_collector.record_timing("medium", 100.0)

        for _ in range(3):
            metrics_collector.record_timing("slow", 500.0)

        slowest = metrics_collector.get_top_slowest_operations(limit=2)

        assert len(slowest) == 2
        assert slowest[0].operation == "slow"
        assert slowest[0].avg_ms == 500.0
        assert slowest[1].operation == "medium"

    def test_get_most_errors(self, metrics_collector: InMemoryMetricsCollector):
        """Test getting operations with most errors."""
        # Record errors for different operations
        for _ in range(5):
            metrics_collector.record_error("operation1", "ValueError", "Test")

        for _ in range(3):
            metrics_collector.record_error("operation2", "TimeoutError", "Test")

        for _ in range(1):
            metrics_collector.record_error("operation3", "ValueError", "Test")

        most_errors = metrics_collector.get_most_errors(limit=2)

        assert len(most_errors) == 2
        assert "operation1" in most_errors
        assert sum(most_errors["operation1"].values()) == 5

    def test_negative_duration_validation(self, metrics_collector: InMemoryMetricsCollector):
        """Test that negative durations are rejected."""
        with pytest.raises(ValueError, match="non-negative"):
            metrics_collector.record_timing("test.operation", -10.0)

    def test_negative_counter_validation(self, metrics_collector: InMemoryMetricsCollector):
        """Test that negative counter increments are rejected."""
        with pytest.raises(ValueError, match="non-negative"):
            metrics_collector.record_counter("test.metric", -5)

    def test_aggregated_error_counts(self, metrics_collector: InMemoryMetricsCollector):
        """Test aggregated error counts across operations."""
        metrics_collector.record_error("operation1", "ValueError", "Test")
        metrics_collector.record_error("operation2", "ValueError", "Test")
        metrics_collector.record_error("operation1", "TimeoutError", "Test")

        # Get aggregated errors (no operation filter)
        aggregated = metrics_collector.get_error_counts()

        assert aggregated["ValueError"] == 2
        assert aggregated["TimeoutError"] == 1


class TestMetricsDecorators:
    """Test suite for metrics decorators."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a fresh metrics collector for each test."""
        collector = InMemoryMetricsCollector()
        yield collector
        collector.reset_metrics()

    def test_track_timing_decorator_sync(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_timing decorator with sync function."""
        from app.core.metrics.metrics_decorators import track_timing

        @track_timing("test.operation", metrics_collector)
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"

        stats = metrics_collector.get_timing_stats("test.operation")
        assert stats is not None
        assert stats.count == 1
        assert stats.min_ms > 0

    def test_track_timing_decorator_async(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_timing decorator with async function."""
        import asyncio
        from app.core.metrics.metrics_decorators import track_timing

        @track_timing("test.operation", metrics_collector)
        async def test_function():
            await asyncio.sleep(0.01)
            return "result"

        async def run_test():
            result = await test_function()
            return result

        result = asyncio.run(run_test())

        assert result == "result"

        stats = metrics_collector.get_timing_stats("test.operation")
        assert stats is not None
        assert stats.count == 1
        assert stats.min_ms > 0

    def test_track_errors_decorator(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_errors decorator."""
        from app.core.metrics.metrics_decorators import track_errors

        @track_errors("test.operation", metrics_collector)
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_function()

        error_counts = metrics_collector.get_error_counts("test.operation")
        assert error_counts["ValueError"] == 1

    def test_track_metrics_decorator(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_metrics decorator (combined timing and errors)."""
        from app.core.metrics.metrics_decorators import track_metrics

        @track_metrics("test.operation", metrics_collector)
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()

        assert result == "success"

        stats = metrics_collector.get_timing_stats("test.operation")
        assert stats is not None

    def test_track_counter_decorator(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_counter decorator."""
        from app.core.metrics.metrics_decorators import track_counter

        @track_counter("test.calls", 1, metrics_collector)
        def test_function():
            return "result"

        test_function()
        test_function()
        test_function()

        count = metrics_collector.get_counter_value("test.calls")
        assert count == 3

    def test_track_operation_context_manager(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_operation context manager."""
        from app.core.metrics.metrics_decorators import track_operation

        with track_operation("test.operation", metrics_collector):
            time.sleep(0.01)

        stats = metrics_collector.get_timing_stats("test.operation")
        assert stats is not None
        assert stats.count == 1

    def test_track_operation_with_error(self, metrics_collector: InMemoryMetricsCollector):
        """Test track_operation context manager with error."""
        from app.core.metrics.metrics_decorators import track_operation

        with pytest.raises(ValueError):
            with track_operation("test.operation", metrics_collector):
                raise ValueError("Test error")

        stats = metrics_collector.get_timing_stats("test.operation")
        assert stats is not None

        error_counts = metrics_collector.get_error_counts("test.operation")
        assert error_counts["ValueError"] == 1


class TestMetricsIntegration:
    """Integration tests for metrics system."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a fresh metrics collector for each test."""
        collector = InMemoryMetricsCollector()
        yield collector
        collector.reset_metrics()

    def test_concurrent_recording(self, metrics_collector: InMemoryMetricsCollector):
        """Test thread-safe concurrent recording."""
        import threading

        def record_timings():
            for i in range(100):
                metrics_collector.record_timing("concurrent.test", float(i))

        # Create multiple threads
        threads = [threading.Thread(target=record_timings) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all recordings
        stats = metrics_collector.get_timing_stats("concurrent.test")
        assert stats.count == 500  # 100 * 5 threads

    def test_metrics_persistence_across_operations(self, metrics_collector: InMemoryMetricsCollector):
        """Test that metrics persist across multiple operations."""
        # Simulate a workflow
        operations = [
            ("database.query", 50.0),
            ("database.query", 75.0),
            ("service.process", 200.0),
            ("service.process", 250.0),
            ("api.request", 100.0),
        ]

        for operation, duration in operations:
            metrics_collector.record_timing(operation, duration)

        # Verify all operations recorded
        all_stats = metrics_collector.get_all_timing_stats()
        assert len(all_stats) == 3

        # Verify individual stats
        db_stats = metrics_collector.get_timing_stats("database.query")
        assert db_stats.count == 2
        assert db_stats.avg_ms == 62.5

    def test_realistic_workflow_simulation(self, metrics_collector: InMemoryMetricsCollector):
        """Test metrics collection in realistic workflow."""
        # Simulate test execution workflow
        metrics_collector.record_counter("test.runs.started", 1)
        metrics_collector.record_timing("test.run.create", 45.0)
        metrics_collector.record_timing("test.execution", 1234.5)
        metrics_collector.record_counter("test.cases.total", 10)
        metrics_collector.record_counter("test.cases.passed", 8)
        metrics_collector.record_counter("test.cases.failed", 2)
        metrics_collector.record_timing("test.results.save", 78.0)

        summary = metrics_collector.get_metrics_summary()

        assert summary.counter_values["test.runs.started"] == 1
        assert summary.counter_values["test.cases.passed"] == 8
        assert summary.counter_values["test.cases.failed"] == 2

        assert len(summary.timing_stats) == 3
        assert "test.run.create" in summary.timing_stats
        assert "test.execution" in summary.timing_stats
        assert "test.results.save" in summary.timing_stats
