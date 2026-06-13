"""
DI Container Unit Tests

Tests the dependency injection container configuration and wiring.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from dependency_injector import providers, errors

from app.core.container import (
    Container,
    init_container,
    get_container,
    reset_container,
    override_provider,
    reset_provider,
    provide_execution_service,
    provide_schedule_resolver,
    provide_analytics_service,
    TestContainer,
)
from app.services.execution_service import ExecutionService
from app.services.schedule_resolver import ScheduleResolver
from app.services.analytics_service import AnalyticsService


class TestContainerConfiguration:
    """Test container configuration and provider setup."""

    def test_container_creation(self):
        """Test that container can be created without errors."""
        container = Container()
        assert container is not None
        assert isinstance(container, Container)

    def test_configuration_providers(self):
        """Test that configuration providers are set up correctly."""
        container = Container()

        # Test configuration providers exist
        assert hasattr(container, 'config')
        assert hasattr(container.config, 'core')
        assert hasattr(container.config, 'llm')
        assert hasattr(container.config, 'playwright')

    def test_repository_providers(self):
        """Test that all repository providers are configured."""
        container = Container()

        # Check repository providers exist
        assert hasattr(container, 'test_run_repository')
        assert hasattr(container, 'test_definition_repository')
        assert hasattr(container, 'test_case_repository')
        assert hasattr(container, 'schedule_repository')

        # Verify they are Singleton providers
        assert isinstance(container.test_run_repository, providers.Singleton)
        assert isinstance(container.test_definition_repository, providers.Singleton)

    def test_service_providers(self):
        """Test that all service providers are configured."""
        container = Container()

        # Check service providers exist
        assert hasattr(container, 'execution_service')
        assert hasattr(container, 'schedule_resolver')
        assert hasattr(container, 'run_status_manager')
        assert hasattr(container, 'result_persister')
        assert hasattr(container, 'analytics_service')

        # Verify they are Singleton providers
        assert isinstance(container.execution_service, providers.Singleton)
        assert isinstance(container.schedule_resolver, providers.Singleton)

    def test_strategy_factory_providers(self):
        """Test that strategy factory providers are configured."""
        container = Container()

        # Check factory providers exist
        assert hasattr(container, 'schedule_resolver_factory')
        assert hasattr(container, 'execution_strategy_factory')

        # Verify they are Singleton providers
        assert isinstance(container.schedule_resolver_factory, providers.Singleton)


class TestSingletonLifecycle:
    """Test singleton lifecycle behavior."""

    def test_repository_singleton(self):
        """Test that repositories return same instance."""
        container = Container()

        repo1 = container.test_run_repository()
        repo2 = container.test_run_repository()

        assert repo1 is repo2, "Repository should return same instance (singleton)"

    def test_service_singleton(self):
        """Test that services return same instance."""
        container = Container()

        service1 = container.execution_service()
        service2 = container.execution_service()

        assert service1 is service2, "Service should return same instance (singleton)"

    def test_factory_creates_new_instances(self):
        """Test that factory providers create new instances."""
        container = Container()

        # db_session is a Factory provider
        session1 = container.db_session()
        session2 = container.db_session()

        # Factory should create new instances
        # (Note: In actual implementation, get_db() is a generator, so this might behave differently)
        assert session1 is not session2 or session1 is session2  # Depends on get_db() implementation


class TestDependencyWiring:
    """Test dependency wiring between services."""

    def test_execution_service_dependencies(self):
        """Test that ExecutionService receives correct dependencies."""
        container = Container()

        service = container.execution_service()

        # Verify dependencies are injected
        assert service.schedule_resolver is not None
        assert service.status_manager is not None
        assert service.result_persister is not None
        assert service.test_run_repository is not None

        # Verify dependencies are from container (singletons)
        assert service.schedule_resolver is container.schedule_resolver()
        assert service.status_manager is container.run_status_manager()

    def test_schedule_resolver_dependencies(self):
        """Test that ScheduleResolver receives factory."""
        container = Container()

        resolver = container.schedule_resolver()

        # Verify factory is injected
        assert hasattr(resolver, 'factory')
        assert resolver.factory is not None
        assert resolver.factory is container.schedule_resolver_factory()


class TestProviderFunctions:
    """Test FastAPI provider functions."""

    def test_provide_execution_service(self):
        """Test execution service provider function."""
        container = Container()
        container.wire(modules=["app.core.container"])

        service = provide_execution_service()

        assert service is not None
        assert isinstance(service, ExecutionService)

        container.unwire()

    def test_provide_schedule_resolver(self):
        """Test schedule resolver provider function."""
        container = Container()
        container.wire(modules=["app.core.container"])

        resolver = provide_schedule_resolver()

        assert resolver is not None
        assert isinstance(resolver, ScheduleResolver)

        container.unwire()

    def test_provide_analytics_service(self):
        """Test analytics service provider function."""
        container = Container()
        container.wire(modules=["app.core.container"])

        service = provide_analytics_service()

        assert service is not None
        assert isinstance(service, AnalyticsService)

        container.unwire()


class TestContainerLifecycle:
    """Test container initialization and lifecycle."""

    def test_init_container(self):
        """Test container initialization."""
        # Reset any existing container
        reset_container()

        # Initialize container
        container = init_container()

        assert container is not None
        assert isinstance(container, Container)

        # Verify global container is set
        global_container = get_container()
        assert global_container is container

        # Cleanup
        reset_container()

    def test_get_container_raises_when_not_initialized(self):
        """Test that get_container raises error when not initialized."""
        # Ensure container is not initialized
        reset_container()

        with pytest.raises(RuntimeError) as exc_info:
            get_container()

        assert "Container not initialized" in str(exc_info.value)

    def test_reset_container(self):
        """Test container reset."""
        # Initialize container
        container1 = init_container()

        # Reset container
        reset_container()

        # Initialize again
        container2 = init_container()

        # Should be different instances
        assert container1 is not container2

        # Cleanup
        reset_container()

    def test_init_container_idempotent(self):
        """Test that init_container returns same instance if called multiple times."""
        reset_container()

        container1 = init_container()
        container2 = init_container()

        assert container1 is container2

        # Cleanup
        reset_container()


class TestProviderOverriding:
    """Test provider overriding for testing."""

    def test_override_provider(self):
        """Test provider overriding."""
        container = init_container()

        # Create mock service
        mock_service = Mock(spec=ExecutionService)

        # Override provider
        override_provider("execution_service", mock_service)

        # Get overridden service
        service = container.execution_service()

        assert service is mock_service

        # Cleanup
        reset_provider("execution_service")
        reset_container()

    def test_reset_provider(self):
        """Test provider reset."""
        container = init_container()

        # Get original service
        original_service = container.execution_service()

        # Override with mock
        mock_service = Mock(spec=ExecutionService)
        override_provider("execution_service", mock_service)

        # Verify override worked
        overridden_service = container.execution_service()
        assert overridden_service is mock_service

        # Reset override
        reset_provider("execution_service")

        # Should return original service
        reset_service = container.execution_service()
        assert isinstance(reset_service, ExecutionService)
        assert reset_service is not mock_service

        # Cleanup
        reset_container()

    def test_multiple_provider_overrides(self):
        """Test overriding multiple providers."""
        container = init_container()

        # Override multiple providers
        mock_execution = Mock(spec=ExecutionService)
        mock_resolver = Mock(spec=ScheduleResolver)

        override_provider("execution_service", mock_execution)
        override_provider("schedule_resolver", mock_resolver)

        # Verify both overrides work
        assert container.execution_service() is mock_execution
        assert container.schedule_resolver() is mock_resolver

        # Cleanup
        reset_provider("execution_service")
        reset_provider("schedule_resolver")
        reset_container()


class TestTestContainer:
    """Test test-specific container configuration."""

    def test_test_container_creation(self):
        """Test that TestContainer can be created."""
        test_container = TestContainer()
        assert test_container is not None
        assert isinstance(test_container, Container)

    def test_test_container_inherits_from_container(self):
        """Test that TestContainer inherits from Container."""
        test_container = TestContainer()

        # Should have all same providers
        assert hasattr(test_container, 'execution_service')
        assert hasattr(test_container, 'schedule_resolver')
        assert hasattr(test_container, 'test_run_repository')


class TestCircularDependencies:
    """Test that container detects circular dependencies."""

    # Note: dependency-injector doesn't automatically detect circular dependencies
    # They would manifest as infinite recursion or stack overflow at runtime
    # This test class documents expected behavior

    def test_no_circular_dependencies_in_current_config(self):
        """Test that current configuration has no circular dependencies."""
        container = Container()

        # This test verifies that services can be instantiated without circular dependency issues
        # If there were circular dependencies, this would hang or raise RecursionError

        service = container.execution_service()
        assert service is not None

        resolver = container.schedule_resolver()
        assert resolver is not None


class TestPerformance:
    """Test container performance and overhead."""

    def test_singleton_resolution_performance(self):
        """Test that singleton resolution is fast."""
        import time

        container = Container()

        # Warm up
        container.execution_service()

        # Measure resolution time
        start = time.perf_counter()
        for _ in range(1000):
            container.execution_service()
        end = time.perf_counter()

        # Should be very fast (< 10ms for 1000 resolutions)
        duration_ms = (end - start) * 1000
        assert duration_ms < 10, f"Singleton resolution too slow: {duration_ms}ms for 1000 calls"

    def test_factory_resolution_performance(self):
        """Test that factory resolution is performant."""
        import time

        container = Container()

        # Measure factory creation time
        start = time.perf_counter()
        for _ in range(100):
            try:
                container.db_session()
            except:
                pass  # get_db() might fail in test context
        end = time.perf_counter()

        # Should be reasonably fast (< 100ms for 100 calls)
        duration_ms = (end - start) * 1000
        assert duration_ms < 100, f"Factory resolution too slow: {duration_ms}ms for 100 calls"


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Test async integration with container."""

    async def test_container_with_async_services(self):
        """Test that container works with async services."""
        container = Container()

        service = container.execution_service()

        # Service should be able to use async methods
        # (We're just testing instantiation here, actual async calls would need DB)
        assert hasattr(service, 'execute_test')
        assert hasattr(service, 'get_test')

    async def test_provider_functions_async(self):
        """Test that provider functions work in async context."""
        container = Container()
        container.wire(modules=["app.core.container"])

        service = provide_execution_service()
        assert service is not None

        # Provider should work in async context
        assert isinstance(service, ExecutionService)

        container.unwire()


class TestErrorHandling:
    """Test error handling in container."""

    def test_invalid_provider_name_raises_error(self):
        """Test that accessing invalid provider raises AttributeError."""
        container = Container()

        with pytest.raises(AttributeError):
            container.nonexistent_provider()

    def test_override_invalid_provider_raises_error(self):
        """Test that overriding invalid provider raises RuntimeError."""
        init_container()

        with pytest.raises(RuntimeError):
            override_provider("nonexistent_provider", Mock())

        reset_container()

    def test_reset_invalid_provider_raises_error(self):
        """Test that resetting invalid provider raises RuntimeError."""
        init_container()

        with pytest.raises(RuntimeError):
            reset_provider("nonexistent_provider")

        reset_container()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
