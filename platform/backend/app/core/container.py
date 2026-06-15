"""
Dependency Injection Container

Implements a comprehensive DI container using dependency-injector library.
Follows SOLID Dependency Inversion Principle for centralized dependency management.

Key Features:
- Singleton lifecycle for repositories and services
- Factory lifecycle for request-scoped objects
- Configuration binding from environment variables
- Provider overriding for testing
- FastAPI integration via @inject decorator
- Async support throughout
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import Depends
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from app.core.config import settings
from app.core.database import get_db, init_db, close_db
from app.core.redis_client import get_redis
from app.core.job_store import JobStore
from app.core.agent_config import get_llm
from app.core.llm_usage_callback import LlmUsageCallbackHandler

# Interface abstractions
from app.core.interfaces.llm_client_interface import ILLMClient
from app.core.interfaces.browser_automation_interface import IBrowserAutomation
from app.core.interfaces.metrics_collector_interface import IMetricsCollector

# Interface implementations
from app.core.llm.glm_client import GLMClient
from app.core.llm.mock_llm_client import MockLLMClient
from app.core.browser.playwright_automation import PlaywrightAutomation
from app.core.browser.mock_browser_automation import MockBrowserAutomation
from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector

# Repositories
from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.repositories.schedule_repository import SQLAlchemyScheduleRepository
from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository
from app.repositories.token_alert_repository import SQLAlchemyTokenAlertRepository
from app.repositories.suite_run_repository import SQLAlchemySuiteRunRepository
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository
from app.repositories.interfaces.token_budget_repository_interface import ITokenBudgetRepository
from app.repositories.interfaces.token_quota_repository_interface import ITokenQuotaRepository
from app.repositories.interfaces.token_alert_repository_interface import ITokenAlertRepository
from app.repositories.interfaces.suite_run_repository_interface import ISuiteRunRepository

# Services
from app.services.execution_service import ExecutionService
from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.services.script_validation_service import ScriptValidationService
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser
from app.services.analytics_service import AnalyticsService
from app.services.suite_service import SuiteService
from app.services.chat_session_service import ChatSessionService
from app.services.monitoring_service import MonitoringService
from app.services.permission_service import PermissionService
from app.services.suite_permission_service import SuitePermissionService
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.services.token_alert_service import TokenAlertService
from app.services.token_reporting_service import TokenReportingService
from app.services.causal_graphrag.neo4j_client import Neo4jClient
from app.services.causal_graphrag.root_cause_service import RootCauseService

# Service Interfaces (for Dependency Inversion Principle)
from app.services.interfaces.execution_service_interface import IExecutionService
from app.services.interfaces.analytics_service_interface import IAnalyticsService
from app.services.interfaces.script_validation_service_interface import IScriptValidationService
from app.services.interfaces.suite_service_interface import ISuiteService

# Strategy Factories
from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory

logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """
    Main Dependency Injection Container.

    Provides centralized dependency management with lifecycle control:
    - Singleton: One instance for application lifetime
    - Factory: New instance each time (useful for request-scoped objects)
    - Configuration: Environment-based configuration
    - Resource: Lifecycle-managed resources (DB, Redis, etc.)

    Usage:
        # In application setup
        container = Container()
        container.config.core.django.from_ini("settings.ini")
        container.wire(modules=["app.api", "app.services"])

        # In FastAPI routes
        @inject
        @app.get("/tests/{test_id}")
        async def get_test(
            test_id: str,
            execution_service: ExecutionService = Depends(Provide[Container.execution_service])
        ):
            return await execution_service.get_test(test_id)

        # In tests
        with container.execution_service.override(mock_execution_service):
            # Test with mock
            ...
    """

    # =============================================================================
    # Configuration
    # =============================================================================

    config = providers.Configuration()

    # Core configuration from settings - Commented out incorrect config attributes
    # config.core.database_url = providers.Object(settings.DATABASE_URL)
    # config.core.redis_url = providers.Object(settings.REDIS_URL)
    # config.core.secret_key = providers.Object(settings.SECRET_KEY)
    # config.core.debug = providers.Object(settings.DEBUG)
    # config.core.app_name = providers.Object(settings.APP_NAME)

    # LLM configuration - Commented out incorrect config attributes
    # config.llm.api_key = providers.Object(settings.LLM_API_KEY)
    # config.llm.base_url = providers.Object(settings.LLM_BASE_URL)
    # config.llm.model = providers.Object(settings.LLM_MODEL)
    # config.llm.timeout_ms = providers.Object(settings.API_TIMEOUT_MS)

    # Playwright configuration - Commented out incorrect config attributes
    # config.playwright.headless = providers.Object(settings.PLAYWRIGHT_HEADLESS)
    # config.playwright.test_timeout = providers.Object(settings.TEST_TIMEOUT)
    # config.playwright.screenshot_dir = providers.Object(settings.SCREENSHOT_DIR)

    # Interface implementation selection - Commented out incorrect config attributes
    # config.interfaces.use_mocks = providers.Object(False)  # Set to True for testing

    # =============================================================================
    # Resources (Lifecycle-managed)
    # =============================================================================

    # Database session provider (request-scoped)
    # Note: This is a factory that creates new sessions when called
    db_session = providers.Factory(
        lambda: next(get_db())
    )

    # Redis client provider (singleton)
    redis_client = providers.Singleton(
        lambda: get_redis()
    )

    # Job Store (singleton)
    job_store = providers.Singleton(
        JobStore,
        redis_client=redis_client
    )

    # =============================================================================
    # Interface Implementations (Singleton)
    # =============================================================================

    # LLM Client Implementation (based on config)
    @staticmethod
    def _create_llm_client(use_mocks: bool = False):
        """Factory function to create LLM client based on configuration."""
        if use_mocks:
            from app.core.llm.mock_llm_client import MockLLMClient
            return MockLLMClient()
        else:
            from app.core.llm.glm_client import GLMClient
            return GLMClient()

    llm_client_impl = providers.Factory(
        _create_llm_client,
        use_mocks=config.interfaces.use_mocks
    )

    # LLM Client Interface (singleton - shared across services)
    llm_client = providers.Singleton(
        lambda llm_impl: llm_impl,
        llm_impl=llm_client_impl
    )

    # Browser Automation Implementation (based on config)
    @staticmethod
    def _create_browser_automation(use_mocks: bool = False):
        """Factory function to create browser automation based on configuration."""
        if use_mocks:
            from app.core.browser.mock_browser_automation import MockBrowserAutomation
            return MockBrowserAutomation()
        else:
            from app.core.browser.playwright_automation import PlaywrightAutomation
            from app.core.interfaces.browser_automation_interface import BrowserConfig
            config = BrowserConfig(
                headless=settings.PLAYWRIGHT_HEADLESS,
                timeout=settings.TEST_TIMEOUT
            )
            return PlaywrightAutomation(config=config)

    browser_automation_impl = providers.Factory(
        _create_browser_automation,
        use_mocks=config.interfaces.use_mocks
    )

    # Browser Automation Interface (scoped per request)
    browser_automation = providers.Factory(
        lambda browser_impl: browser_impl,
        browser_impl=browser_automation_impl
    )

    # =============================================================================
    # Metrics (Singleton)
    # =============================================================================

    # Metrics Collector (in-memory implementation)
    metrics_collector = providers.Singleton(
        InMemoryMetricsCollector
    )

    # =============================================================================
    # Legacy LLM Components (Singleton)
    # =============================================================================

    # Legacy LangChain LLM client (for backward compatibility)
    llm_langchain = providers.Singleton(
        get_llm
    )

    # LLM usage callback (singleton for tracking)
    llm_usage_callback = providers.Singleton(
        LlmUsageCallbackHandler
    )

    # =============================================================================
    # Repositories (Singleton)
    # =============================================================================

    # Test Run Repository
    test_run_repository = providers.Singleton(
        SQLAlchemyTestRunRepository
    )

    # Test Definition Repository
    test_definition_repository = providers.Singleton(
        SQLAlchemyTestDefinitionRepository
    )

    # Test Case Repository
    test_case_repository = providers.Singleton(
        TestCaseRepository
    )

    # Schedule Repository
    schedule_repository = providers.Singleton(
        SQLAlchemyScheduleRepository
    )

    # Token Budget Repository
    token_budget_repository = providers.Singleton(
        SQLAlchemyTokenBudgetRepository
    )

    # Token Quota Repository
    token_quota_repository = providers.Singleton(
        SQLAlchemyTokenQuotaRepository
    )

    # Token Alert Repository
    token_alert_repository = providers.Singleton(
        SQLAlchemyTokenAlertRepository
    )

    # Suite Run Repository
    suite_run_repository = providers.Singleton(
        SQLAlchemySuiteRunRepository
    )

    # =============================================================================
    # Strategy Factories (Singleton)
    # =============================================================================

    # Schedule Resolver Factory (with strategies auto-registered)
    schedule_resolver_factory = providers.Singleton(
        ScheduleResolverFactory
    )

    # =============================================================================
    # Core Services (Singleton)
    # =============================================================================

    # Schedule Resolver (uses factory for strategy pattern)
    schedule_resolver = providers.Singleton(
        ScheduleResolver,
        factory=schedule_resolver_factory
    )

    # Run Status Manager
    run_status_manager = providers.Singleton(
        RunStatusManager,
        test_run_repository=test_run_repository
    )

    # Result Persister
    result_persister = providers.Singleton(
        ResultPersister,
        test_run_repository=test_run_repository,
        test_case_repository=test_case_repository,
        test_definition_repository=test_definition_repository
    )

    # Prompt Builder (LLM service)
    prompt_builder = providers.Singleton(
        PromptBuilder
    )

    # Response Parser (LLM service)
    response_parser = providers.Singleton(
        ResponseParser
    )

    # Script Validation Service
    script_validation_service = providers.Singleton(
        ScriptValidationService
    )

    # =============================================================================
    # High-Level Services (Singleton)
    # =============================================================================

    # Execution Service (orchestrates test execution)
    execution_service = providers.Singleton(
        ExecutionService,
        schedule_resolver=schedule_resolver,
        status_manager=run_status_manager,
        result_persister=result_persister,
        test_run_repository=test_run_repository
    )

    # Analytics Service (singleton without db - db passed per method call)
    analytics_service = providers.Singleton(
        AnalyticsService
    )

    # Suite Service (singleton with repository dependency - db passed per method call)
    suite_service = providers.Singleton(
        SuiteService,
        suite_run_repository=suite_run_repository
    )

    # Chat Session Service
    chat_session_service = providers.Singleton(
        ChatSessionService
    )

    # Monitoring Service
    monitoring_service = providers.Singleton(
        MonitoringService
    )

    # Permission Service
    permission_service = providers.Singleton(
        PermissionService
    )

    # Suite Permission Service
    suite_permission_service = providers.Singleton(
        SuitePermissionService
    )

    # =============================================================================
    # Token Management Services (Singleton)
    # =============================================================================

    # Token Budget Service
    token_budget_service = providers.Singleton(
        TokenBudgetService,
        budget_repository=token_budget_repository,
        metrics_collector=metrics_collector
    )

    # Token Quota Service
    token_quota_service = providers.Singleton(
        TokenQuotaService,
        quota_repository=token_quota_repository,
        metrics_collector=metrics_collector
    )

    # Token Alert Service
    token_alert_service = providers.Singleton(
        TokenAlertService,
        alert_repository=token_alert_repository,
        metrics_collector=metrics_collector
    )

    # Token Reporting Service
    token_reporting_service = providers.Singleton(
        TokenReportingService,
        metrics_collector=metrics_collector
    )

    # =============================================================================
    # Causal GraphRAG (Root Cause Analysis) Services (Singleton)
    # =============================================================================

    # Neo4j client (lazy connection)
    neo4j_client = providers.Singleton(
        Neo4jClient
    )

    # Root Cause Service (GraphRAG + causal inference + LLM summarization)
    root_cause_service = providers.Singleton(
        RootCauseService,
        neo4j_client=neo4j_client,
        llm_client=llm_client
    )


# =============================================================================
# Global Container Instance
# =============================================================================

# Global container instance (initialized in application startup)
container: Optional[Container] = None


def init_container() -> Container:
    """
    Initialize and configure the DI container.

    This should be called once during application startup.
    Sets up configuration and wires the container with application modules.

    Returns:
        Container: Initialized container instance

    Example:
        >>> from app.core.container import init_container
        >>> container = init_container()
        >>> # Container is now ready for dependency injection
    """
    global container

    if container is not None:
        logger.warning("Container already initialized, returning existing instance")
        return container

    logger.info("Initializing DI Container")

    # Create container instance
    container = Container()

    # Wire container with application modules
    # This enables @inject decorator to work in these modules
    # Wire container so @inject on provide_* functions resolves dependencies.
    container.wire(modules=["app.core.container"])

    logger.info("DI Container initialized and wired successfully")
    return container


def get_container() -> Container:
    """
    Get the current container instance.

    Returns:
        Container: Current container instance

    Raises:
        RuntimeError: If container has not been initialized

    Example:
        >>> from app.core.container import get_container
        >>> container = get_container()
        >>> service = container.execution_service()
    """
    global container

    if container is None:
        raise RuntimeError(
            "Container not initialized. Call init_container() during application startup."
        )

    return container


def reset_container() -> None:
    """
    Reset the container instance.

    Primarily useful for testing to ensure clean state between tests.

    Example:
        >>> from app.core.container import reset_container
        >>> reset_container()
        >>> # Now init_container() will create a fresh instance
    """
    global container

    if container is not None:
        container.unwire()
        container = None

    logger.debug("Container reset")


# =============================================================================
# Convenience Provider Functions for FastAPI
# =============================================================================

@inject
def provide_execution_service(
    service: ExecutionService = Depends(Provide[Container.execution_service])
) -> ExecutionService:
    """
    FastAPI provider for ExecutionService.

    Usage in FastAPI routes:
        @app.get("/tests/{test_id}")
        async def get_test(
            test_id: str,
            service: ExecutionService = Depends(provide_execution_service)
        ):
            return await service.get_test(test_id)

    Args:
        service: Injected ExecutionService instance

    Returns:
        ExecutionService: Service instance
    """
    return service


@inject
def provide_schedule_resolver(
    resolver: ScheduleResolver = Depends(Provide[Container.schedule_resolver])
) -> ScheduleResolver:
    """FastAPI provider for ScheduleResolver."""
    return resolver


@inject
def provide_run_status_manager(
    manager: RunStatusManager = Depends(Provide[Container.run_status_manager])
) -> RunStatusManager:
    """FastAPI provider for RunStatusManager."""
    return manager


@inject
def provide_result_persister(
    persister: ResultPersister = Depends(Provide[Container.result_persister])
) -> ResultPersister:
    """FastAPI provider for ResultPersister."""
    return persister


@inject
def provide_analytics_service(
    service: AnalyticsService = Depends(Provide[Container.analytics_service])
) -> AnalyticsService:
    """FastAPI provider for AnalyticsService."""
    return service


@inject
def provide_suite_service(
    service: SuiteService = Depends(Provide[Container.suite_service])
) -> SuiteService:
    """FastAPI provider for SuiteService."""
    return service


@inject
def provide_test_run_repository(
    repo: ITestRunRepository = Depends(Provide[Container.test_run_repository])
) -> ITestRunRepository:
    """FastAPI provider for TestRun Repository."""
    return repo


@inject
def provide_test_definition_repository(
    repo: ITestDefinitionRepository = Depends(Provide[Container.test_definition_repository])
) -> ITestDefinitionRepository:
    """FastAPI provider for TestDefinition Repository."""
    return repo


@inject
def provide_schedule_repository(
    repo: IScheduleRepository = Depends(Provide[Container.schedule_repository])
) -> IScheduleRepository:
    """FastAPI provider for Schedule Repository."""
    return repo


@inject
def provide_llm_client(
    llm = Depends(Provide[Container.llm_client])
):
    """FastAPI provider for LLM client."""
    return llm


@inject
def provide_prompt_builder(
    builder: PromptBuilder = Depends(Provide[Container.prompt_builder])
) -> PromptBuilder:
    """FastAPI provider for PromptBuilder."""
    return builder


@inject
def provide_response_parser(
    parser: ResponseParser = Depends(Provide[Container.response_parser])
) -> ResponseParser:
    """FastAPI provider for ResponseParser."""
    return parser


@inject
def provide_script_validation_service(
    service: ScriptValidationService = Depends(Provide[Container.script_validation_service])
) -> ScriptValidationService:
    """FastAPI provider for ScriptValidationService."""
    return service


@inject
def provide_metrics_collector(
    collector: IMetricsCollector = Depends(Provide[Container.metrics_collector])
) -> IMetricsCollector:
    """FastAPI provider for Metrics Collector."""
    return collector


@inject
def provide_token_budget_service(
    service: TokenBudgetService = Depends(Provide[Container.token_budget_service])
) -> TokenBudgetService:
    """FastAPI provider for Token Budget Service."""
    return service


@inject
def provide_token_quota_service(
    service: TokenQuotaService = Depends(Provide[Container.token_quota_service])
) -> TokenQuotaService:
    """FastAPI provider for Token Quota Service."""
    return service


@inject
def provide_token_alert_service(
    service: TokenAlertService = Depends(Provide[Container.token_alert_service])
) -> TokenAlertService:
    """FastAPI provider for Token Alert Service."""
    return service


@inject
def provide_token_reporting_service(
    service: TokenReportingService = Depends(Provide[Container.token_reporting_service])
) -> TokenReportingService:
    """FastAPI provider for Token Reporting Service."""
    return service


@inject
def provide_root_cause_service(
    service: RootCauseService = Depends(Provide[Container.root_cause_service])
) -> RootCauseService:
    """FastAPI provider for the Causal GraphRAG Root Cause Service."""
    return service


# =============================================================================
# Provider Aliases for Common Use Cases
# =============================================================================

# Type aliases for cleaner dependency declarations
DependsExecutionService = Depends(provide_execution_service)
DependsScheduleResolver = Depends(provide_schedule_resolver)
DependsAnalyticsService = Depends(provide_analytics_service)
DependsSuiteService = Depends(provide_suite_service)
DependsTestRunRepository = Depends(provide_test_run_repository)
DependsTestDefinitionRepository = Depends(provide_test_definition_repository)
DependsScheduleRepository = Depends(provide_schedule_repository)
DependsMetricsCollector = Depends(provide_metrics_collector)

# Token Management Service Aliases
DependsTokenBudgetService = Depends(provide_token_budget_service)
DependsTokenQuotaService = Depends(provide_token_quota_service)
DependsTokenAlertService = Depends(provide_token_alert_service)
DependsTokenReportingService = Depends(provide_token_reporting_service)


# =============================================================================
# Testing Utilities
# =============================================================================

class TestContainer(Container):
    """
    Test-specific container configuration.

    Overrides providers with mock implementations for testing.
    Used in test suites to isolate dependencies.

    Example:
        >>> from app.core.container import TestContainer
        >>> test_container = TestContainer()
        >>> test_container.wire(modules=["app.api.v1.endpoints.tests"])
        >>> # Run tests with mocked dependencies
    """


def override_provider(provider_name: str, mock_instance):
    """
    Override a provider with a mock instance for testing.

    Args:
        provider_name: Name of the provider to override
        mock_instance: Mock instance to use instead

    Example:
        >>> from unittest.mock import Mock
        >>> from app.core.container import get_container, override_provider
        >>> mock_service = Mock()
        >>> override_provider("execution_service", mock_service)
        >>> # Now execution_service will use the mock
    """
    global container

    if container is None:
        raise RuntimeError("Container not initialized")

    provider = getattr(container, provider_name)
    provider.override(providers.Object(mock_instance))

    logger.debug(f"Overridden provider: {provider_name}")


def reset_provider(provider_name: str):
    """
    Reset a provider override.

    Args:
        provider_name: Name of the provider to reset

    Example:
        >>> from app.core.container import get_container, reset_provider
        >>> reset_provider("execution_service")
        >>> # Provider now uses original implementation
    """
    global container

    if container is None:
        raise RuntimeError("Container not initialized")

    provider = getattr(container, provider_name)
    provider.reset_override()

    logger.debug(f"Reset provider override: {provider_name}")


# =============================================================================
# Lifecycle Management
# =============================================================================

async def startup_container() -> None:
    """
    Initialize container resources during application startup.

    This should be called in FastAPI lifespan context manager.

    Example:
        >>> @asynccontextmanager
        ... async def lifespan(app: FastAPI):
        ...     await startup_container()
        ...     yield
        ...     await shutdown_container()
    """
    logger.info("Starting up container resources")

    # Initialize database
    await init_db()

    # Initialize container
    init_container()

    logger.info("Container startup complete")


async def shutdown_container() -> None:
    """
    Cleanup container resources during application shutdown.

    This should be called in FastAPI lifespan context manager.

    Example:
        >>> @asynccontextmanager
        ... async def lifespan(app: FastAPI):
        ...     await startup_container()
        ...     yield
        ...     await shutdown_container()
    """
    global container

    logger.info("Shutting down container resources")

    # Close database
    await close_db()

    # Unwire container
    if container is not None:
        container.unwire()
        container = None

    logger.info("Container shutdown complete")
