# CLAUDE.md

AI-powered E2E testing framework using GLM LLM + DeepAgents + Playwright for browser automation.

## Quick Start

```bash
./start-dev.sh     # Start dev environment
./start-prod.sh    # Start prod environment
# Stop with corresponding stop scripts
```

## Architecture

```
Frontend (React/Vite :5173) → Nginx (:8080) → Unified Backend (FastAPI :8011)
                                                    ↓
                              PostgreSQL (:5432) ← Temporal Server
```

## Project Rules

Detailed gudance is organized in `.claude/rules/`:

| Rule File | Content |
|-----------|---------|
| `development.md` | Docker commands, database operations |
| `database.md` | Schema, relationships, timestamp handling |
| `frontend.md` | Design system, routing, state management |
| `i18n.md` | Internationalization requirements |
| `backend.md` | API structure, LLM integration, services |
| `test-execution.md` | DeepAgents test runner pipeline, execution flow |
| `troubleshooting.md` | Common issues and solutions |
| `config.md` | Environment variables, port mappings |
| `performance.md` | Query optimization, worker scaling |

## SOLID Architecture

This project implements a comprehensive SOLID principles-based architecture for maintainability, testability, and scalability. The refactoring applies all five SOLID principles throughout the codebase.

### Principles Applied

- **Single Responsibility Principle (SRP)**: Each class has one clear purpose
  - Repositories handle data access only
  - Services contain business logic only
  - Strategies encapsulate specific algorithms
  - Result types handle response formatting only

- **Open/Closed Principle (OCP)**: Open for extension, closed for modification
  - Strategy patterns allow adding new behaviors without modifying existing code
  - New schedule types can be added via new strategies
  - New execution modes can be added via new strategies

- **Liskov Substitution Principle (LSP)**: Consistent interfaces, interchangeable implementations
  - All repository implementations can be swapped without breaking services
  - All health checkers are interchangeable
  - All strategies follow the same contract

- **Interface Segregation Principle (ISP)**: Focused, small interfaces
  - `IHealthChecker` - health checking only
  - `IMetricsCollector` - metrics collection only
  - Repository interfaces - domain-specific data access

- **Dependency Inversion Principle (DIP)**: Depend on abstractions, not concretions
  - Services depend on repository interfaces, not implementations
  - High-level modules don't depend on low-level modules
  - Dependency injection container manages all dependencies

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  REST endpoints, request validation, response formatting    │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────────────────┐
│                   Service Layer                             │
│  Business logic, orchestration, Result types, Strategies   │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────────────────┐
│                 Repository Layer                            │
│  Data access abstractions (ITestRunRepository, etc.)       │
└────────────────────┬────────────────────────────────────────┘
                     │ implemented by
┌────────────────────▼────────────────────────────────────────┐
│            Repository Implementations                       │
│  SQLAlchemyTestRunRepository, etc.                          │
└────────────────────┬────────────────────────────────────────┘
                     │ uses
┌────────────────────▼────────────────────────────────────────┐
│                  Database Layer                              │
│  PostgreSQL + SQLAlchemy ORM + AsyncSession                │
└─────────────────────────────────────────────────────────────┘
```

### Repository Layer

The repository layer implements the Repository Pattern for clean separation of data access logic.

**Available Repositories:**

| Repository | Interface | Purpose | Key Methods |
|------------|-----------|---------|-------------|
| TestRunRepository | `ITestRunRepository` | Test run data access | `create()`, `get_by_id()`, `update_status()`, `get_stats_by_date_range()` |
| TestDefinitionRepository | `ITestDefinitionRepository` | Test definition data access | `create()`, `get_by_id()`, `get_active_definitions()`, `get_by_tags()` |
| ScheduleRepository | `IScheduleRepository` | Schedule data access | `create()`, `get_due_schedules()`, `activate()`, `update_next_run_time()` |
| TestCaseRepository | `ITestCaseRepository` | Test case result data access | `create()`, `get_by_run_id()`, `get_by_test_definition_id()` |

**Usage Example:**

```python
from app.repositories.repository_factory import RepositoryFactory

# Get repository instance (singleton)
test_run_repo = RepositoryFactory.get_test_run_repository()

# Use repository
test_run = await test_run_repo.create(
    run_id="test-123",
    test_definition_id=100,
    start_time_ms=1000000,
    db_session=db
)

# Get with filters
recent_runs = await test_run_repo.get_recent_runs(
    days=7,
    db_session=db,
    limit=10
)
```

**Benefits:**

- Testability: Easy to mock for unit tests
- Flexibility: Can swap implementations (SQLAlchemy → MongoDB)
- Separation: Data logic isolated from business logic
- Type Safety: Full type hints with async support

### Service Layer

The service layer contains business logic and uses Result wrapper types for consistent error handling.

#### Result Types

Services use specialized result types for consistent error handling and HTTP status mapping.

**Available Result Types:**

| Type | Purpose | HTTP Status |
|------|---------|-------------|
| `ServiceSuccess[T]` | Successful operation with data | 200 |
| `ServiceError[E]` | Failed operation with error details | 400-500 |
| `NotFoundError` | Resource not found | 404 |
| `ConflictError` | Resource conflict | 409 |
| `ValidationError` | Input validation failed | 400 |
| `PermissionError` | Permission denied | 403 |
| `TestExecutionError` | Test execution failed | 500 |

**Usage Example:**

```python
from app.core.service_result_types import ServiceSuccess, ServiceError, NotFoundError

# Service method returning Result
async def get_test_run(self, run_id: str) -> ServiceSuccess[TestRun] | ServiceError:
    try:
        test_run = await self.test_run_repository.get_by_id(run_id, db)
        if not test_run:
            return NotFoundError("TestRun", run_id)
        return ServiceSuccess(data=test_run)
    except Exception as e:
        return ServiceError(f"Failed to get test run: {e}")

# Using Result
result = await service.get_test_run("test-123")
if result.is_success():
    test_run = result.get_data()
    print(f"Found test run: {test_run.run_id}")
else:
    error = result.get_error_message()
    status = result.get_http_status()
    print(f"Error {status}: {error}")
```

**Error Code Categories:**

- 1000-1999: General errors
- 2000-2999: Database errors
- 3000-3999: Validation errors
- 4000-4999: Permission errors
- 5000-5999: Resource errors
- 6000-6999: Business logic errors
- 7000-7999: Test execution errors
- 8000-8999: Temporal errors

### Strategy Patterns

The Strategy Pattern implements the Open/Closed Principle for extensible behavior.

#### Schedule Resolver Strategies

Schedule resolution logic is encapsulated in strategies, allowing new schedule types without modifying existing code.

**Available Strategies:**

| Strategy | Schedule Type | Description |
|----------|--------------|-------------|
| `SingleTestResolver` | `single` | Resolves single test definition |
| `SuiteResolver` | `suite` | Resolves test suite to multiple definitions |
| `TagFilterResolver` | `tag_filter` | Resolves tests matching tags |

**Usage Example:**

```python
from app.services.schedule_resolver import ScheduleResolver

# Create resolver (uses factory pattern internally)
resolver = ScheduleResolver()

# Resolve schedule (automatically picks correct strategy)
test_ids = await resolver.resolve_schedule(schedule, db)

# Strategy is automatically selected based on schedule.schedule_type
# 'single' → SingleTestResolver
# 'suite' → SuiteResolver
# 'tag_filter' → TagFilterResolver
```

**Adding New Strategies:**

```python
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy
from app.services.strategies import ScheduleResolverFactory

class CustomResolver(ScheduleResolverStrategy):
    """Custom resolver for new schedule type."""

    async def resolve(self, schedule, db):
        self.validate_schedule(schedule)
        # Custom resolution logic
        return [1, 2, 3]

    def get_strategy_name(self):
        return "CustomResolver"

    def get_supported_schedule_types(self):
        return ['custom']

# Register strategy
ScheduleResolverFactory.register_strategy('custom', CustomResolver())

# Now available for use!
# No changes needed to existing code
```

#### Execution Strategies

Test execution modes are implemented as strategies for extensibility.

**Available Strategies:**

| Strategy | Mode | Description |
|----------|------|-------------|
| `ScriptExecutionStrategy` | `script` | Execute approved Playwright scripts |
| `NLStepExecutionStrategy` | `nl_steps` | Execute natural language steps (deprecated) |

### Health Check System

Comprehensive health checking with pluggable health checkers following Interface Segregation Principle.

**Available Health Checkers:**

| Checker | Component | Critical | Metrics |
|---------|-----------|----------|---------|
| `DatabaseHealthChecker` | PostgreSQL | Yes | Connectivity, query performance, pool size |
| `RedisHealthChecker` | Redis | Yes | Connectivity, memory usage |
| `LLMHealthChecker` | GLM LLM | No | API connectivity, response time |
| `TemporalHealthChecker` | Temporal | Yes | Connectivity, worker health |
| `FilesystemHealthChecker` | Disk | No | Write permissions, disk space |

**Usage Example:**

```python
from app.health.checkers import DatabaseHealthChecker, RedisHealthChecker

# Create health checkers
db_checker = DatabaseHealthChecker(timeout=5.0)
redis_checker = RedisHealthChecker(timeout=3.0)

# Perform health checks
db_health = await db_checker.check_health()
redis_health = await redis_checker.check_health()

# Check results
if db_health.status == HealthStatus.HEALTHY:
    print(f"DB is healthy: {db_health.details}")

# Safe wrapper with error handling
health = await db_checker.safe_check()  # Never throws, returns UNHEALTHY on error
```

**Health Check Interface:**

All health checkers implement `IHealthChecker`:

```python
class IHealthChecker(ABC):
    @abstractmethod
    async def check_health(self) -> ComponentHealth:
        """Perform health check."""
        pass

    @abstractmethod
    def get_check_type(self) -> str:
        """Get checker identifier."""
        pass

    @abstractmethod
    def is_critical(self) -> bool:
        """Check if component is critical."""
        pass
```

### Metrics Collection

Performance metrics collection with decorator-based instrumentation.

**Metrics Types:**

| Type | Description | Example |
|------|-------------|---------|
| Timing | Operation execution time | `database.query.execution_time` |
| Counter | Incremental counters | `http.requests.total` |
| Gauge | Current values | `database.connections.active` |
| Error | Error occurrences | `llm.api.errors` |

**Usage Examples:**

```python
from app.core.metrics.metrics_decorators import track_timing, track_metrics, track_errors
from app.core.container import get_container

# Decorator-based metrics
@track_timing("database.user.create")
async def create_user(user_data):
    # Execution time automatically recorded
    pass

@track_metrics("service.execution.process")
async def process_request(request):
    # Timing and errors automatically recorded
    pass

# Manual metrics collection
metrics = get_container().metrics_collector()
metrics.record_timing("database.query", 45.2)
metrics.record_counter("http.requests", 1)
metrics.record_gauge("database.connections.active", 10)
metrics.record_error("llm.api", "TimeoutError", "Request timed out")

# Get statistics
stats = metrics.get_timing_stats("database.query")
print(f"Average: {stats.avg_ms}ms, p95: {stats.p95_ms}ms")
```

**Available Metrics:**

- Timing statistics: min, max, avg, p50, p95, p99
- Counter aggregation: total counts
- Gauge values: current state
- Error tracking: by operation and type
- Summary reports: comprehensive metrics dump

### Dependency Injection Container

Comprehensive DI container using `dependency-injector` for centralized dependency management.

**Container Features:**

- 20+ registered services
- Singleton lifecycle for shared services
- Factory lifecycle for request-scoped objects
- FastAPI integration via `@inject` decorator
- Configuration binding from environment
- Provider overriding for testing

**Key Services:**

| Service | Type | Purpose |
|---------|------|---------|
| `execution_service` | Singleton | Test execution orchestration |
| `analytics_service` | Singleton | Analytics and reporting |
| `schedule_resolver` | Singleton | Schedule resolution logic |
| `test_run_repository` | Singleton | Test run data access |
| `test_definition_repository` | Singleton | Test definition data access |
| `metrics_collector` | Singleton | Performance metrics |
| `llm_client` | Singleton | LLM API client |
| `browser_automation` | Factory | Browser automation (per-request) |

**Usage in FastAPI Routes:**

```python
from fastapi import Depends, APIRouter
from app.core.container import Provide, Container, inject
from app.services.execution_service import ExecutionService

router = APIRouter()

@inject
@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(Provide[Container.execution_service])
):
    # Service automatically injected by container
    return await service.get_test(test_id)

# Alternative: Using provider functions
from app.core.container import provide_execution_service

@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = Depends(provide_execution_service)
):
    return await service.get_test(test_id)
```

**Testing with Mocks:**

```python
from unittest.mock import Mock
from app.core.container import get_container, override_provider

# Get container
container = get_container()

# Override with mock
mock_service = Mock()
override_provider("execution_service", mock_service)

# Now execution_service uses the mock
# ... run tests ...

# Reset override
from app.core.container import reset_provider
reset_provider("execution_service")
```

**Service Lifetimes:**

| Lifetime | Description | Use Case |
|----------|-------------|----------|
| Singleton | One instance for app lifetime | Repositories, Services, Factories |
| Factory | New instance each time | Request-scoped objects, Browser automation |
| Configuration | Environment-based config | Database URL, API keys, Feature flags |

### Architecture Diagrams

#### Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes                            │
│  @router.get("/tests/{test_id}")                             │
│  async def get_test(                                         │
│      service: ExecutionService = Depends(...)                │
│  ):                                                          │
└────────────────────┬────────────────────────────────────────┘
                     │ @inject decorator
                     │ Provide[Container.execution_service]
┌────────────────────▼────────────────────────────────────────┐
│              DI Container (dependency-injector)              │
│  - Manages service lifetimes                                 │
│  - Wires dependencies automatically                          │
│  - Provides FastAPI integration                              │
└────────────────────┬────────────────────────────────────────┘
                     │ singleton injection
┌────────────────────▼────────────────────────────────────────┐
│              ExecutionService                                │
│  - Business logic for test execution                        │
│  - Uses Result types for error handling                     │
│  - Depends on repository interfaces                         │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on interfaces
┌────────────────────▼────────────────────────────────────────┐
│          ITestRunRepository (interface)                     │
│  - Abstract data access contract                             │
│  - Methods: create(), get_by_id(), update_status()          │
└────────────────────┬────────────────────────────────────────┘
                     │ implemented by
┌────────────────────▼────────────────────────────────────────┐
│       SQLAlchemyTestRunRepository (implementation)          │
│  - Concrete SQLAlchemy implementation                       │
│  - Uses AsyncSession for queries                             │
└────────────────────┬────────────────────────────────────────┘
                     │ queries database
┌────────────────────▼────────────────────────────────────────┐
│               PostgreSQL Database                           │
└─────────────────────────────────────────────────────────────┘
```

#### Strategy Pattern Flow

```
┌─────────────────────────────────────────────────────────────┐
│               ScheduleResolver (Facade)                      │
│  resolve_schedule(schedule, db)                             │
└────────────────────┬────────────────────────────────────────┘
                     │ delegates to
┌────────────────────▼────────────────────────────────────────┐
│         ScheduleResolverFactory (Registry)                  │
│  get_strategy_for_schedule(schedule)                       │
└────────────────────┬────────────────────────────────────────┘
                     │ selects strategy based on schedule_type
┌────────────────────▼────────────────────────────────────────┐
│       ScheduleResolverStrategy (Abstract)                   │
│  - resolve(schedule, db)                                    │
│  - get_strategy_name()                                      │
│  - get_supported_schedule_types()                          │
└────────────────────┬────────────────────────────────────────┘
                     │ implemented by
       ┌─────────────┼─────────────┬─────────────┐
       │             │             │             │
┌──────▼──────┐ ┌──▼─────────┐ ┌─▼──────────┐ ┌─▼──────────┐
│  SingleTest │ │   Suite    │ │ TagFilter  │ │  Custom    │
│  Resolver   │ │  Resolver  │ │  Resolver  │ │  Resolver  │
│ (single)    │ │  (suite)   │ │(tag_filter)│ │ (custom)   │
└─────────────┘ └────────────┘ └────────────┘ └────────────┘
       │             │             │             │
       └─────────────┼─────────────┴─────────────┘
                     │ returns List[int]
┌────────────────────▼────────────────────────────────────────┐
│         List of test_definition_ids                        │
│  [1, 2, 3]                                                  │
└─────────────────────────────────────────────────────────────┘
```

#### Service Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│              API Request (GET /api/v1/tests/123)            │
└────────────────────┬────────────────────────────────────────┘
                     │ FastAPI route handler
┌────────────────────▼────────────────────────────────────────┐
│         @inject + Depends(Provide[Container...])            │
│  - Dependency injection from container                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Service Layer                                  │
│  - Business logic                                           │
│  - Result type wrapping                                    │
│  - Strategy usage                                           │
│  - Metrics decoration                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│         Result Types (ServiceSuccess/ServiceError)          │
│  - Error code mapping                                       │
│  - HTTP status determination                                │
│  - Consistent response format                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Repository Layer                               │
│  - Data access abstractions                                 │
│  - Interface-based design                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Database Layer                                 │
│  - SQLAlchemy ORM                                           │
│  - Async database operations                                │
└─────────────────────────────────────────────────────────────┘
```

## SOLID Development Guide

### Creating New Services

**Step 1: Define Service with Dependencies**

```python
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.core.service_result_types import ServiceSuccess, ServiceError

class MyNewService:
    def __init__(
        self,
        test_run_repository: ITestRunRepository = None,
        db_session=None
    ):
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()
        self.db = db_session
```

**Step 2: Use Result Types**

```python
async def perform_action(self, id: int) -> ServiceSuccess[Data] | ServiceError:
    try:
        data = await self.test_run_repository.get_by_pk(id, self.db)
        if not data:
            return NotFoundError("TestRun", str(id))

        # Business logic here
        result = process_data(data)
        return ServiceSuccess(data=result)

    except ValueError as e:
        return ServiceValidationError(f"Invalid input: {e}")
    except Exception as e:
        return ServiceError(f"Operation failed: {e}")
```

**Step 3: Add to DI Container**

```python
# In app/core/container.py
class Container(containers.DeclarativeContainer):
    # Add new service
    my_new_service = providers.Singleton(
        MyNewService,
        test_run_repository=test_run_repository
    )

# Add provider function
@inject
def provide_my_new_service(
    service: MyNewService = Depends(Provide[Container.my_new_service])
) -> MyNewService:
    return service
```

**Step 4: Use in API**

```python
from app.core.container import provide_my_new_service

@router.get("/action/{id}")
async def perform_action(
    id: int,
    service: MyNewService = Depends(provide_my_new_service)
):
    result = await service.perform_action(id)
    if result.is_success():
        return JSONResponse(
            content=result.to_dict(),
            status_code=200
        )
    else:
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.get_http_status()
        )
```

### Creating New Strategies

**Step 1: Define Strategy Interface**

```python
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy

class MyCustomStrategy(ScheduleResolverStrategy):
    """Custom strategy for new schedule type."""

    async def resolve(self, schedule, db):
        self.validate_schedule(schedule)

        # Custom resolution logic
        test_ids = await self._resolve_custom(schedule, db)

        return test_ids

    def get_strategy_name(self):
        return "MyCustomStrategy"

    def get_supported_schedule_types(self):
        return ['custom_type']

    def validate_schedule(self, schedule):
        if schedule.schedule_type != 'custom_type':
            raise ValueError("Invalid schedule type")
        if not hasattr(schedule, 'custom_field'):
            raise ValueError("Missing custom_field")
```

**Step 2: Register Strategy**

```python
from app.services.strategies import ScheduleResolverFactory

# Register at application startup
ScheduleResolverFactory.register_strategy(
    'custom_type',
    MyCustomStrategy()
)
```

**Step 3: Use Strategy**

```python
# No changes needed to existing code!
# Strategy is automatically available

resolver = ScheduleResolver()
schedule = Schedule(
    name="Custom Schedule",
    schedule_type='custom_type',
    custom_field='value'
)

test_ids = await resolver.resolve_schedule(schedule, db)
```

### Creating New Health Checkers

**Step 1: Implement Interface**

```python
from app.core.interfaces.health_check_interface import IHealthChecker
from app.core.health_check_types import ComponentHealth, HealthStatus

class MyCustomHealthChecker(IHealthChecker):
    """Custom health checker for new component."""

    async def check_health(self) -> ComponentHealth:
        import time
        start_time = time.time()

        try:
            # Perform health check
            is_healthy = await self._check_component()

            return ComponentHealth(
                component_name="my_component",
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details="Component is healthy" if is_healthy else "Component is unhealthy",
                is_critical=False
            )
        except Exception as e:
            return ComponentHealth(
                component_name="my_component",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details=f"Health check failed: {str(e)}",
                is_critical=False
            )

    def get_check_type(self) -> str:
        return "my_component"

    def is_critical(self) -> bool:
        return False  # Set to True if component is critical
```

**Step 2: Register in Health Check Service**

```python
# In app/health/health_service.py or similar
from app.health.checkers.my_custom_health_checker import MyCustomHealthChecker

# Add to health checkers list
health_checkers.append(MyCustomHealthChecker())
```

**Step 3: Use Health Checker**

```python
checker = MyCustomHealthChecker()
health = await checker.check_health()

if health.status == HealthStatus.HEALTHY:
    print(f"Component healthy: {health.details}")
else:
    print(f"Component unhealthy: {health.details}")
```

### Testing with SOLID Architecture

**Unit Testing Services (Mock Repositories):**

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_execution_service():
    # Mock repository
    mock_repo = Mock()
    mock_repo.get_by_id = AsyncMock(return_value=Mock(id=1, run_id="test-123"))

    # Inject mock repository
    service = ExecutionService(test_run_repository=mock_repo)

    # Test service logic
    result = await service.get_test_run("test-123", db=None)

    # Verify result
    assert result.is_success()
    assert result.get_data().run_id == "test-123"

    # Verify repository was called
    mock_repo.get_by_id.assert_called_once_with("test-123", None)
```

**Integration Testing (Real Database):**

```python
import pytest
from app.repositories.test_run_repository import SQLAlchemyTestRunRepository

@pytest.mark.asyncio
async def test_repository_integration(test_db_session):
    repository = SQLAlchemyTestRunRepository()

    # Create
    run = await repository.create(
        run_id="test-123",
        test_definition_id=100,
        start_time_ms=1000000,
        db_session=test_db_session
    )

    # Retrieve
    retrieved = await repository.get_by_id("test-123", test_db_session)
    assert retrieved is not None
    assert retrieved.run_id == "test-123"
```

**Testing Strategies:**

```python
import pytest
from app.services.strategies.single_test_resolver import SingleTestResolver

@pytest.mark.asyncio
async def test_single_resolver():
    resolver = SingleTestResolver()
    schedule = Schedule(
        schedule_type='single',
        test_definition_id=5
    )
    db = Mock()

    result = await resolver.resolve(schedule, db)

    assert result == [5]
    assert resolver.get_strategy_name() == "SingleTestResolver"
    assert 'single' in resolver.get_supported_schedule_types()
```

**Testing with DI Container:**

```python
from app.core.container import Container, override_provider, reset_provider

def test_with_mock_container():
    container = Container()

    # Override with mock
    mock_service = Mock()
    override_provider("execution_service", mock_service)

    # Test with mock
    service = container.execution_service()
    assert service is mock_service

    # Reset
    reset_provider("execution_service")
```

## Migration Guide

### Migrating from Direct Database Access

**Before (violates DIP):**

```python
class ExecutionService:
    def __init__(self, db_session):
        self.db = db_session

    async def create_test_run(self, run_id, test_id):
        test_run = TestRun(
            run_id=run_id,
            test_definition_id=test_id,
            status='pending'
        )
        self.db.add(test_run)
        await self.db.commit()
        return test_run
```

**After (follows DIP):**

```python
class ExecutionService:
    def __init__(
        self,
        db_session=None,
        test_run_repository: ITestRunRepository = None
    ):
        self.db = db_session
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()

    async def create_test_run(self, run_id, test_id):
        return await self.test_run_repository.create(
            run_id=run_id,
            test_definition_id=test_id,
            start_time_ms=int(time.time() * 1000),
            db_session=self.db
        )
```

### Migrating to Result Types

**Before (inconsistent error handling):**

```python
async def get_test_run(self, run_id: str):
    try:
        test_run = await self.repository.get_by_id(run_id, self.db)
        if not test_run:
            return None, "Not found"
        return test_run, None
    except Exception as e:
        return None, str(e)
```

**After (consistent Result types):**

```python
async def get_test_run(self, run_id: str) -> ServiceSuccess[TestRun] | ServiceError:
    try:
        test_run = await self.repository.get_by_id(run_id, self.db)
        if not test_run:
            return NotFoundError("TestRun", run_id)
        return ServiceSuccess(data=test_run)
    except Exception as e:
        return ServiceError(f"Failed to get test run: {e}")
```

### Migrating from If/Elif to Strategies

**Before (violates OCP):**

```python
class ScheduleResolver:
    async def resolve_schedule(self, schedule, db):
        if schedule.schedule_type == 'single':
            return [schedule.test_definition_id]
        elif schedule.schedule_type == 'suite':
            # suite logic...
        elif schedule.schedule_type == 'tag_filter':
            # tag filter logic...
        else:
            raise ValueError(f"Unknown type: {schedule.schedule_type}")
```

**After (follows OCP):**

```python
# No changes needed! Refactored resolver maintains backward compatibility

from app.services.schedule_resolver import ScheduleResolver

resolver = ScheduleResolver()
test_ids = await resolver.resolve_schedule(schedule, db)

# To add new types, create new strategy - no code modification needed!
```

## Best Practices

### 1. Always Use Interfaces

```python
# Good - depends on abstraction
def __init__(self, repository: ITestRunRepository):
    self.repository = repository

# Bad - depends on concrete implementation
def __init__(self, repository: SQLAlchemyTestRunRepository):
    self.repository = repository
```

### 2. Use Result Types Consistently

```python
# Good - consistent error handling
async def perform_action(self) -> ServiceSuccess[Result] | ServiceError:
    try:
        result = await self._do_work()
        return ServiceSuccess(data=result)
    except ValueError as e:
        return ServiceValidationError(f"Invalid input: {e}")
    except Exception as e:
        return ServiceError(f"Operation failed: {e}")

# Bad - inconsistent error handling
async def perform_action(self):
    try:
        result = await self._do_work()
        return result, None
    except Exception as e:
        return None, str(e)
```

### 3. Inject Dependencies

```python
# Good - allows injection and testing
def __init__(
    self,
    repository: ITestRunRepository = None,
    db_session=None
):
    self.repository = repository or RepositoryFactory.get_test_run_repository()
    self.db = db_session

# Bad - tightly coupled
def __init__(self):
    self.repository = SQLAlchemyTestRunRepository()
    self.db = get_db()
```

### 4. Use Metrics Decorators

```python
# Good - automatic metrics
@track_timing("database.user.create")
@track_metrics("service.user.create")
async def create_user(self, user_data):
    # Logic here
    pass

# Bad - manual metrics tracking
async def create_user(self, user_data):
    start = time.time()
    try:
        # Logic here
        duration = (time.time() - start) * 1000
        metrics.record_timing("user.create", duration)
    except Exception as e:
        metrics.record_error("user.create", type(e).__name__)
        raise
```

### 5. Keep Strategies Focused

```python
# Good - single responsibility
class SingleTestResolver(ScheduleResolverStrategy):
    async def resolve(self, schedule, db):
        # Only handles single test resolution
        return [schedule.test_definition_id]

# Bad - multiple responsibilities
class MultiPurposeResolver(ScheduleResolverStrategy):
    async def resolve(self, schedule, db):
        # Handles single, suite, and tag_filter
        # Too much logic, hard to test
        if schedule.schedule_type == 'single':
            # ...
        elif schedule.schedule_type == 'suite':
            # ...
```

### 6. Handle Async Properly

```python
# Good - proper async handling
test_run = await self.repository.get_by_id("test-123", db)

# Bad - forgetting await
test_run = self.repository.get_by_id("test-123", db)  # Returns coroutine!
```

## Key Points

- **Hot-reload**: `backend/app/` and `frontend/src/` auto-refresh
- **Design System**: Read DESIGN.md before UI changes (IBM Carbon-inspired)
- **LLM**: GLM via OpenAI-compatible API (`app/core/agent_config.py`)
- **Token Monitoring**: Per-call LLM token usage tracked via LangChain callback (`app/core/llm_usage_callback.py`), persisted to `llm_usage` table, analytics at `/api/v1/llm-usage/`
- **Timestamps**: PostgreSQL naive datetime, use `datetime.utcnow()`
- **Feedback**: All save/submit/delete ops must show success/failure messages
- **SOLID Principles**: All new code must follow SOLID architecture
- **Dependency Injection**: Use DI container for all service dependencies
- **Result Types**: Use ServiceSuccess/ServiceError for consistent error handling
- **Repository Pattern**: Always use repositories for data access
- **Strategy Pattern**: Use strategies for extensible behaviors

## AI Team Configuration (autogenerated by team-configurator, 2025-06-12)

**Important: YOU MUST USE subagents when available for the task.**

### Detected Tech Stack

**Backend Framework:**
- FastAPI 0.109+ with async/await patterns
- Python 3.12+ with modern type hints
- Pydantic V2 for validation and schemas
- SQLAlchemy 2.0 with async support
- Alembic for database migrations

**AI & Agent Framework:**
- LangChain 1.0+ for LLM orchestration
- LangGraph 1.0+ for agent workflows and state machines
- GLM LLM via OpenAI-compatible API
- DeepAgents framework for test composition
- LangGraph checkpoint with PostgreSQL

**Orchestration & Automation:**
- Temporal Server for workflow orchestration
- Temporal activities for test execution
- Playwright for browser automation
- Cron-based test scheduling

**Frontend:**
- React 18+ with hooks and modern patterns
- Vite for fast development and hot-reload
- IBM Carbon-inspired design system
- React Query for state management
- Chart.js for data visualization

**Database & Storage:**
- PostgreSQL with asyncpg driver
- Redis for caching and job state
- Alembic for schema migrations
- Naive datetime timestamps (UTC)

**Testing & Quality:**
- Pytest for backend testing
- Playwright for E2E testing
- Factory Boy for test data
- Coverage analysis and mutation testing

### AI Team Assignments

| Task Category | Specialist Agent | Notes |
|---------------|------------------|-------|
| **FastAPI Backend Development** | `@fastapi-expert` | API design, Pydantic V2 schemas, async/await patterns, middleware, dependency injection |
| **Python Core Development** | `@python-expert` | Python 3.12+ features, type hints, async programming, service layer architecture |
| **Database & Migrations** | `@python-expert` + `@code-reviewer` | SQLAlchemy 2.0 async, Alembic migrations, query optimization, relationship design |
| **LangGraph Agents** | `@python-expert` | LangGraph workflows, state machines, checkpoint management, agent orchestration |
| **LangChain Integration** | `@python-expert` | LLM chains, prompt engineering, context management, token monitoring |
| **Temporal Workflows** | `@python-expert` | Workflow design, activity implementation, error handling, scheduling |
| **React Frontend** | `@react-component-architect` | Component architecture, hooks, state management, design system adherence |
| **UI/UX Implementation** | `@react-component-architect` | IBM Carbon design system, responsive layouts, accessibility |
| **E2E Testing Strategy** | `@testing-expert` | Playwright test design, test data management, coverage analysis |
| **Test Automation** | `@testing-expert` | Pytest configuration, fixtures, factories, integration tests |
| **Performance Optimization** | `@performance-optimizer` | Query optimization, caching strategies, async performance, worker scaling |
| **Code Quality & Security** | `@code-reviewer` | Security review, code quality assessment, best practices enforcement |
| **Codebase Analysis** | `@code-archaeologist` | Architecture documentation, dependency analysis, technical debt assessment |
| **Documentation** | `@documentation-specialist` | API docs, architecture docs, onboarding guides |

### Workflow Delegation Triggers

| Scenario | Delegate To | Handoff Context |
|----------|-------------|-----------------|
| New FastAPI endpoints or API refactoring | `@fastapi-expert` | "Implement REST API with Pydantic V2 validation and async patterns" |
| LangGraph agent development or debugging | `@python-expert` | "Develop LangGraph workflow with PostgreSQL checkpoint" |
| Database schema changes or migrations | `@python-expert` → `@code-reviewer` | "Create Alembic migration for schema changes, then review" |
| Slow queries or performance issues | `@performance-optimizer` | "Optimize database queries and async operations" |
| React component development or UI changes | `@react-component-architect` | "Follow IBM Carbon design system, maintain consistency" |
| Test strategy or coverage improvements | `@testing-expert` | "Design comprehensive test suite with factories and fixtures" |
| Security review before deployment | `@code-reviewer` | "Conduct security-focused review with severity assessment" |
| Architecture documentation or onboarding | `@code-archaeologist` | "Produce comprehensive codebase assessment report" |
| Code review after feature completion | `@code-reviewer` | "Review merged code for quality, security, and maintainability" |

### Sample Commands

```bash
# Backend development
"@fastapi-expert Design and implement a new REST endpoint for test schedule management with Pydantic V2 validation"

# Agent development
"@python-expert Create a LangGraph workflow for test composition with state management and PostgreSQL checkpoint"

# Frontend development
"@react-component-architect Build a monitoring dashboard component following the IBM Carbon design system"

# Testing strategy
"@testing-expert Design a comprehensive test suite for the Temporal workflow execution with proper fixtures"

# Performance optimization
"@performance-optimizer Analyze and optimize the test execution pipeline for better throughput"

# Code review
"@code-reviewer Review the recent changes to the LangGraph agent implementation for security and quality"
```

### Development Workflow Integration

1. **Feature Development**: Always start with the appropriate specialist agent
2. **Code Review**: Use `@code-reviewer` before merging to main
3. **Performance Checks**: Use `@performance-optimizer` proactively before scaling
4. **Documentation**: Update docs via `@documentation-specialist` after significant changes
5. **Testing**: Ensure `@testing-expert` validates test coverage and quality

### Key Project-Specific Considerations

- **Hot-Reload**: Backend and frontend changes auto-apply without rebuilding
- **Design System**: Always consult DESIGN.md before UI changes (IBM Carbon-inspired)
- **Timestamps**: Use `datetime.utcnow()` for PostgreSQL naive datetime
- **LLM Integration**: GLM via OpenAI-compatible API with token monitoring
- **Temporal**: Scheduling handled natively by Temporal Server
- **Database**: All schema changes MUST use Alembic migrations
- **Testing**: E2E tests use Playwright, unit tests use Pytest
- **SOLID Architecture**: Follow SOLID principles for all new code
- **Dependency Injection**: Use DI container for service dependencies
- **Result Types**: Use ServiceSuccess/ServiceError for consistent error handling
- **Repository Pattern**: Always use repositories for data access
