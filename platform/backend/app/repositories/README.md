# Repository Pattern Documentation

## Overview

This repository implements the Repository Pattern for database operations, following SOLID principles and the Dependency Inversion Principle. Services depend on repository interfaces rather than concrete database implementations, enabling:

- **Testability**: Easy to mock repositories for unit tests
- **Flexibility**: Can swap database implementations without changing services
- **Separation of Concerns**: Database logic isolated from business logic
- **Maintainability**: Clear separation between data access and business logic

## Architecture

```
Services (business logic)
    ↓ depends on
Repository Interfaces (abstractions)
    ↓ implemented by
Repository Implementations (concrete)
    ↓ use
Database Session (SQLAlchemy)
```

## Components

### 1. Repository Interfaces

Located in `app/repositories/interfaces/`, these define the contract for data access operations.

**Example: `ITestRunRepository`**

```python
from abc import ABC, abstractmethod

class ITestRunRepository(ABC):
    @abstractmethod
    async def create(self, run_id: str, test_definition_id: Optional[int], start_time_ms: int, db_session) -> TestRun:
        """Create a new test run record."""
        pass

    @abstractmethod
    async def get_by_id(self, run_id: str, db_session) -> Optional[TestRun]:
        """Retrieve a test run by its run_id."""
        pass
```

### 2. Repository Implementations

Located in `app/repositories/`, these provide concrete implementations using SQLAlchemy.

**Example: `SQLAlchemyTestRunRepository`**

```python
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class SQLAlchemyTestRunRepository(ITestRunRepository):
    async def create(self, run_id: str, test_definition_id: Optional[int], start_time_ms: int, db_session) -> TestRun:
        # Implementation using SQLAlchemy
        test_run = TestRun(
            run_id=run_id,
            test_definition_id=test_definition_id,
            status='pending',
            start_time=start_time_ms
        )
        db_session.add(test_run)
        await db_session.flush()
        await db_session.refresh(test_run)
        return test_run
```

### 3. Repository Factory

The `RepositoryFactory` provides centralized repository creation with singleton pattern.

**Example Usage:**

```python
from app.repositories.repository_factory import RepositoryFactory

# Get TestRun repository instance (singleton)
test_run_repo = RepositoryFactory.get_test_run_repository()

# Use TestRun repository
test_run = await test_run_repo.create(
    run_id="test-123",
    test_definition_id=100,
    start_time_ms=1000000,
    db_session=db
)

# Get TestDefinition repository instance (singleton)
test_def_repo = RepositoryFactory.get_test_definition_repository()

# Use TestDefinition repository
test_def = await test_def_repo.get_by_id(123, db_session)
active_definitions = await test_def_repo.get_active_definitions(db_session)
```

## Usage in Services

### Dependency Injection Pattern

Services receive repository instances via constructor injection:

```python
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class ExecutionService:
    def __init__(
        self,
        db_session=None,
        test_run_repository: Optional[ITestRunRepository] = None
    ):
        self.db = db_session
        # Use provided repository or get from factory
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()
```

### Service Integration

Services use repositories instead of direct database access:

**Before (direct database access):**

```python
# ❌ Violates Dependency Inversion
test_run = TestRun(run_id=run_id, status='pending')
self.db.add(test_run)
await self.db.commit()
```

**After (using repository):**

```python
# ✅ Follows Dependency Inversion
test_run = await self.test_run_repository.create(
    run_id=run_id,
    test_definition_id=test_definition_id,
    start_time_ms=start_time_ms,
    db_session=self.db
)
```

## Available Repository Methods

### TestRun Repository

The `ITestRunRepository` interface provides:

| Method | Description | Returns |
|--------|-------------|---------|
| `create()` | Create new test run | TestRun |
| `get_by_id()` | Get by run_id | Optional[TestRun] |
| `get_by_pk()` | Get by primary key | Optional[TestRun] |
| `update_status()` | Update status and timestamps | TestRun |
| `update_results()` | Update with execution results | TestRun |
| `get_by_test_definition_id()` | Get runs for test definition | List[TestRun] |
| `get_pending_runs()` | Get all pending runs | List[TestRun] |
| `get_recent_runs()` | Get recent runs by date | List[TestRun] |
| `count_by_status()` | Count runs by status | int |
| `delete()` | Delete test run | bool |
| `get_all()` | Get all with optional filter | List[TestRun] |
| `exists()` | Check if run exists | bool |
| `get_stats_by_date_range()` | Get statistics for date range | Dict[str, Any] |

### TestDefinition Repository

The `ITestDefinitionRepository` interface provides:

| Method | Description | Returns |
|--------|-------------|---------|
| `create()` | Create new test definition | TestDefinition |
| `get_by_id()` | Get by primary key ID | Optional[TestDefinition] |
| `get_by_test_id()` | Get by test_id | Optional[TestDefinition] |
| `get_by_name()` | Get by name | Optional[TestDefinition] |
| `get_all()` | Get all with optional filtering | List[TestDefinition] |
| `update()` | Update test definition fields | TestDefinition |
| `delete()` | Delete test definition | bool |
| `get_by_suite_id()` | Get definitions by suite ID | List[TestDefinition] |
| `get_by_tag()` | Get definitions by single tag | List[TestDefinition] |
| `get_by_tags()` | Get definitions by multiple tags | List[TestDefinition] |
| `search()` | Search by name/description/test_id | List[TestDefinition] |
| `count()` | Count total definitions | int |
| `get_active_definitions()` | Get all active definitions | List[TestDefinition] |
| `get_by_workspace_id()` | Get definitions from workspace | List[TestDefinition] |
| `get_by_review_status()` | Get definitions by review status | List[TestDefinition] |
| `get_regression_tests()` | Get all regression tests | List[TestDefinition] |
| `exists_by_test_id()` | Check if test_id exists | bool |
| `update_script()` | Update Playwright script | TestDefinition |
| `update_review_status()` | Update review status | TestDefinition |

### Schedule Repository

The `IScheduleRepository` interface provides:

| Method | Description | Returns |
|--------|-------------|---------|
| `create()` | Create new schedule | Schedule |
| `get_by_id()` | Get by primary key ID | Optional[Schedule] |
| `get_all()` | Get all with optional filtering | List[Schedule] |
| `get_active_schedules()` | Get all active schedules | List[Schedule] |
| `get_by_test_definition_id()` | Get schedules by test definition ID | List[Schedule] |
| `get_by_suite_id()` | Get schedules by test suite ID | List[Schedule] |
| `update()` | Update schedule fields | Schedule |
| `update_next_run_time()` | Update next scheduled execution time | Schedule |
| `activate()` | Activate a schedule | Schedule |
| `deactivate()` | Deactivate a schedule | Schedule |
| `delete()` | Delete a schedule | bool |
| `get_by_type()` | Get schedules by type (single/suite/tag) | List[Schedule] |
| `get_due_schedules()` | Get schedules due for execution | List[Schedule] |
| `count()` | Count total schedules | int |
| `count_by_status()` | Count schedules by active status | int |
| `update_last_run_time()` | Update last execution time | Schedule |
| `exists()` | Check if schedule exists | bool |

**Schedule Repository Examples:**

```python
from app.repositories.repository_factory import RepositoryFactory

# Get Schedule repository
schedule_repo = RepositoryFactory.get_schedule_repository()

# Create a new schedule
schedule_data = {
    'name': 'Daily Test Schedule',
    'schedule_type': 'single',
    'test_definition_ids': [1, 2, 3],
    'test_definition_id': 1,
    'cron_expression': '0 0 * * *',  # Daily at midnight
    'timezone': 'UTC',
    'environment_overrides': {'ENV': 'production'},
    'is_active': True,
    'allow_concurrent': False,
    'max_retries': 3
}

schedule = await schedule_repo.create(schedule_data, db_session)

# Get active schedules that are due for execution
from datetime import datetime, timedelta

now = datetime.utcnow()
due_schedules = await schedule_repo.get_due_schedules(now, db_session)

# Activate or deactivate a schedule
activated = await schedule_repo.activate(schedule.id, db_session)
deactivated = await schedule_repo.deactivate(schedule.id, db_session)

# Update next run time after execution
next_run = datetime.utcnow() + timedelta(hours=24)
updated = await schedule_repo.update_next_run_time(schedule.id, next_run, db_session)

# Get schedules by type
single_schedules = await schedule_repo.get_by_type('single', db_session, active_only=True)

# Count schedules
total = await schedule_repo.count(db_session)
active_count = await schedule_repo.count_by_status(True, db_session)
```

## Testing

### Unit Tests with Mocks

Mock repositories for unit testing services:

```python
import pytest
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_service_with_mock():
    # Create mock repository
    mock_repo = Mock()
    mock_repo.create.return_value = Mock(id=1, run_id="test-123")

    # Inject into service
    service = ExecutionService(test_run_repository=mock_repo)

    # Test service logic
    result = await service.create_test_run("test-123", [100], {}, db)
    assert result.run_id == "test-123"
```

### Integration Tests with Database

Use real database for repository testing:

```python
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

### Custom Repository Implementation

For testing or alternative implementations:

```python
class MockTestRunRepository(ITestRunRepository):
    """Custom mock repository."""
    async def create(self, run_id, test_definition_id, start_time_ms, db_session):
        return Mock(id=1, run_id=run_id)

    # Implement other methods...

# Use custom repository
RepositoryFactory.set_test_run_repository(MockTestRunRepository())
```

## Migration Guide

### Migrating from Direct Database Access

**Step 1: Identify Database Operations**

Find all direct database access in services:

```python
# Before
self.db.add(test_run)
await self.db.commit()
```

**Step 2: Replace with Repository Method**

Identify the appropriate repository method:

```python
# After
await self.test_run_repository.create(...)
```

**Step 3: Update Service Constructor**

Add repository injection:

```python
def __init__(self, db_session=None, test_run_repository=None):
    self.db = db_session
    self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()
```

**Step 4: Update Tests**

Update tests to inject mock repositories:

```python
# Before
service = ExecutionService(db=mock_db)

# After
mock_repo = Mock()
service = ExecutionService(db=mock_db, test_run_repository=mock_repo)
```

## Best Practices

### 1. Use Interfaces, Not Implementations

```python
# ✅ Good - depends on abstraction
def __init__(self, repository: ITestRunRepository):
    self.repository = repository

# ❌ Bad - depends on concrete implementation
def __init__(self, repository: SQLAlchemyTestRunRepository):
    self.repository = repository
```

### 2. Inject Dependencies

```python
# ✅ Good - allows injection
def __init__(self, repository: ITestRunRepository = None):
    self.repository = repository or RepositoryFactory.get_test_run_repository()

# ❌ Bad - tightly coupled
def __init__(self):
    self.repository = SQLAlchemyTestRunRepository()
```

### 3. Handle Errors Properly

```python
try:
    test_run = await self.repository.create(...)
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise
except Exception as e:
    logger.error(f"Database error: {e}")
    raise
```

### 4. Use Async Patterns

All repository methods are async - always await them:

```python
# ✅ Good
test_run = await self.repository.get_by_id("test-123", db)

# ❌ Bad
test_run = self.repository.get_by_id("test-123", db)
```

## Benefits

### 1. Testability

- Easy to mock repositories for unit tests
- Test services without database
- Fast test execution

### 2. Flexibility

- Swap database implementations (PostgreSQL → MySQL)
- Add caching layer without changing services
- Support multiple databases

### 3. Maintainability

- Centralized data access logic
- Easier to add new data sources
- Clear separation of concerns

### 4. SOLID Principles

- **Single Responsibility**: Repository only handles data access
- **Open/Closed**: Open for extension (new repositories), closed for modification
- **Liskov Substitution**: Any repository implementation can be used
- **Interface Segregation**: Focused interfaces per domain
- **Dependency Inversion**: Depend on abstractions, not concretions

## Troubleshooting

### Common Issues

**Issue: Circular Import Errors**

```python
# ❌ Causes circular import
from app.services.execution_service import ExecutionService
from app.repositories.test_run_repository import SQLAlchemyTestRunRepository

# ✅ Use lazy imports or TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.execution_service import ExecutionService
```

**Issue: Repository Not Initialized**

```python
# ❌ Forgets to initialize repository
service = ExecutionService(db=db)
# service.test_run_repository is None!

# ✅ Uses factory pattern
service = ExecutionService(db=db)
# service.test_run_repository is auto-initialized
```

**Issue: Mock Repository Not Returning Expected Values**

```python
# ❌ Mock not configured
mock_repo = Mock()
result = await mock_repo.get_by_id("test-123", db)
# result is None!

# ✅ Configure mock return value
mock_repo.get_by_id.return_value = TestRun(id=1, run_id="test-123")
result = await mock_repo.get_by_id("test-123", db)
# result is TestRun object
```

## Future Enhancements

Potential improvements to the repository pattern:

1. **Caching Layer**: Add Redis caching to repository methods
2. **Read/Write Separation**: Separate repositories for read/write operations
3. **Transaction Management**: Built-in transaction support
4. **Bulk Operations**: Optimized bulk insert/update methods
5. **Query Builders**: Fluent query builder interfaces
6. **Event Sourcing**: Add event publishing for data changes

## References

- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
