# Token Management DI Container - Quick Reference

## For Developers: How to Use Token Services

### 1. In FastAPI Routes (Recommended)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.container import (
    DependsTokenBudgetService,
    DependsTokenQuotaService,
    DependsTokenAlertService,
    DependsTokenReportingService
)
from app.services.token_budget_service import TokenBudgetService

router = APIRouter()

@router.post("/token/check")
async def check_token_availability(
    scope_type: str,
    scope_id: int,
    requested_tokens: int,
    db: AsyncSession = Depends(get_db),
    budget_service: TokenBudgetService = DependsTokenBudgetService
):
    """Check token availability before LLM call."""
    result = await budget_service.check_token_availability(
        scope_type, scope_id, requested_tokens, db
    )
    return result
```

### 2. In Other Services

```python
from app.core.container import get_container

class MyLLMService:
    def __init__(self):
        container = get_container()
        self.budget_service = container.token_budget_service()
        self.quota_service = container.token_quota_service()
        self.alert_service = container.token_alert_service()

    async def make_llm_call(self, prompt: str, db):
        # Check availability
        availability = await self.budget_service.check_token_availability(
            "organization", 1, 1000, db
        )

        if not availability.data["available"]:
            raise Exception("Insufficient tokens")

        # Make LLM call
        response = await self.llm_client.generate(prompt)

        # Record usage
        await self.budget_service.record_token_usage(
            "organization", 1, response.tokens_used, db
        )

        # Check for alerts
        await self.alert_service.check_and_trigger_alerts(
            budget_id=1, db=db
        )

        return response
```

### 3. In Tests (with Mocks)

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.core.container import get_container, override_provider, reset_provider

@pytest.fixture
def mock_budget_service():
    """Create mock budget service."""
    service = Mock()
    service.check_token_availability = AsyncMock(
        return_value=service_success(data={"available": True})
    )
    service.record_token_usage = AsyncMock(
        return_value=service_success(data={"remaining_tokens": 9000})
    )
    return service

def test_with_mock(mock_budget_service):
    """Test with mocked budget service."""
    container = get_container()

    # Override with mock
    override_provider("token_budget_service", mock_budget_service)

    # Test
    result = await mock_budget_service.check_token_availability(...)
    assert result.data["available"] == True

    # Clean up
    reset_provider("token_budget_service")
```

### 4. Direct Container Access

```python
from app.core.container import Container, get_container

# Get container instance
container = get_container()

# Access services
budget_service = container.token_budget_service()
quota_service = container.token_quota_service()
alert_service = container.token_alert_service()
reporting_service = container.token_reporting_service()

# Access repositories
budget_repo = container.token_budget_repository()
quota_repo = container.token_quota_repository()
alert_repo = container.token_alert_repository()
```

## Available Providers

### Repository Providers
- `token_budget_repository` → `SQLAlchemyTokenBudgetRepository`
- `token_quota_repository` → `SQLAlchemyTokenQuotaRepository`
- `token_alert_repository` → `SQLAlchemyTokenAlertRepository`

### Service Providers
- `token_budget_service` → `TokenBudgetService`
- `token_quota_service` → `TokenQuotaService`
- `token_alert_service` → `TokenAlertService`
- `token_reporting_service` → `TokenReportingService`

### Provider Functions
- `provide_token_budget_service()`
- `provide_token_quota_service()`
- `provide_token_alert_service()`
- `provide_token_reporting_service()`

### Provider Aliases (for FastAPI)
- `DependsTokenBudgetService`
- `DependsTokenQuotaService`
- `DependsTokenAlertService`
- `DependsTokenReportingService`

## Service Dependencies

### TokenBudgetService
- `budget_repository: ITokenBudgetRepository`
- `metrics_collector: IMetricsCollector`

### TokenQuotaService
- `quota_repository: ITokenQuotaRepository`
- `metrics_collector: IMetricsCollector`

### TokenAlertService
- `alert_repository: ITokenAlertRepository`
- `metrics_collector: IMetricsCollector`

### TokenReportingService
- `metrics_collector: IMetricsCollector`

## Common Patterns

### Pattern 1: Check Before Use

```python
async def llm_operation(user_id: int, prompt: str, db: AsyncSession):
    # 1. Check budget
    budget_check = await budget_service.check_token_availability(
        "user", user_id, estimated_tokens, db
    )

    if not budget_check.data["available"]:
        return {"error": "Insufficient tokens"}

    # 2. Execute LLM call
    response = await llm_client.generate(prompt)

    # 3. Record usage
    await budget_service.record_token_usage(
        "user", user_id, response.tokens_used, db
    )

    return response
```

### Pattern 2: Alert Handling

```python
async def handle_token_usage(budget_id: int, tokens_used: int, db: AsyncSession):
    # Record usage
    result = await budget_service.record_token_usage(
        budget_id, tokens_used, db
    )

    # Check for alerts
    alerts = await alert_service.check_and_trigger_alerts(
        budget_id=budget_id, db=db
    )

    # Send notifications if alerts triggered
    if alerts.data["triggered_alerts_count"] > 0:
        for alert_data in alerts.data["triggered_alerts"]:
            await alert_service.send_alert_notifications(
                alert_data["alert_id"], db, channels=["ui"]
            )
```

### Pattern 3: Reporting

```python
async def get_usage_report(start_date: datetime, end_date: datetime, db: AsyncSession):
    # Generate usage report
    report = await reporting_service.generate_usage_report(
        db=db,
        period_type="daily",
        start_date=start_date,
        end_date=end_date
    )

    # Calculate costs
    costs = await reporting_service.calculate_costs(
        db=db,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "usage": report.data,
        "costs": costs.data
    }
```

## Testing Utilities

### Repository Factory Methods

```python
from app.repositories.repository_factory import RepositoryFactory

# Get repositories
budget_repo = RepositoryFactory.get_token_budget_repository()
quota_repo = RepositoryFactory.get_token_quota_repository()
alert_repo = RepositoryFactory.get_token_alert_repository()

# Set custom repositories (for testing)
RepositoryFactory.set_token_budget_repository(mock_budget_repo)
RepositoryFactory.set_token_quota_repository(mock_quota_repo)
RepositoryFactory.set_token_alert_repository(mock_alert_repo)

# Reset factory (for testing)
RepositoryFactory.reset()
```

### Container Override Methods

```python
from app.core.container import get_container, override_provider, reset_provider

# Override any provider
override_provider("token_budget_service", mock_service)
override_provider("token_quota_service", mock_service)
override_provider("token_alert_service", mock_service)
override_provider("token_reporting_service", mock_service)

# Reset override
reset_provider("token_budget_service")
```

## Lifecycle Management

All token management services and repositories use **Singleton** lifecycle:

- Created once on first access
- Shared across all requests
- Automatically managed by container
- Thread-safe for concurrent access

## Configuration

Token management services use configuration from:

1. **Environment Variables** (via `app.core.config.settings`)
   - Token enforcement modes
   - Alert thresholds
   - Cost calculation parameters

2. **Database Models** (via repository layer)
   - Budget configurations
   - Quota settings
   - Alert rules

3. **Metrics Collector** (shared service)
   - Usage tracking
   - Performance monitoring
   - Alert metrics

## Troubleshooting

### Issue: "Container not initialized"
**Solution:** Call `init_container()` during application startup

### Issue: "Provider not found"
**Solution:** Ensure provider is wired in `init_container()`

### Issue: "Import error"
**Solution:** Check that all token services are imported in `container.py`

### Issue: "Circular dependency"
**Solution:** All token services are designed without circular dependencies

## Best Practices

1. ✅ **Use Provider Aliases in FastAPI routes** - Cleanest syntax
2. ✅ **Inject services, not repositories** - Follows layered architecture
3. ✅ **Use async/await** - All service methods are async
4. ✅ **Handle service results** - Use `is_success()`, `is_error()` helpers
5. ✅ **Mock services in tests** - Use override providers
6. ✅ **Reset state between tests** - Use `reset_container()` or `RepositoryFactory.reset()`

## Files Reference

### Core Files
- `app/core/container.py` - DI container configuration
- `app/repositories/repository_factory.py` - Repository factory

### Service Files
- `app/services/token_budget_service.py` - Budget management
- `app/services/token_quota_service.py` - Quota management
- `app/services/token_alert_service.py` - Alert management
- `app/services/token_reporting_service.py` - Reporting and analytics

### Repository Files
- `app/repositories/token_budget_repository.py` - Budget data access
- `app/repositories/token_quota_repository.py` - Quota data access
- `app/repositories/token_alert_repository.py` - Alert data access

### Interface Files
- `app/repositories/interfaces/token_budget_repository_interface.py`
- `app/repositories/interfaces/token_quota_repository_interface.py`
- `app/repositories/interfaces/token_alert_repository_interface.py`
