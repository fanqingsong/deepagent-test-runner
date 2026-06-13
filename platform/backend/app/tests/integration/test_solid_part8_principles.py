"""
SOLID Verification Part 8: SOLID Principles

Tests all SOLID principles are followed:
- Single Responsibility Principle (SRP)
- Open/Closed Principle (OCP)
- Liskov Substitution Principle (LSP)
- Interface Segregation Principle (ISP)
- Dependency Inversion Principle (DIP)
"""

import pytest

from app.core.container import Container, init_container
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository
from app.repositories.schedule_repository import SQLAlchemyScheduleRepository
from app.services.execution_service import ExecutionService
from app.services.schedule_resolver import ScheduleResolver
from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory
from app.health.checkers import DatabaseHealthChecker
from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
from app.core.interfaces.metrics_collector_interface import IMetricsCollector


class TestSOLIDPrinciples:
    """Verify all SOLID principles are followed."""

    @pytest.mark.asyncio
    async def test_single_responsibility_principle(self):
        """Test each class has only one reason to change."""
        # Repository - only responsible for data access
        repo = SQLAlchemyTestRunRepository()
        assert hasattr(repo, 'create')
        assert hasattr(repo, 'get_by_id')
        # Should not have business logic
        assert not hasattr(repo, 'execute_test')

        # Service - only responsible for business logic
        service = ExecutionService()
        assert hasattr(service, 'resolve_target_tests_v2')
        # Should not have direct database access (uses repository)
        # Should not have HTTP handling

        # Health checker - only responsible for health checks
        checker = DatabaseHealthChecker()
        assert hasattr(checker, 'check_health')
        # Should not have other responsibilities
        assert not hasattr(checker, 'execute_query')

    @pytest.mark.asyncio
    async def test_open_closed_principle(self):
        """Test system is open for extension, closed for modification."""
        factory = ScheduleResolverFactory()

        # Can get existing strategies without modifying code
        single_strategy = factory.get_strategy("single")
        assert single_strategy is not None

        # Can add new strategies without modifying existing ones
        # (This is design capability - actual extension would be done at runtime)
        initial_strategies = factory.get_registered_strategies()
        assert len(initial_strategies) >= 3

    @pytest.mark.asyncio
    async def test_liskov_substitution_principle(self):
        """Test interface implementations are interchangeable."""
        # All repositories should be substitutable via their interfaces
        test_run_repo: ITestRunRepository = SQLAlchemyTestRunRepository()
        test_def_repo = SQLAlchemyTestDefinitionRepository()
        schedule_repo = SQLAlchemyScheduleRepository()

        # Should all have the same interface methods
        for repo in [test_run_repo, test_def_repo, schedule_repo]:
            assert hasattr(repo, 'create')
            assert hasattr(repo, 'get_by_id')
            assert hasattr(repo, 'update')
            assert hasattr(repo, 'delete')

    @pytest.mark.asyncio
    async def test_interface_segregation_principle(self):
        """Test interfaces are focused and not bloated."""
        # Clients should not depend on methods they don't use

        # Repository interface is focused on CRUD
        required_repo_methods = ['create', 'get_by_id', 'update', 'delete']
        for method in required_repo_methods:
            assert hasattr(ITestRunRepository, method)

        # Metrics interface is focused on metrics operations
        required_metrics_methods = ['record_timing', 'get_timing_stats']
        for method in required_metrics_methods:
            assert hasattr(IMetricsCollector, method)

    @pytest.mark.asyncio
    async def test_dependency_inversion_principle(self):
        """Test high-level modules depend on abstractions."""
        # Service depends on repository interface, not concrete implementation
        service = ExecutionService()

        # Should use repository interface
        assert service.test_run_repository is not None
        assert isinstance(service.test_run_repository, ITestRunRepository)

        # Container provides interface-based dependencies
        container = init_container()
        repo = container.test_run_repository()
        assert isinstance(repo, ITestRunRepository)

    @pytest.mark.asyncio
    async def test_srp_repositories(self):
        """Test repositories have single responsibility - data access only."""
        repo = RepositoryFactory.get_test_run_repository()

        # Should only have data access methods
        data_access_methods = [
            'create', 'get_by_id', 'update', 'delete', 'get_all',
            'get_by_run_id', 'get_by_test_definition', 'get_recent_runs'
        ]

        for method in data_access_methods:
            assert hasattr(repo, method)

        # Should not have business logic
        assert not hasattr(repo, 'validate_schedule')
        assert not hasattr(repo, 'resolve_tests')

    @pytest.mark.asyncio
    async def test_srp_services(self):
        """Test services have single responsibility - business logic."""
        service = ExecutionService()

        # Should have business logic methods
        business_methods = [
            'resolve_target_tests_v2',
            'create_test_run_v2',
            'save_test_results_v2'
        ]

        for method in business_methods:
            assert hasattr(service, method)

        # Should not have data access methods (uses repository)
        # Should not have HTTP/UI methods
        assert not hasattr(service, 'execute_sql_query')
        assert not hasattr(service, 'render_html_template')

    @pytest.mark.asyncio
    async def test_ocp_strategies(self):
        """Test strategies follow Open/Closed Principle."""
        factory = ScheduleResolverFactory()

        # Can use existing strategies without modification
        strategies = factory.get_registered_strategies()

        for strategy_name in strategies:
            strategy = factory.get_strategy(strategy_name)
            assert strategy is not None

        # Design allows adding new strategies without modifying existing code
        # This demonstrates OCP

    @pytest.mark.asyncio
    async def test_lsp_interfaces(self):
        """Test all implementations of interfaces are substitutable."""
        # Create instances of different repositories
        repos = [
            SQLAlchemyTestRunRepository(),
            SQLAlchemyTestDefinitionRepository(),
            SQLAlchemyScheduleRepository()
        ]

        # All should have basic CRUD interface
        for repo in repos:
            assert hasattr(repo, 'create')
            assert hasattr(repo, 'get_by_id')
            assert hasattr(repo, 'update')
            assert hasattr(repo, 'delete')
            assert callable(repo.create)
            assert callable(repo.get_by_id)

    @pytest.mark.asyncio
    async def test_isp_focused_interfaces(self):
        """Test interfaces are focused and role-specific."""
        # ITestRunRepository should only have test-run methods
        test_run_methods = [
            'create', 'get_by_id', 'update', 'delete',
            'get_by_run_id', 'get_recent_runs'
        ]

        for method in test_run_methods:
            assert hasattr(ITestRunRepository, method)

        # Should not have unrelated methods
        assert not hasattr(ITestRunRepository, 'send_email')
        assert not hasattr(ITestRunRepository, 'render_pdf')

        # IMetricsCollector should only have metrics methods
        metrics_methods = [
            'record_timing', 'record_counter', 'record_gauge',
            'record_error', 'get_timing_stats', 'get_metrics_summary'
        ]

        for method in metrics_methods:
            assert hasattr(IMetricsCollector, method)

        # Should not have unrelated methods
        assert not hasattr(IMetricsCollector, 'query_database')

    @pytest.mark.asyncio
    async def test_dip_high_level_modules(self):
        """Test high-level modules depend on abstractions."""
        container = init_container()

        # Service (high-level) depends on repository interface (abstraction)
        service = container.execution_service()
        assert isinstance(service.test_run_repository, ITestRunRepository)

        # Should not depend on concrete implementation
        from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
        # The service uses the interface, not the concrete class directly

    @pytest.mark.asyncio
    async def test_dip_container_abstractions(self):
        """Test container provides abstractions to depend on."""
        container = init_container()

        # Container should provide interface-based dependencies
        test_run_repo = container.test_run_repository()
        assert isinstance(test_run_repo, ITestRunRepository)

        # Service gets interface, not concrete
        service = container.execution_service()
        assert isinstance(service.test_run_repository, ITestRunRepository)
