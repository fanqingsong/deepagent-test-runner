"""
Test Token Management Container Integration

Tests to verify that token management services are properly integrated
into the DI container and can be resolved correctly.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.core.container import Container, init_container, reset_container, get_container


class TestTokenContainerIntegration:
    """Test token management service container integration."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_container_has_token_budget_repository(self):
        """Test that container has token budget repository registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_budget_repository')

        # Create instance
        repo = container.token_budget_repository()
        assert repo is not None
        assert repo.__class__.__name__ == 'SQLAlchemyTokenBudgetRepository'

    def test_container_has_token_quota_repository(self):
        """Test that container has token quota repository registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_quota_repository')

        # Create instance
        repo = container.token_quota_repository()
        assert repo is not None
        assert repo.__class__.__name__ == 'SQLAlchemyTokenQuotaRepository'

    def test_container_has_token_alert_repository(self):
        """Test that container has token alert repository registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_alert_repository')

        # Create instance
        repo = container.token_alert_repository()
        assert repo is not None
        assert repo.__class__.__name__ == 'SQLAlchemyTokenAlertRepository'

    def test_container_has_token_budget_service(self):
        """Test that container has token budget service registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_budget_service')

        # Create instance
        service = container.token_budget_service()
        assert service is not None
        assert service.__class__.__name__ == 'TokenBudgetService'

        # Verify dependencies injected
        assert service.budget_repository is not None
        assert service.metrics_collector is not None

    def test_container_has_token_quota_service(self):
        """Test that container has token quota service registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_quota_service')

        # Create instance
        service = container.token_quota_service()
        assert service is not None
        assert service.__class__.__name__ == 'TokenQuotaService'

        # Verify dependencies injected
        assert service.quota_repository is not None
        assert service.metrics_collector is not None

    def test_container_has_token_alert_service(self):
        """Test that container has token alert service registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_alert_service')

        # Create instance
        service = container.token_alert_service()
        assert service is not None
        assert service.__class__.__name__ == 'TokenAlertService'

        # Verify dependencies injected
        assert service.alert_repository is not None
        assert service.metrics_collector is not None

    def test_container_has_token_reporting_service(self):
        """Test that container has token reporting service registered."""
        container = Container()

        # Verify provider exists
        assert hasattr(container, 'token_reporting_service')

        # Create instance
        service = container.token_reporting_service()
        assert service is not None
        assert service.__class__.__name__ == 'TokenReportingService'

        # Verify dependencies injected
        assert service.metrics_collector is not None

    def test_token_services_are_singletons(self):
        """Test that token services are singleton instances."""
        container = Container()

        # Create multiple instances
        service1 = container.token_budget_service()
        service2 = container.token_budget_service()

        # Should be same instance (singleton)
        assert service1 is service2

    def test_token_repositories_are_singletons(self):
        """Test that token repositories are singleton instances."""
        container = Container()

        # Create multiple instances
        repo1 = container.token_budget_repository()
        repo2 = container.token_budget_repository()

        # Should be same instance (singleton)
        assert repo1 is repo2

    def test_provider_functions_exist(self):
        """Test that provider functions exist for token services."""
        from app.core.container import (
            provide_token_budget_service,
            provide_token_quota_service,
            provide_token_alert_service,
            provide_token_reporting_service
        )

        # Verify functions are callable
        assert callable(provide_token_budget_service)
        assert callable(provide_token_quota_service)
        assert callable(provide_token_alert_service)
        assert callable(provide_token_reporting_service)

    def test_provider_aliases_exist(self):
        """Test that provider aliases exist for token services."""
        from app.core.container import (
            DependsTokenBudgetService,
            DependsTokenQuotaService,
            DependsTokenAlertService,
            DependsTokenReportingService
        )

        # Verify aliases exist (they are Depends objects)
        assert DependsTokenBudgetService is not None
        assert DependsTokenQuotaService is not None
        assert DependsTokenAlertService is not None
        assert DependsTokenReportingService is not None

    def test_container_initialization(self):
        """Test that container initializes without errors."""
        container = init_container()

        # Verify token services are accessible
        assert container.token_budget_service() is not None
        assert container.token_quota_service() is not None
        assert container.token_alert_service() is not None
        assert container.token_reporting_service() is not None

    def test_service_dependencies_injected(self):
        """Test that service dependencies are properly injected."""
        container = Container()

        # Get budget service
        budget_service = container.token_budget_service()

        # Verify it has the right repository
        assert budget_service.budget_repository.__class__.__name__ == 'SQLAlchemyTokenBudgetRepository'

        # Verify it has metrics collector
        assert budget_service.metrics_collector is not None

    def test_repository_factory_has_token_repositories(self):
        """Test that RepositoryFactory has token repository methods."""
        from app.repositories.repository_factory import RepositoryFactory

        # Verify methods exist
        assert hasattr(RepositoryFactory, 'get_token_budget_repository')
        assert hasattr(RepositoryFactory, 'get_token_quota_repository')
        assert hasattr(RepositoryFactory, 'get_token_alert_repository')

        # Verify setter methods exist
        assert hasattr(RepositoryFactory, 'set_token_budget_repository')
        assert hasattr(RepositoryFactory, 'set_token_quota_repository')
        assert hasattr(RepositoryFactory, 'set_token_alert_repository')

    def test_container_wiring_modules(self):
        """Test that container can be wired with token modules."""
        container = Container()

        # Should not raise errors
        container.wire(
            modules=[
                "app.services.token_budget_service",
                "app.services.token_quota_service",
                "app.services.token_alert_service",
                "app.services.token_reporting_service"
            ]
        )

        # Clean up
        container.unwire()


class TestTokenServiceOverrides:
    """Test token service overrides for testing."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_override_token_budget_service(self):
        """Test overriding token budget service."""
        from app.core.container import get_container, override_provider, reset_provider

        # Initialize container
        container = init_container()

        # Create mock service
        mock_service = Mock()
        mock_service.budget_repository = Mock()
        mock_service.metrics_collector = Mock()

        # Override provider
        override_provider('token_budget_service', mock_service)

        # Get service and verify it's the mock
        service = container.token_budget_service()
        assert service is mock_service

        # Reset
        reset_provider('token_budget_service')

    def test_override_token_quota_service(self):
        """Test overriding token quota service."""
        from app.core.container import get_container, override_provider, reset_provider

        # Initialize container
        container = init_container()

        # Create mock service
        mock_service = Mock()
        mock_service.quota_repository = Mock()
        mock_service.metrics_collector = Mock()

        # Override provider
        override_provider('token_quota_service', mock_service)

        # Get service and verify it's the mock
        service = container.token_quota_service()
        assert service is mock_service

        # Reset
        reset_provider('token_quota_service')

    def test_repository_factory_reset_includes_token_repos(self):
        """Test that RepositoryFactory.reset() includes token repositories."""
        from app.repositories.repository_factory import RepositoryFactory

        # Get repositories to create instances
        repo1 = RepositoryFactory.get_token_budget_repository()
        repo2 = RepositoryFactory.get_token_quota_repository()
        repo3 = RepositoryFactory.get_token_alert_repository()

        # Verify instances exist
        assert repo1 is not None
        assert repo2 is not None
        assert repo3 is not None

        # Reset factory
        RepositoryFactory.reset()

        # Get new instances (should be new objects)
        new_repo1 = RepositoryFactory.get_token_budget_repository()
        new_repo2 = RepositoryFactory.get_token_quota_repository()
        new_repo3 = RepositoryFactory.get_token_alert_repository()

        # Should be different instances
        assert new_repo1 is not repo1
        assert new_repo2 is not repo2
        assert new_repo3 is not repo3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
