# Schedule Resolver Strategies

## Overview

This module implements the Strategy Pattern for schedule resolution, following the SOLID Open/Closed Principle. The schedule resolution logic has been refactored from hard-coded `if/elif` chains to a flexible, extensible strategy-based architecture.

## Architecture

```
ScheduleResolver (Facade)
    ↓ uses
ScheduleResolverFactory (Factory + Registry)
    ↓ creates
ScheduleResolverStrategy (Abstract Interface)
    ↓ implemented by
├── SingleTestResolver
├── SuiteResolver
└── TagFilterResolver
```

## Benefits

### 1. Open/Closed Principle
- **Open for extension**: Add new schedule types by creating new strategies
- **Closed for modification**: Existing strategies remain stable

### 2. Single Responsibility Principle
- Each strategy handles one schedule type
- Factory handles strategy creation and registration
- Resolver delegates to appropriate strategy

### 3. Testability
- Each strategy can be tested independently
- Factory can be mocked for testing
- Clear separation of concerns

### 4. Extensibility
- New strategies can be added without modifying existing code
- Custom strategies can be registered at runtime
- Plugin architecture for extensions

## Usage

### Basic Usage

```python
from app.services.schedule_resolver import ScheduleResolver

# Create resolver
resolver = ScheduleResolver()

# Resolve schedule
test_ids = await resolver.resolve_schedule(schedule, db)
```

### Using Factory Directly

```python
from app.services.strategies import ScheduleResolverFactory

# Get appropriate strategy
strategy = ScheduleResolverFactory.get_strategy('single')

# Use strategy
test_ids = await strategy.resolve(schedule, db)
```

### Registering Custom Strategies

```python
from app.services.strategies import ScheduleResolverFactory
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy

class CustomResolver(ScheduleResolverStrategy):
    """Custom resolver for special schedule types."""

    async def resolve(self, schedule, db):
        # Custom resolution logic
        return [1, 2, 3]

    def get_strategy_name(self):
        return "CustomResolver"

    def get_supported_schedule_types(self):
        return ['custom']

# Register custom strategy
ScheduleResolverFactory.register_strategy('custom', CustomResolver())

# Use custom strategy
strategy = ScheduleResolverFactory.get_strategy('custom')
test_ids = await strategy.resolve(schedule, db)
```

## Available Strategies

### SingleTestResolver
- **Schedule Type**: `single`
- **Purpose**: Resolve single test definitions
- **Required Fields**: `test_definition_id`
- **Example**:
  ```python
  schedule = Schedule(
      name="Single Test",
      schedule_type="single",
      test_definition_id=5
  )
  # Returns: [5]
  ```

### SuiteResolver
- **Schedule Type**: `suite`
- **Purpose**: Resolve test suites to multiple test definitions
- **Required Fields**: `test_suite_id`
- **Example**:
  ```python
  schedule = Schedule(
      name="Suite Schedule",
      schedule_type="suite",
      test_suite_id=10
  )
  # Returns: [1, 2, 3] (from suite.test_definition_ids)
  ```

### TagFilterResolver
- **Schedule Type**: `tag_filter`
- **Purpose**: Resolve tests matching specific tags
- **Required Fields**: `tag_filter`
- **Example**:
  ```python
  schedule = Schedule(
      name="Tag Filter",
      schedule_type="tag_filter",
      tag_filter="smoke"
  )
  # Returns: [1, 2, 3] (tests with 'smoke' tag)
  ```

## Adding New Strategies

### Step 1: Create Strategy Class

```python
# app/services/strategies/custom_resolver.py
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schedule import Schedule
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy

class CustomResolver(ScheduleResolverStrategy):
    """Custom resolver strategy."""

    async def resolve(self, schedule: Schedule, db: AsyncSession) -> List[int]:
        # Implement resolution logic
        self.validate_schedule(schedule)
        # ... your logic here ...
        return [1, 2, 3]

    def get_strategy_name(self) -> str:
        return "CustomResolver"

    def get_supported_schedule_types(self) -> List[str]:
        return ['custom']

    def validate_schedule(self, schedule: Schedule) -> None:
        """Validate schedule has required fields."""
        if not hasattr(schedule, 'custom_field'):
            raise ValueError("Custom field required")
```

### Step 2: Register Strategy

```python
# In your app initialization or configuration
from app.services.strategies import ScheduleResolverFactory
from app.services.strategies.custom_resolver import CustomResolver

ScheduleResolverFactory.register_strategy('custom', CustomResolver())
```

### Step 3: Use New Strategy

```python
# No changes needed to ScheduleResolver!
# The new strategy is automatically available

schedule = Schedule(
    name="Custom Schedule",
    schedule_type='custom',
    custom_field='value'
)

resolver = ScheduleResolver()
test_ids = await resolver.resolve_schedule(schedule, db)
```

## Testing

### Test Individual Strategies

```python
import pytest
from app.services.strategies.single_test_resolver import SingleTestResolver

@pytest.mark.asyncio
async def test_single_resolver():
    resolver = SingleTestResolver()
    schedule = Schedule(schedule_type='single', test_definition_id=5)
    db = Mock()

    result = await resolver.resolve(schedule, db)

    assert result == [5]
```

### Test Factory

```python
def test_factory():
    strategy = ScheduleResolverFactory.get_strategy('single')
    assert isinstance(strategy, SingleTestResolver)
```

### Test Custom Registration

```python
def test_custom_registration():
    ScheduleResolverFactory.register_strategy('custom', CustomResolver())
    strategy = ScheduleResolverFactory.get_strategy('custom')
    assert isinstance(strategy, CustomResolver)
```

## API Reference

### ScheduleResolverStrategy

**Abstract base class for all strategies.**

**Methods:**
- `async def resolve(schedule, db) -> List[int]`: Resolve schedule to test IDs
- `def get_strategy_name() -> str`: Get strategy name
- `def get_supported_schedule_types() -> List[str]`: Get supported types
- `def validate_schedule(schedule) -> None`: Validate schedule

### ScheduleResolverFactory

**Factory for creating and managing strategies.**

**Class Methods:**
- `get_strategy(schedule_type) -> ScheduleResolverStrategy`: Get strategy by type
- `get_strategy_for_schedule(schedule) -> ScheduleResolverStrategy`: Get strategy from schedule
- `register_strategy(schedule_type, strategy) -> None`: Register new strategy
- `list_strategies() -> Dict[str, str]`: List all registered strategies
- `is_strategy_registered(schedule_type) -> bool`: Check if strategy exists
- `unregister_strategy(schedule_type) -> bool`: Remove strategy (testing)
- `reset() -> None`: Reset factory (testing)

## Migration Guide

### Before (Old Code)
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

### After (New Code)
```python
# No changes needed! The refactored resolver maintains backward compatibility.

from app.services.schedule_resolver import ScheduleResolver

resolver = ScheduleResolver()
test_ids = await resolver.resolve_schedule(schedule, db)
```

## Performance Considerations

- Strategy lookup is O(1) via dictionary
- Factory initialization is lazy (on first use)
- Strategy instances are reused (singleton pattern)
- No performance degradation compared to if/elif chains

## Best Practices

1. **Keep strategies focused**: Each strategy should handle one schedule type
2. **Validate inputs**: Use `validate_schedule()` to check required fields
3. **Log appropriately**: Use logging for debugging and monitoring
4. **Test independently**: Each strategy should have its own test suite
5. **Document clearly**: Describe strategy purpose and requirements
6. **Handle errors**: Raise `ValueError` for validation failures

## Troubleshooting

### Issue: "Unknown schedule_type" error

**Cause**: Schedule type not registered in factory

**Solution**: Register strategy for that type or check for typos

```python
# Check available types
strategies = ScheduleResolverFactory.list_strategies()
print(strategies.keys())  # ['single', 'suite', 'tag_filter', ...]
```

### Issue: Custom strategy not working

**Cause**: Strategy not properly registered

**Solution**: Ensure strategy is registered before use

```python
# Register before use
ScheduleResolverFactory.register_strategy('custom', CustomResolver())

# Verify registration
assert ScheduleResolverFactory.is_strategy_registered('custom')
```

### Issue: Strategy validation error

**Cause**: Schedule missing required fields

**Solution**: Check schedule has required fields for strategy type

```python
# Check validation
strategy = ScheduleResolverFactory.get_strategy('single')
try:
    strategy.validate_schedule(schedule)
except ValueError as e:
    print(f"Validation error: {e}")
```

## Future Enhancements

Potential areas for extension:

1. **Composite strategies**: Combine multiple resolution methods
2. **Caching strategies**: Cache resolved test IDs for performance
3. **Async strategies**: Support for async resolution logic
4. **Conditional strategies**: Apply different logic based on conditions
5. **Strategy chains**: Chain multiple strategies together

## Related Files

- `app/services/schedule_resolver.py`: Main resolver facade
- `app/models/schedule.py`: Schedule ORM model
- `app/tests/test_schedule_resolver.py`: Original tests (backward compatibility)
- `app/tests/test_schedule_resolver_refactored.py`: New tests
- `app/tests/strategies/`: Strategy-specific tests
