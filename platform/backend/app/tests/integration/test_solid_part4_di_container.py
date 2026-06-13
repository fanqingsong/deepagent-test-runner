"""
SOLID Verification Part 4: Dependency Injection Container

Tests DI container follows Dependency Inversion Principle:
- High-level modules depend on abstractions
- Container provides concrete implementations
"""

import pytest

from app.core.container import Container, init_container, reset_container, get_container
from app.services.execution_service import ExecutionService
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository


class TestDIContainer:
    """Verify dependency injection container works correctly."""

    @pytest.mark.asyncio
    async def test_container_initialization(self):
        """Test container can be initialized and configured."""
        # Reset any existing container
        reset_container()

        # Initialize container
        container = init_container()

        assert container is not None
        assert isinstance(container, Container)

        # Verify we can get container instance
        same_container = get_container()
        assert same_container is container

    @pytest.mark.asyncio
    async def test_singleton_services(self):
        """Test services are singleton (same instance)."""
        container = init_container()

        # Get same service twice
        service1 = container.execution_service()
        service2 = container.execution_service()

        # Should be same instance (singleton)
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_all_registered_services(self):
        """Test all required services are registered."""
        container = init_container()

        # Verify core services are registered
        services_to_check = [
            'execution_service',
            'suite_service',
            'analytics_service',
            'schedule_resolver',
            'run_status_manager',
            'result_persister',
            'script_validation_service'
        ]

        for service_name in services_to_check:
            assert hasattr(container, service_name)
            service = getattr(container, service_name)
            assert service is not None
            # Call the provider to get instance
            instance = service()
            assert instance is not None

    @pytest.mark.asyncio
    async def test_repository_registration(self):
        """Test all repositories are registered in container."""
        container = init_container()

        repositories = [
            'test_run_repository',
            'test_definition_repository',
            'test_case_repository',
            'schedule_repository'
        ]

        for repo_name in repositories:
            assert hasattr(container, repo_name)
            repo_provider = getattr(container, repo_name)
            repo = repo_provider()
            assert repo is not None

    @pytest.mark.asyncio
    async def test_interface_based_dependencies(self):
        """Test container provides interface-based dependencies."""
        container = init_container()

        # Get repository via container
        test_run_repo = container.test_run_repository()

        # Should implement interface
        assert isinstance(test_run_repo, ITestRunRepository)

        test_def_repo = container.test_definition_repository()
        assert isinstance(test_def_repo, ITestDefinitionRepository)

    @pytest.mark.asyncio
    async def test_provider_functions(self):
        """Test FastAPI provider functions work."""
        from app.core.container import (
            provide_execution_service,
            provide_schedule_resolver,
            provide_analytics_service,
            provide_suite_service
        )

        container = init_container()

        # Test each provider function
        execution_service = provide_execution_service()
        assert execution_service is not None

        schedule_resolver = provide_schedule_resolver()
        assert schedule_resolver is not None

        analytics_service = provide_analytics_service()
        assert analytics_service is not None

        suite_service = provide_suite_service()
        assert suite_service is not None

    @pytest.mark.asyncio
    async def test_dependency_inversion_principle(self):
        """Test high-level modules depend on abstractions."""
        container = init_container()

        # Service should depend on repository interface
        service = container.execution_service()

        # Should use repository interface
        assert service.test_run_repository is not None
        assert isinstance(service.test_run_repository, ITestRunRepository)
