# Activity Migration Guide

## Overview

This guide helps you migrate existing Temporal activities to the new standardized interface system. Migration ensures **Liskov Substitution Principle** compliance, making activities interchangeable and testable.

## Why Migrate?

### Benefits

1. **Consistency**: All activities follow the same patterns
2. **Testability**: Easy to test with consistent interfaces
3. **Maintainability**: Clear patterns for new activities
4. **Observability**: Consistent logging and metrics
5. **Error Handling**: Predictable error propagation
6. **Type Safety**: Strong typing with input/output classes

### Migration Impact

- **Minimal code changes** for existing activities
- **100% backward compatibility** maintained
- **No workflow changes** required
- **Gradual migration** possible (migrate one at a time)

## Migration Steps

### Step 1: Analyze Existing Activity

**Current Activity** (example: `prepare_test`):

```python
@activity.defn
async def prepare_test(input: PrepareTestInput) -> PrepareTestOutput:
    """Prepare test execution."""
    test_definition_id = input.test_definition_id
    run_id = input.run_id

    # Load test definition from database
    async def _load_test_data(db):
        test_def = await db.get(TestDefinition, test_definition_id)
        return PrepareTestOutput(
            test_definition_id=test_definition_id,
            run_id=run_id,
            url=test_def.url,
            test_goal=test_def.test_goal,
            test_steps=[],
        )

    return await run_with_session(_load_test_data)
```

**Identify**:
- Input type: `PrepareTestInput`
- Output type: `PrepareTestOutput`
- Core logic: Database query and output construction
- Error handling: Implicit (exceptions propagate)

### Step 2: Ensure Input/Output Classes Extend Base Classes

**Before**:

```python
@dataclass
class PrepareTestInput:
    test_definition_id: str
    run_id: str
    environment: Dict[str, Any]
```

**After**:

```python
@dataclass
class PrepareTestInput(ActivityInput):
    test_definition_id: str
    run_id: str
    environment: Dict[str, Any]
```

**Changes**:
- Extend `ActivityInput` instead of plain `dataclass`
- No other changes needed

### Step 3: Create Activity Class

**Create** `PrepareTestActivity` extending `BaseActivity`:

```python
class PrepareTestActivity(BaseActivity[PrepareTestInput, PrepareTestOutput]):
    """Activity for preparing test execution."""

    async def validate_input(self, input_data: PrepareTestInput) -> bool:
        """Validate input."""
        await super().validate_input(input_data)

        if not input_data.test_definition_id:
            raise ValueError("test_definition_id is required")
        if not input_data.run_id:
            raise ValueError("run_id is required")

        try:
            int(input_data.test_definition_id)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid test_definition_id: {e}")

        return True

    async def execute_impl(self, input_data: PrepareTestInput) -> PrepareTestOutput:
        """Execute preparation logic."""
        test_definition_id_str = input_data.test_definition_id
        run_id = input_data.run_id
        environment = input_data.environment or {}

        test_definition_id = int(test_definition_id_str)

        async def _load_test_data(db: AsyncSession) -> PrepareTestOutput:
            def_result = await db.execute(
                select(TestDefinition).where(TestDefinition.id == test_definition_id)
            )
            test_def = def_result.scalar_one_or_none()

            if not test_def:
                raise ValueError(f"Test definition {test_definition_id} not found")

            return PrepareTestOutput(
                test_definition_id=test_definition_id_str,
                run_id=run_id,
                url=test_def.url,
                test_goal=getattr(test_def, "test_goal", None),
                test_steps=[],
                environment=environment,
                mode="execute_only",
                execution_mode=getattr(test_def, "execution_mode", "script"),
                playwright_script=getattr(test_def, "playwright_script", None),
                script_status=getattr(test_def, "script_status", None),
            )

        return await run_with_session(_load_test_data)
```

**Key Changes**:
1. Extract core logic into `execute_impl()`
2. Add `validate_input()` with validation logic
3. Keep error handling (exceptions will be caught by base class)

### Step 4: Create Wrapper Function

**Create** wrapper for Temporal compatibility:

```python
@activity.defn
async def prepare_test(input: PrepareTestInput) -> PrepareTestOutput:
    """Temporal activity wrapper for PrepareTestActivity."""
    activity_instance = PrepareTestActivity()
    return await activity_instance.execute(input)
```

**Purpose**: Maintains backward compatibility with existing workflows.

### Step 5: Update Imports (If Needed)

**Before**:

```python
from app.temporal.activities.test_activities import prepare_test
```

**After**:

```python
from app.temporal.activities.test_activities_refactored import prepare_test
```

**Or** keep same file path and replace contents (recommended for gradual migration).

### Step 6: Test

**Run existing tests** to ensure backward compatibility:

```bash
pytest tests/temporal/activities/test_test_activities.py
```

**Run new tests** for interface compliance:

```bash
pytest tests/temporal/interfaces/test_activity_interface.py
pytest tests/temporal/interfaces/test_base_activity.py
```

## Common Migration Patterns

### Pattern 1: Simple Activity

**Simple activity** (no complex logic):

```python
# Before
@activity.defn
async def simple_activity(input: SimpleInput) -> SimpleOutput:
    result = process(input.data)
    return SimpleOutput(result=result)

# After
class SimpleActivity(BaseActivity[SimpleInput, SimpleOutput]):
    async def validate_input(self, input_data: SimpleInput) -> bool:
        await super().validate_input(input_data)
        if not input_data.data:
            raise ValueError("data is required")
        return True

    async def execute_impl(self, input_data: SimpleInput) -> SimpleOutput:
        result = process(input_data.data)
        return SimpleOutput(result=result)

@activity.defn
async def simple_activity(input: SimpleInput) -> SimpleOutput:
    activity_instance = SimpleActivity()
    return await activity_instance.execute(input)
```

### Pattern 2: Database Activity

**Database activity** (uses database session):

```python
# Before
@activity.defn
async def db_activity(input: DBInput) -> DBOutput:
    async def _process(db):
        result = await db.execute(query)
        return DBOutput(data=result)

    return await run_with_session(_process)

# After
class DBActivity(BaseActivity[DBInput, DBOutput]):
    async def validate_input(self, input_data: DBInput) -> bool:
        await super().validate_input(input_data)
        if not input_data.id:
            raise ValueError("id is required")
        return True

    async def execute_impl(self, input_data: DBInput) -> DBOutput:
        async def _process(db: AsyncSession) -> DBOutput:
            result = await db.execute(query)
            return DBOutput(data=result)

        return await run_with_session(_process)

@activity.defn
async def db_activity(input: DBInput) -> DBOutput:
    activity_instance = DBActivity()
    return await activity_instance.execute(input)
```

### Pattern 3: Activity with External Service

**External service activity** (calls external API):

```python
# Before
@activity.defn
async def external_activity(input: ExternalInput) -> ExternalOutput:
    client = ExternalServiceClient()
    result = await client.call(input.params)
    return ExternalOutput(result=result)

# After
class ExternalActivity(BaseActivity[ExternalInput, ExternalOutput]):
    async def validate_input(self, input_data: ExternalInput) -> bool:
        await super().validate_input(input_data)
        if not input_data.params:
            raise ValueError("params is required")
        return True

    async def execute_impl(self, input_data: ExternalInput) -> ExternalOutput:
        client = ExternalServiceClient()
        result = await client.call(input_data.params)
        return ExternalOutput(result=result)

    async def handle_error(self, error: Exception, input_data: ExternalInput) -> ActivityError:
        # Custom error handling for external service
        error_type = error.__class__.__name__

        # External service errors might be retryable
        is_retryable = "timeout" in str(error).lower() or "rate limit" in str(error).lower()

        return ActivityError(
            error_type=error_type,
            error_message=str(error),
            is_retryable=is_retryable,
        )

@activity.defn
async def external_activity(input: ExternalInput) -> ExternalOutput:
    activity_instance = ExternalActivity()
    return await activity_instance.execute(input)
```

## Validation Checklist

Use this checklist to ensure complete migration:

### Input/Output Classes

- [ ] Input class extends `ActivityInput`
- [ ] Output class extends `ActivityOutput`
- [ ] All required fields documented
- [ ] Default values specified
- [ ] Type hints added

### Activity Class

- [ ] Extends `BaseActivity[InputType, OutputType]`
- [ ] Implements `validate_input()`
- [ ] Implements `execute_impl()`
- [ ] Calls `super().validate_input()` first
- [ ] Raises `ValueError` for validation failures
- [ ] Returns correct output type

### Wrapper Function

- [ ] Decorated with `@activity.defn`
- [ ] Creates activity instance
- [ ] Calls `activity.execute(input)`
- [ ] Returns correct output type

### Error Handling

- [ ] Exceptions propagate correctly
- [ ] Custom error handling (if needed)
- [ ] Retry logic configured (if needed)

### Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Workflow tests pass
- [ ] Backward compatibility verified

## Gradual Migration Strategy

### Option 1: Side-by-Side Migration

1. Create new refactored file (`test_activities_refactored.py`)
2. Keep old file (`test_activities.py`)
3. Migrate one activity at a time
4. Test thoroughly
5. Switch imports when ready

**Pros**: Safe, easy to rollback
**Cons**: Duplicate code temporarily

### Option 2: In-Place Migration

1. Refactor activities one by one in same file
2. Test each activity thoroughly
3. Commit after each activity
4. No duplicate code

**Pros**: No duplicate code
**Cons**: Riskier, harder to rollback

### Option 3: Feature Flag Migration

1. Add feature flag for new implementation
2. Switch between old/new based on flag
3. Test both implementations
4. Remove old when confident

**Pros**: Very safe, A/B testing
**Cons**: More complex implementation

## Post-Migration

### Verify Workflows

Run all workflow tests to ensure compatibility:

```bash
pytest tests/temporal/workflows/test_test_execution.py
pytest tests/temporal/workflows/test_schedules.py
```

### Monitor Logs

Check logs for any unexpected behavior:

```bash
docker compose logs backend | grep "activity\."
```

### Check Metrics

Verify metrics are being collected:

```bash
# Check activity logs
docker compose logs backend | grep "activity_complete"

# Verify metrics structure
# Should see: activity_name, duration_ms, timestamp
```

### Performance Validation

Compare performance before/after:

```python
# Before migration
avg_duration_before = 1500  # ms

# After migration (should be similar)
avg_duration_after = 1520  # ms

# Overhead should be minimal (< 5%)
overhead = (avg_duration_after - avg_duration_before) / avg_duration_before * 100
assert overhead < 5, f"Overhead too high: {overhead}%"
```

## Troubleshooting

### Issue: Import Errors

**Error**: `ImportError: cannot import name 'ActivityInput'`

**Solution**: Ensure new modules are imported:

```python
from app.temporal.interfaces import ActivityInput, ActivityOutput, BaseActivity
```

### Issue: Type Errors

**Error**: `TypeError: Missing required field`

**Solution**: Ensure all input fields have values:

```python
input_data = MyActivityInput(
    required_field="value",
    optional_field=0,  # Default value
)
```

### Issue: Validation Failures

**Error**: `ValueError: Input validation failed`

**Solution**: Check validation logic:

```python
async def validate_input(self, input_data: InputType) -> bool:
    await super().validate_input(input_data)  # Call parent
    # Your validation
    return True
```

### Issue: Activity Not Retrying

**Error**: Activity fails but doesn't retry

**Solution**: Check error classification:

```python
async def handle_error(self, error: Exception, input_data: InputType) -> ActivityError:
    # Ensure is_retryable is set correctly
    is_retryable = error.__class__.__name__ not in ["ValidationError"]
    return ActivityError(
        error_type=error.__class__.__name__,
        error_message=str(error),
        is_retryable=is_retryable,
    )
```

## Example: Complete Migration

### Before Migration

```python
@activity.defn
async def mark_run_failed(input: MarkRunFailedInput) -> None:
    """Mark a test run as failed."""
    run_id = input.run_id
    error_message = input.error_message

    async def _mark_failed(db: AsyncSession) -> None:
        svc = ExecutionService(db)
        await svc.mark_run_failed(run_id, error_message)

    await run_with_session(_mark_failed)
```

### After Migration

```python
@dataclass
class MarkRunFailedInput(ActivityInput):
    """Input for mark_run_failed activity."""
    run_id: str
    error_message: Optional[str] = None

class MarkRunFailedActivity(BaseActivity[MarkRunFailedInput, None]):
    """Activity for marking a test run as failed."""

    async def validate_input(self, input_data: MarkRunFailedInput) -> bool:
        """Validate input."""
        await super().validate_input(input_data)

        if not input_data.run_id:
            raise ValueError("run_id is required")

        return True

    async def execute_impl(self, input_data: MarkRunFailedInput) -> None:
        """Execute mark failed logic."""
        run_id = input_data.run_id
        error_message = input_data.error_message

        async def _mark_failed(db: AsyncSession) -> None:
            svc = ExecutionService(db)
            await svc.mark_run_failed(run_id, error_message)

        await run_with_session(_mark_failed)

@activity.defn
async def mark_run_failed(input: MarkRunFailedInput) -> None:
    """Temporal activity wrapper for MarkRunFailedActivity."""
    activity_instance = MarkRunFailedActivity()
    await activity_instance.execute(input)
```

## Next Steps

1. **Migrate High-Value Activities First**: Start with most frequently used activities
2. **Add Tests**: Create comprehensive tests for migrated activities
3. **Monitor**: Watch for issues in production
4. **Document**: Update any activity-specific documentation
5. **Train**: Share migration guide with team

## Resources

- [Activity Interface Documentation](./ACTIVITY_INTERFACES.md)
- [Test Examples](../../../tests/temporal/interfaces/)
- [Refactored Activities](../../activities/test_activities_refactored.py)
