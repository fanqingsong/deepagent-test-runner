# Dependency Injection Container - Complete Guide

## Overview

This application uses `dependency-injector` library to implement a comprehensive Dependency Injection (DI) container following SOLID principles. The DI container manages service lifecycles, wires dependencies automatically, and provides a centralized configuration for all application services.

## Why Dependency Injection?

### Benefits

1. **Centralized Configuration**: All dependencies defined in one place (`app/core/container.py`)
2. **Automatic Wiring**: Dependencies automatically injected via `@inject` decorator
3. **Lifetime Management**: Proper singleton/scoped/transient lifetimes
4. **Testability**: Easy to swap implementations for tests
5. **Maintainability**: Clear dependency graph and explicit dependencies
6. **Type Safety**: Full type hints for IDE support
7. **Configuration**: Environment-based configuration binding

### DI Framework Choice: `dependency-injector`

We chose `dependency-injector` over alternatives because:

- **Mature & Production-Ready**: Well-tested and widely used
- **FastAPI Integration**: Built-in FastAPI support via `@inject` decorator
- **Async Support**: Full support for async injections
- **Performance**: Written in Cython for minimal overhead
- **Features**: Singleton, Factory, Configuration, Resources, and provider overriding
- **Documentation**: Comprehensive documentation and examples

## Architecture

### Container Structure

```
Container (app/core/container.py)
├── Configuration (environment-based)
│   ├── core.* (database, redis, security)
│   ├── llm.* (LLM client settings)
│   └── playwright.* (browser automation settings)
│
├── Resources (lifecycle-managed)
│   ├── db_session (factory for database sessions)
│   ├── redis_client (singleton Redis connection)
│   └── job_store (singleton job metadata store)
│
├── LLM Components (singleton)
│   ├── llm_client (GLM LLM client)
│   └── llm_usage_callback (token usage tracking)
│
├── Repositories (singleton)
│   ├── test_run_repository
│   ├── test_definition_repository
│   ├── test_case_repository
│   └── schedule_repository
│
├── Strategy Factories (singleton)
│   ├── schedule_resolver_factory
│   └── execution_strategy_factory
│
└── Services (singleton)
    ├── schedule_resolver
    ├── run_status_manager
    ├── result_persister
    ├── execution_service
    ├── analytics_service
    ├── suite_service
    └── ... (other services)
```

### Lifecycle Types

1. **Singleton**: One instance for application lifetime
   - Used for: Repositories, Services, Factories
   - Provider: `providers.Singleton`

2. **Factory**: New instance each time
   - Used for: Database sessions (request-scoped)
   - Provider: `providers.Factory`

3. **Configuration**: Environment-based settings
   - Used for: Settings from environment variables
   - Provider: `providers.Configuration`

## Usage Guide

### 1. Application Startup

The container is initialized during application startup in `main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.container import startup_container, shutdown_container

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_container()  # Initializes container and DB
    yield
    # Shutdown
    await shutdown_container()  # Cleanup resources

app = FastAPI(lifespan=lifespan)
```

### 2. Using Dependencies in FastAPI Routes

#### Method 1: Using Provider Functions (Recommended)

```python
from fastapi import APIRouter, Depends
from app.core.container import provide_execution_service
from app.services.execution_service import ExecutionService

router = APIRouter()

@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(provide_execution_service)
):
    return await service.get_test(test_id)
```

#### Method 2: Using @inject Decorator

```python
from fastapi import APIRouter
from app.core.container import inject, Provide, Container
from app.services.execution_service import ExecutionService

router = APIRouter()

@inject
@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(Provide[Container.execution_service])
):
    return await service.get_test(test_id)
```

#### Method 3: Using Pre-defined Aliases (Cleanest)

```python
from fastapi import APIRouter
from app.core.container import DependsExecutionService
from app.services.execution_service import ExecutionService

router = APIRouter()

@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = DependsExecutionService
):
    return await service.get_test(test_id)
```

### 3. Using Dependencies in Services

Services receive dependencies via constructor injection:

```python
from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class ExecutionService:
    def __init__(
        self,
        schedule_resolver: ScheduleResolver,
        status_manager: RunStatusManager,
        result_persister: ResultPersister,
        test_run_repository: ITestRunRepository
    ):
        self.schedule_resolver = schedule_resolver
        self.status_manager = status_manager
        self.result_persister = result_persister
        self.test_run_repository = test_run_repository
```

The container automatically wires these dependencies.

### 4. Using Dependencies in Temporal Activities

```python
from app.core.container import get_container
from app.services.execution_service import ExecutionService

async def prepare_test(test_id: str) -> Dict:
    """Prepare test for execution."""
    container = get_container()
    execution_service = container.execution_service()

    test = await execution_service.get_test(test_id)
    return test
```

## Adding New Services

### Step 1: Create Your Service

```python
# app/services/my_new_service.py
from typing import List, Dict, Any
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository

class MyNewService:
    """My new service description."""

    def __init__(
        self,
        test_definition_repository: ITestDefinitionRepository
    ):
        self.test_definition_repository = test_definition_repository

    async def do_something(self) -> List[Dict[str, Any]]:
        """Service method implementation."""
        return await self.test_definition_repository.get_all()
```

### Step 2: Register in Container

```python
# app/core/container.py

# In imports section
from app.services.my_new_service import MyNewService

# In Container class
class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    # My New Service
    my_new_service = providers.Singleton(
        MyNewService,
        test_definition_repository=test_definition_repository
    )
```

### Step 3: Create Provider Function (Optional)

```python
# app/core/container.py

@inject
def provide_my_new_service(
    service: MyNewService = Depends(Provide[Container.my_new_service])
) -> MyNewService:
    """FastAPI provider for MyNewService."""
    return service

# Create alias
DependsMyNewService = Depends(provide_my_new_service)
```

### Step 4: Wire Module (If Using @inject)

```python
# In init_container() function
container.wire(
    modules=[
        # ... existing modules ...
        "app.services.my_new_service",
    ]
)
```

### Step 5: Use in FastAPI Routes

```python
from fastapi import APIRouter, Depends
from app.core.container import DependsMyNewService

router = APIRouter()

@router.get("/something")
async def get_something(
    service: MyNewService = DependsMyNewService
):
    return await service.do_something()
```

## Testing with DI Container

### Method 1: Provider Overriding

```python
import pytest
from unittest.mock import Mock
from app.core.container import get_container, override_provider, reset_provider

@pytest.fixture
async def mock_execution_service():
    """Mock execution service for testing."""
    mock_service = Mock()
    mock_service.get_test.return_value = {"id": "test-123", "name": "Mock Test"}

    override_provider("execution_service", mock_service)

    yield mock_service

    reset_provider("execution_service")

@pytest.mark.asyncio
async def test_get_test_with_mock(mock_execution_service):
    """Test endpoint with mocked service."""
    # The endpoint will now use the mocked service
    response = await client.get("/tests/test-123")
    assert response.status_code == 200
```

### Method 2: Test Container

```python
from app.core.container import TestContainer
from unittest.mock import Mock

def test_with_test_container():
    """Test using separate test container."""
    test_container = TestContainer()

    # Override providers with mocks
    test_container.execution_service.override(
        providers.Object(Mock())
    )

    # Wire test container
    test_container.wire(modules=["app.api.v1.endpoints.tests"])

    # Run tests...
    # test_container.execution_service() returns mock

    # Cleanup
    test_container.unwire()
```

### Method 3: Direct Injection

```python
from app.services.execution_service import ExecutionService
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_execution_service_logic():
    """Test service logic directly."""
    # Create mock dependencies
    mock_schedule_resolver = Mock()
    mock_status_manager = Mock()
    mock_result_persister = Mock()
    mock_test_run_repository = Mock()

    # Create service with mocked dependencies
    service = ExecutionService(
        schedule_resolver=mock_schedule_resolver,
        status_manager=mock_status_manager,
        result_persister=mock_result_persister,
        test_run_repository=mock_test_run_repository
    )

    # Test service methods
    result = await service.get_test("test-123")
    assert result is not None
```

## Configuration Management

### Environment Variables

Configuration is loaded from environment variables via `app/core/config.py`:

```python
# In container
config = providers.Configuration()

# Bind to settings
config.core.database_url = providers.Object(settings.DATABASE_URL)
config.core.redis_url = providers.Object(settings.REDIS_URL)
config.llm.api_key = providers.Object(settings.LLM_API_KEY)
```

### Overriding Configuration for Tests

```python
def test_with_custom_config():
    """Test with custom configuration."""
    container = Container()

    # Override configuration
    container.config.core.database_url.from_value("sqlite:///:memory:")

    # Now services will use test database
    ...
```

## Best Practices

### 1. Use Singleton for Stateful Services

```python
# GOOD - Singleton for stateful service
execution_service = providers.Singleton(ExecutionService, ...)

# BAD - Factory would create multiple instances
execution_service = providers.Factory(ExecutionService, ...)
```

### 2. Use Factory for Request-scoped Resources

```python
# GOOD - Factory for database sessions
db_session = providers.Factory(lambda: next(get_db()))

# BAD - Singleton would share session across requests
db_session = providers.Singleton(lambda: next(get_db()))
```

### 3. Depend on Interfaces, Not Implementations

```python
# GOOD - Depend on interface
def __init__(
    self,
    repository: ITestRunRepository
):
    self.repository = repository

# BAD - Depend on concrete implementation
def __init__(
    self,
    repository: SQLAlchemyTestRunRepository
):
    self.repository = repository
```

### 4. Use Provider Functions for FastAPI

```python
# GOOD - Use provider function
@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(provide_execution_service)
):
    return await service.get_test(test_id)

# ALSO GOOD - Use @inject decorator
@inject
@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(Provide[Container.execution_service])
):
    return await service.get_test(test_id)
```

### 5. Clean Up Overrides in Tests

```python
@pytest.fixture
def mock_service():
    """Fixture that cleans up overrides."""
    override_provider("my_service", Mock())
    yield
    reset_provider("my_service")  # Always cleanup
```

## Migration Guide

### Migrating from Manual Dependency Injection

#### Before (Manual Injection)

```python
class ExecutionService:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.schedule_resolver = ScheduleResolver()
        self.status_manager = RunStatusManager()

    async def get_test(self, test_id: str):
        resolver = ScheduleResolver()  # Created every time!
        manager = RunStatusManager()   # Created every time!
        ...
```

#### After (DI Container)

```python
class ExecutionService:
    def __init__(
        self,
        schedule_resolver: ScheduleResolver,
        status_manager: RunStatusManager,
        test_run_repository: ITestRunRepository
    ):
        self.schedule_resolver = schedule_resolver  # Singleton injected
        self.status_manager = status_manager        # Singleton injected
        self.test_run_repository = test_run_repository

    async def get_test(self, test_id: str):
        # Use injected dependencies
        test_ids = await self.schedule_resolver.resolve_schedule(...)
        ...
```

### Migrating RepositoryFactory

#### Before (RepositoryFactory)

```python
from app.repositories.repository_factory import RepositoryFactory

class ExecutionService:
    def __init__(self):
        self.test_run_repo = RepositoryFactory.get_test_run_repository()
```

#### After (DI Container)

```python
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class ExecutionService:
    def __init__(
        self,
        test_run_repository: ITestRunRepository
    ):
        self.test_run_repository = test_run_repository
```

## Troubleshooting

### Issue: Circular Dependency Error

**Problem**: Service A depends on Service B, but Service B also depends on Service A.

**Solution**: Refactor to introduce a third service or use events/callbacks:

```python
# BAD - Circular dependency
class ServiceA:
    def __init__(self, service_b: ServiceB): ...

class ServiceB:
    def __init__(self, service_a: ServiceA): ...

# GOOD - Refactor
class ServiceA:
    def __init__(self, event_publisher: EventPublisher): ...

class ServiceB:
    def __init__(self, event_publisher: EventPublisher): ...
```

### Issue: "Container not initialized" Error

**Problem**: Container not initialized before use.

**Solution**: Ensure `init_container()` is called during startup:

```python
# In main.py
from app.core.container import init_container

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_container()  # Calls init_container()
    yield
    await shutdown_container()
```

### Issue: Provider Not Found

**Problem**: `Provide[Container.nonexistent_provider]` used.

**Solution**: Ensure provider exists in container:

```python
# In container.py
class Container(containers.DeclarativeContainer):
    nonexistent_provider = providers.Singleton(NonexistentService)
```

## Performance Considerations

### Overhead

The DI container adds minimal overhead:
- Singleton resolution: ~1-2 microseconds
- Factory resolution: ~2-5 microseconds
- Provider injection: ~1-3 microseconds

### Optimization Tips

1. **Use Singleton for Stateful Services**: Avoid recreating expensive objects
2. **Lazy Initialization**: Services created only when first used
3. **Avoid Deep Dependency Trees**: Keep dependency graph shallow (<5 levels)
4. **Profile Performance**: Use profiling tools to identify bottlenecks

## Reference

### Available Provider Functions

```python
# Repositories
provide_test_run_repository() -> ITestRunRepository
provide_test_definition_repository() -> ITestDefinitionRepository
provide_schedule_repository() -> IScheduleRepository
provide_test_case_repository() -> ITestCaseRepository

# Services
provide_execution_service() -> ExecutionService
provide_schedule_resolver() -> ScheduleResolver
provide_run_status_manager() -> RunStatusManager
provide_result_persister() -> ResultPersister
provide_analytics_service() -> AnalyticsService
provide_suite_service() -> SuiteService
provide_prompt_builder() -> PromptBuilder
provide_response_parser() -> ResponseParser
provide_script_validation_service() -> ScriptValidationService

# LLM Components
provide_llm_client() -> BaseLanguageModel

# Resources
provide_db_session() -> AsyncSession
provide_redis_client() -> Redis
```

### Available Aliases

```python
DependsExecutionService
DependsScheduleResolver
DependsAnalyticsService
DependsSuiteService
DependsTestRunRepository
DependsTestDefinitionRepository
DependsScheduleRepository
```

## Further Reading

- [dependency-injector Documentation](https://python-dependency-injector.ets-labs.org/)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Dependency Injection Pattern](https://en.wikipedia.org/wiki/Dependency_injection)

## Support

For issues or questions:
1. Check this guide first
2. Review existing provider examples in `container.py`
3. Check `dependency-injector` documentation
4. Ask in team chat or create issue
