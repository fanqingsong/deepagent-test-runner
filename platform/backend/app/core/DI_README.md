# DI Container - Quick Start

## What is it?

A Dependency Injection container that automatically manages service dependencies and lifecycles.

## Key Benefits

- **No more manual dependency creation**: Services get their dependencies automatically
- **Centralized configuration**: All dependencies in one place
- **Easy testing**: Swap implementations with mocks
- **Better performance**: Singleton services reused across requests

## Quick Usage

### In FastAPI Routes

```python
from fastapi import APIRouter, Depends
from app.core.container import DependsExecutionService

router = APIRouter()

@router.get("/tests/{test_id}")
async def get_test(
    test_id: str,
    service: ExecutionService = DependsExecutionService  # Injected!
):
    return await service.get_test(test_id)
```

### In Services

```python
class MyService:
    def __init__(
        self,
        test_run_repository: ITestRunRepository  # Injected!
    ):
        self.test_run_repository = test_run_repository
```

### In Tests

```python
from unittest.mock import Mock
from app.core.container import override_provider, reset_provider

def test_with_mock():
    mock_service = Mock()
    override_provider("execution_service", mock_service)

    # Test with mock...

    reset_provider("execution_service")
```

## Available Dependencies

### Services
- `DependsExecutionService`
- `DependsScheduleResolver`
- `DependsAnalyticsService`
- `DependsSuiteService`

### Repositories
- `DependsTestRunRepository`
- `DependsTestDefinitionRepository`
- `DependsScheduleRepository`

## Adding New Services

1. Create service with constructor injection
2. Register in `app/core/container.py`
3. Create provider function (optional)
4. Use in routes via `Depends`

## Documentation

- **Complete Guide**: `DI_CONTAINER_GUIDE.md`
- **Migration Examples**: `DI_MIGRATION_EXAMPLE.md`
- **Tests**: `tests/test_container.py`

## Status

✅ Container implemented
✅ All services registered
✅ FastAPI integrated
✅ Tests created
✅ Documentation complete

Ready to use! 🚀
