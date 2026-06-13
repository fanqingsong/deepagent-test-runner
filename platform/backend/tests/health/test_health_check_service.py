"""
Tests for Health Check Service

Tests the health check service orchestration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.health_check_service import HealthCheckService
from app.core.health_check_types import (
    HealthCheckConfig,
    HealthStatus,
    ComponentHealth,
)


class TestHealthCheckService:
    """Test HealthCheckService."""

    @pytest.fixture
    def service(self):
        """Create health check service instance."""
        return HealthCheckService()

    @pytest.fixture
    def mock_checkers(self):
        """Create mock health checkers."""
        healthy_checker = Mock(spec=Mock)
        healthy_checker.get_check_type.return_value = "healthy"
        healthy_checker.is_critical.return_value = True
        healthy_checker.should_run.return_value = True
        healthy_checker.safe_check = AsyncMock(return_value=ComponentHealth(
            component_name="healthy",
            status=HealthStatus.HEALTHY,
            details="OK",
            is_critical=True,
        ))

        unhealthy_checker = Mock(spec=Mock)
        unhealthy_checker.get_check_type.return_value = "unhealthy"
        unhealthy_checker.is_critical.return_value = False
        unhealthy_checker.should_run.return_value = True
        unhealthy_checker.safe_check = AsyncMock(return_value=ComponentHealth(
            component_name="unhealthy",
            status=HealthStatus.UNHEALTHY,
            details="Failed",
            is_critical=False,
        ))

        return [healthy_checker, unhealthy_checker]

    def test_get_checker(self, service):
        """Test getting a specific checker."""
        checker = service.get_checker("database")
        assert checker is not None
        assert checker.get_check_type() == "database"

    def test_get_checker_not_found(self, service):
        """Test getting non-existent checker."""
        checker = service.get_checker("nonexistent")
        assert checker is None

    @pytest.mark.asyncio
    async def test_check_health_parallel(self, service, mock_checkers):
        """Test parallel health check execution."""
        service.checkers = mock_checkers

        config = HealthCheckConfig(
            parallel_execution=True,
        )

        result = await service.check_health(config)

        assert result.status == HealthStatus.DEGRADED  # 1 unhealthy component
        assert result.total_components == 2
        assert result.healthy_components == 1
        assert result.unhealthy_components == 1

    @pytest.mark.asyncio
    async def test_check_health_sequential(self, service, mock_checkers):
        """Test sequential health check execution."""
        service.checkers = mock_checkers

        config = HealthCheckConfig(
            parallel_execution=False,
        )

        result = await service.check_health(config)

        assert result.total_components == 2
        assert "healthy" in result.components
        assert "unhealthy" in result.components

    @pytest.mark.asyncio
    async def test_check_health_critical_only(self, service):
        """Test checking only critical components."""
        # Mock checkers
        critical_checker = Mock(spec=Mock)
        critical_checker.get_check_type.return_value = "critical"
        critical_checker.is_critical.return_value = True
        critical_checker.should_run.return_value = True
        critical_checker.safe_check = AsyncMock(return_value=ComponentHealth(
            component_name="critical",
            status=HealthStatus.HEALTHY,
            details="OK",
            is_critical=True,
        ))

        non_critical_checker = Mock(spec=Mock)
        non_critical_checker.get_check_type.return_value = "non_critical"
        non_critical_checker.is_critical.return_value = False
        non_critical_checker.should_run.return_value = False  # Should not run
        non_critical_checker.safe_check = AsyncMock(return_value=ComponentHealth(
            component_name="non_critical",
            status=HealthStatus.HEALTHY,
            details="OK",
            is_critical=False,
        ))

        service.checkers = [critical_checker, non_critical_checker]

        config = HealthCheckConfig(
            critical_only=True,
        )

        result = await service.check_health(config)

        assert result.total_components == 1
        assert "critical" in result.components
        assert "non_critical" not in result.components

    @pytest.mark.asyncio
    async def test_check_component_success(self, service):
        """Test checking a specific component."""
        mock_checker = Mock(spec=Mock)
        mock_checker.get_check_type.return_value = "test"
        mock_checker.is_critical.return_value = True
        mock_checker.safe_check = AsyncMock(return_value=ComponentHealth(
            component_name="test",
            status=HealthStatus.HEALTHY,
            details="OK",
            is_critical=True,
        ))

        service.checkers = [mock_checker]

        result = await service.check_component("test")

        assert result.status == HealthStatus.HEALTHY
        assert result.component_name == "test"

    @pytest.mark.asyncio
    async def test_check_component_not_found(self, service):
        """Test checking non-existent component."""
        with pytest.raises(ValueError, match="Unknown component type"):
            await service.check_component("nonexistent")

    @pytest.mark.asyncio
    async def test_check_critical_only_method(self, service, mock_checkers):
        """Test the check_critical_only convenience method."""
        service.checkers = mock_checkers

        result = await service.check_critical_only()

        assert result is not None
        assert isinstance(result.total_components, int)

    def test_get_status_summary_no_cache(self, service):
        """Test status summary without cache."""
        summary = service.get_status_summary()

        assert summary["status"] == "unknown"
        assert "No health check data available" in summary["message"]

    def test_get_status_summary_with_cache(self, service):
        """Test status summary with cached result."""
        # Simulate cached result
        from app.core.health_check_types import HealthCheckResult

        service._cache = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            components={},
        )
        service._cache_time = datetime.utcnow()

        summary = service.get_status_summary()

        assert summary["status"] == "healthy"
        assert "last_check" in summary

    def test_clear_cache(self, service):
        """Test clearing the cache."""
        # Set some cache
        service._cache = Mock()
        service._cache_time = datetime.utcnow()

        service.clear_cache()

        assert service._cache is None
        assert service._cache_time is None

    def test_get_history(self, service):
        """Test getting health check history."""
        # Add some history
        from app.core.health_check_types import HealthHistory

        service._history = [
            HealthHistory(
                timestamp=datetime.utcnow(),
                status=HealthStatus.HEALTHY,
                response_time_ms=100.0,
                component_count=5,
                unhealthy_count=0,
            ),
            HealthHistory(
                timestamp=datetime.utcnow(),
                status=HealthStatus.DEGRADED,
                response_time_ms=200.0,
                component_count=5,
                unhealthy_count=1,
            ),
        ]

        history = service.get_history(limit=2)

        assert len(history) == 2
        assert history[0].status == HealthStatus.HEALTHY
        assert history[1].status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_cache_functionality(self, service):
        """Test health check caching."""
        # Create a mock checker that counts calls
        call_count = 0

        async def mock_check():
            nonlocal call_count
            call_count += 1
            return ComponentHealth(
                component_name="test",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )

        mock_checker = Mock(spec=Mock)
        mock_checker.get_check_type.return_value = "test"
        mock_checker.is_critical.return_value = True
        mock_checker.should_run.return_value = True
        mock_checker.safe_check = mock_check

        service.checkers = [mock_checker]

        config = HealthCheckConfig(cache_ttl_seconds=60)

        # First call should execute
        await service.check_health(config)
        first_count = call_count

        # Second call should use cache
        await service.check_health(config)
        second_count = call_count

        assert first_count == 1
        assert second_count == 1  # Should not increase

    @pytest.mark.asyncio
    async def test_cache_expiration(self, service):
        """Test cache expiration."""
        call_count = 0

        async def mock_check():
            nonlocal call_count
            call_count += 1
            return ComponentHealth(
                component_name="test",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )

        mock_checker = Mock(spec=Mock)
        mock_checker.get_check_type.return_value = "test"
        mock_checker.is_critical.return_value = True
        mock_checker.should_run.return_value = True
        mock_checker.safe_check = mock_check

        service.checkers = [mock_checker]

        # First call with short TTL
        config = HealthCheckConfig(cache_ttl_seconds=0)
        await service.check_health(config)
        first_count = call_count

        # Second call should execute again (cache expired)
        await service.check_health(config)
        second_count = call_count

        assert first_count == 1
        assert second_count == 2  # Should increase (cache expired)

    @pytest.mark.asyncio
    async def test_history_limit(self, service):
        """Test history size limit."""
        from app.core.health_check_types import HealthHistory

        # Add more than max history size
        for i in range(150):
            service._add_to_history(
                HealthHistory(
                    timestamp=datetime.utcnow(),
                    status=HealthStatus.HEALTHY,
                    response_time_ms=100.0,
                    component_count=5,
                    unhealthy_count=0,
                )
            )

        # Should be limited to max_history_size
        assert len(service._history) == service._max_history_size

        # Should keep most recent entries
        history = service.get_history()
        assert len(history) == 10  # Default limit
