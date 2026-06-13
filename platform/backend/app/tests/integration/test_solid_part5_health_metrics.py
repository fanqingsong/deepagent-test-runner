"""
SOLID Verification Part 5: Health Checks & Metrics

Tests health check and metrics systems follow SOLID principles:
- Single responsibility (each checker has one job)
- Interface segregation (focused interfaces)
- Liskov substitution (all checkers are interchangeable)
"""

import pytest
import asyncio

from app.health.checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    LLMHealthChecker,
    TemporalHealthChecker,
    FileSystemHealthChecker
)
from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
from app.core.interfaces.metrics_collector_interface import IMetricsCollector


class TestHealthChecks:
    """Verify health check system works correctly."""

    @pytest.mark.asyncio
    async def test_all_health_checkers_exist(self):
        """Test all 5 health checkers can be instantiated."""
        # Database health checker
        db_checker = DatabaseHealthChecker()
        assert db_checker is not None
        assert hasattr(db_checker, 'check_health')

        # Redis health checker
        redis_checker = RedisHealthChecker()
        assert redis_checker is not None
        assert hasattr(redis_checker, 'check_health')

        # LLM health checker
        llm_checker = LLMHealthChecker()
        assert llm_checker is not None
        assert hasattr(llm_checker, 'check_health')

        # Temporal health checker
        temporal_checker = TemporalHealthChecker()
        assert temporal_checker is not None
        assert hasattr(temporal_checker, 'check_health')

        # FileSystem health checker
        fs_checker = FileSystemHealthChecker()
        assert fs_checker is not None
        assert hasattr(fs_checker, 'check_health')

    @pytest.mark.asyncio
    async def test_health_check_return_types(self):
        """Test health checkers return proper result types."""
        db_checker = DatabaseHealthChecker()
        result = await db_checker.check_health()

        # Should have expected fields
        assert 'status' in result
        assert 'component' in result
        assert result['component'] == 'database'
        assert result['status'] in ['healthy', 'unhealthy', 'degraded']

    @pytest.mark.asyncio
    async def test_health_check_parallel_execution(self):
        """Test health checks can run in parallel."""
        import time

        checkers = [
            DatabaseHealthChecker(),
            RedisHealthChecker(),
            FileSystemHealthChecker()
        ]

        # Run all checks in parallel
        start_time = time.time()
        results = await asyncio.gather(*[checker.check_health() for checker in checkers])
        elapsed = time.time() - start_time

        # All should return results
        assert len(results) == 3
        for result in results:
            assert 'status' in result
            assert 'component' in result

        # Parallel execution should be faster than sequential
        assert elapsed < 5  # Should complete reasonably quickly

    @pytest.mark.asyncio
    async def test_health_check_single_responsibility(self):
        """Test each health checker has single responsibility."""
        db_checker = DatabaseHealthChecker()

        # Should only have health check method
        assert hasattr(db_checker, 'check_health')

        # Should not have unrelated methods
        assert not hasattr(db_checker, 'execute_query')
        assert not hasattr(db_checker, 'create_table')


class TestMetricsSystem:
    """Verify metrics collection system works correctly."""

    @pytest.mark.asyncio
    async def test_metrics_collector_interface(self):
        """Test metrics collector implements interface correctly."""
        collector = InMemoryMetricsCollector()

        # Should implement IMetricsCollector
        assert isinstance(collector, IMetricsCollector)

        # Should have required methods
        assert hasattr(collector, 'record_timing')
        assert hasattr(collector, 'record_counter')
        assert hasattr(collector, 'record_gauge')
        assert hasattr(collector, 'record_error')
        assert hasattr(collector, 'get_timing_stats')
        assert hasattr(collector, 'get_all_timing_stats')

    @pytest.mark.asyncio
    async def test_metrics_timing_collection(self):
        """Test timing metrics are collected correctly."""
        collector = InMemoryMetricsCollector()

        # Record some timings
        collector.record_timing("database.query", 45.2)
        collector.record_timing("database.query", 50.1)
        collector.record_timing("database.query", 38.7)

        # Get stats
        stats = collector.get_timing_stats("database.query")

        assert stats is not None
        assert stats.operation == "database.query"
        assert stats.count == 3
        assert stats.min_ms == 38.7
        assert stats.max_ms == 50.1
        assert 40 < stats.avg_ms < 50

    @pytest.mark.asyncio
    async def test_metrics_counter_collection(self):
        """Test counter metrics are collected correctly."""
        collector = InMemoryMetricsCollector()

        # Increment counter
        collector.record_counter("http.requests", 1)
        collector.record_counter("http.requests", 1)
        collector.record_counter("http.requests", 2)

        # Get counter value (via summary)
        summary = collector.get_metrics_summary()

        assert "http.requests" in summary["counters"]
        assert summary["counters"]["http.requests"] == 4

    @pytest.mark.asyncio
    async def test_metrics_error_tracking(self):
        """Test error metrics are tracked correctly."""
        collector = InMemoryMetricsCollector()

        # Record errors
        collector.record_error("database.query", "ConnectionError", "Connection timeout")
        collector.record_error("database.query", "TimeoutError", "Query timeout")
        collector.record_error("api.call", "ValidationError", "Invalid input")

        # Get error summary
        summary = collector.get_metrics_summary()

        assert "database.query" in summary["errors"]
        assert summary["errors"]["database.query"]["ConnectionError"] == 1
        assert summary["errors"]["database.query"]["TimeoutError"] == 1

    @pytest.mark.asyncio
    async def test_metrics_thread_safety(self):
        """Test metrics collection is thread-safe."""
        import threading

        collector = InMemoryMetricsCollector()

        def record_timings():
            for i in range(100):
                collector.record_timing("test.operation", i * 1.0)

        # Create multiple threads
        threads = [threading.Thread(target=record_timings) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all timings were recorded
        stats = collector.get_timing_stats("test.operation")
        assert stats.count == 500  # 5 threads * 100 iterations
