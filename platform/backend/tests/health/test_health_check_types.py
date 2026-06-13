"""
Tests for Health Check Types

Tests the data models and types used in the health check system.
"""

import pytest
from datetime import datetime
from app.core.health_check_types import (
    HealthStatus,
    ComponentHealth,
    HealthCheckResult,
    SystemHealth,
    HealthCheckConfig,
    HealthHistory,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestComponentHealth:
    """Test ComponentHealth model."""

    def test_component_health_creation(self):
        """Test creating ComponentHealth."""
        component = ComponentHealth(
            component_name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.5,
            details="Test component",
            is_critical=True,
        )

        assert component.component_name == "test"
        assert component.status == HealthStatus.HEALTHY
        assert component.response_time_ms == 100.5
        assert component.details == "Test component"
        assert component.is_critical is True
        assert isinstance(component.checked_at, datetime)

    def test_component_health_defaults(self):
        """Test ComponentHealth default values."""
        component = ComponentHealth(
            component_name="test",
            status=HealthStatus.HEALTHY,
            details="Test",
        )

        assert component.response_time_ms is None
        assert component.metadata == {}
        assert component.is_critical is False
        assert isinstance(component.checked_at, datetime)


class TestHealthCheckResult:
    """Test HealthCheckResult model."""

    def test_health_check_result_creation(self):
        """Test creating HealthCheckResult."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            components={},
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.components == {}
        assert result.total_components == 0
        assert result.healthy_components == 0
        assert result.degraded_components == 0
        assert result.unhealthy_components == 0
        assert isinstance(result.timestamp, datetime)


class TestSystemHealth:
    """Test SystemHealth model."""

    def test_add_component(self):
        """Test adding component to SystemHealth."""
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            components={},
        )

        component1 = ComponentHealth(
            component_name="test1",
            status=HealthStatus.HEALTHY,
            details="Test 1",
            is_critical=True,
        )

        system_health.add_component(component1)

        assert system_health.total_components == 1
        assert system_health.healthy_components == 1
        assert system_health.degraded_components == 0
        assert system_health.unhealthy_components == 0
        assert "test1" in system_health.components

    def test_add_multiple_components(self):
        """Test adding multiple components."""
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            components={},
        )

        system_health.add_component(
            ComponentHealth(
                component_name="healthy",
                status=HealthStatus.HEALTHY,
                details="Healthy",
                is_critical=True,
            )
        )

        system_health.add_component(
            ComponentHealth(
                component_name="degraded",
                status=HealthStatus.DEGRADED,
                details="Degraded",
                is_critical=False,
            )
        )

        system_health.add_component(
            ComponentHealth(
                component_name="unhealthy",
                status=HealthStatus.UNHEALTHY,
                details="Unhealthy",
                is_critical=False,
            )
        )

        assert system_health.total_components == 3
        assert system_health.healthy_components == 1
        assert system_health.degraded_components == 1
        assert system_health.unhealthy_components == 1

    def test_calculate_overall_status_healthy(self):
        """Test overall status calculation when all healthy."""
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            components={},
        )

        system_health.add_component(
            ComponentHealth(
                component_name="db",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )
        )

        system_health.add_component(
            ComponentHealth(
                component_name="redis",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )
        )

        status = system_health.calculate_overall_status()

        assert status == HealthStatus.HEALTHY
        assert system_health.details == "All components healthy"

    def test_calculate_overall_status_critical_unhealthy(self):
        """Test overall status when critical component is unhealthy."""
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            components={},
        )

        system_health.add_component(
            ComponentHealth(
                component_name="db",
                status=HealthStatus.UNHEALTHY,
                details="Failed",
                is_critical=True,
            )
        )

        system_health.add_component(
            ComponentHealth(
                component_name="redis",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )
        )

        status = system_health.calculate_overall_status()

        assert status == HealthStatus.UNHEALTHY
        assert "Critical component db is unhealthy" in system_health.details

    def test_calculate_overall_status_non_critical_unhealthy(self):
        """Test overall status when non-critical component is unhealthy."""
        system_health = SystemHealth(
            status=HealthStatus.UNKNOWN,
            components={},
        )

        system_health.add_component(
            ComponentHealth(
                component_name="db",
                status=HealthStatus.HEALTHY,
                details="OK",
                is_critical=True,
            )
        )

        system_health.add_component(
            ComponentHealth(
                component_name="llm",
                status=HealthStatus.UNHEALTHY,
                details="Failed",
                is_critical=False,
            )
        )

        status = system_health.calculate_overall_status()

        assert status == HealthStatus.DEGRADED
        assert "1 component(s) unhealthy" in system_health.details


class TestHealthCheckConfig:
    """Test HealthCheckConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.timeout_seconds == 5.0
        assert config.parallel_execution is True
        assert config.cache_ttl_seconds == 60
        assert config.include_non_critical is True
        assert config.critical_only is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(
            timeout_seconds=10.0,
            parallel_execution=False,
            cache_ttl_seconds=120,
            include_non_critical=False,
            critical_only=True,
        )

        assert config.timeout_seconds == 10.0
        assert config.parallel_execution is False
        assert config.cache_ttl_seconds == 120
        assert config.include_non_critical is False
        assert config.critical_only is True


class TestHealthHistory:
    """Test HealthHistory model."""

    def test_health_history_creation(self):
        """Test creating HealthHistory."""
        history = HealthHistory(
            timestamp=datetime.utcnow(),
            status=HealthStatus.HEALTHY,
            response_time_ms=150.5,
            component_count=5,
            unhealthy_count=0,
        )

        assert history.status == HealthStatus.HEALTHY
        assert history.response_time_ms == 150.5
        assert history.component_count == 5
        assert history.unhealthy_count == 0
        assert isinstance(history.timestamp, datetime)
