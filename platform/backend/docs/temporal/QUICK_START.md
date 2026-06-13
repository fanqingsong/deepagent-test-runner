# Quick Start: Activity Interface Standardization

## 5-Minute Guide

This guide gets you started with the new activity interface system in 5 minutes.

## What is This?

A standardized system for Temporal activities that ensures:
- **Consistency**: All activities work the same way
- **Testability**: Easy to test with consistent interfaces
- **Maintainability**: Clear patterns for new activities
- **Observability**: Consistent logging and metrics

## Basic Pattern

### 1. Define Input/Output

```python
from app.temporal.interfaces import ActivityInput, ActivityOutput

@dataclass
class MyActivityInput(ActivityInput):
    required_field: str
    optional_field: int = 0

@dataclass
class MyActivityOutput(ActivityOutput):
    result: str
```

### 2. Implement Activity

```python
from app.temporal.interfaces import BaseActivity

class MyActivity(BaseActivity[MyActivityInput, MyActivityOutput]):
    async def validate_input(self, input_data: MyActivityInput) -> bool:
        """Validate input."""
        await super().validate_input(input_data)
        if not input_data.required_field:
            raise ValueError("required_field is required")
        return True

    async def execute_impl(self, input_data: MyActivityInput) -> MyActivityOutput:
        """Execute logic."""
        result = f"processed_{input_data.required_field}"
        return MyActivityOutput(result=result)
```

### 3. Create Wrapper

```python
from temporalio import activity

@activity.defn
async def my_activity(input: MyActivityInput) -> MyActivityOutput:
    """Temporal activity wrapper."""
    activity_instance = MyActivity()
    return await activity_instance.execute(input)
```

That's it! Your activity now has:
- ✅ Input validation
- ✅ Error handling
- ✅ Structured logging
- ✅ Metrics collection
- ✅ Retry support

## Complete Example

```python
"""Complete activity example."""
from app.temporal.interfaces import BaseActivity, ActivityInput, ActivityOutput
from temporalio import activity
from dataclasses import dataclass

@dataclass
class ProcessDataInput(ActivityInput):
    data: str
    mode: str = "default"

@dataclass
class ProcessDataOutput(ActivityOutput):
    processed_data: str
    items_count: int = 0

class ProcessDataActivity(BaseActivity[ProcessDataInput, ProcessDataOutput]):
    """Activity for processing data."""

    async def validate_input(self, input_data: ProcessDataInput) -> bool:
        """Validate input."""
        await super().validate_input(input_data)

        if not input_data.data:
            raise ValueError("data is required")

        if input_data.mode not in ["default", "advanced"]:
            raise ValueError("mode must be 'default' or 'advanced'")

        return True

    async def execute_impl(self, input_data: ProcessDataInput) -> ProcessDataOutput:
        """Execute data processing."""
        # Your logic here
        processed = f"processed_{input_data.data}"
        items = len(input_data.data)

        self.get_logger().info(f"Processed {items} items in {input_data.mode} mode")

        return ProcessDataOutput(
            processed_data=processed,
            items_count=items,
        )

@activity.defn
async def process_data(input: ProcessDataInput) -> ProcessDataOutput:
    """Temporal activity wrapper."""
    activity_instance = ProcessDataActivity()
    return await activity_instance.execute(input)
```

## Testing Your Activity

```python
"""Test your activity."""
import pytest
from app.temporal.activities.my_activity import ProcessDataActivity, ProcessDataInput

@pytest.mark.asyncio
async def test_process_data_success():
    """Test successful processing."""
    activity = ProcessDataActivity()
    input_data = ProcessDataInput(data="test_data", mode="default")

    output = await activity.execute(input_data)

    assert output.processed_data == "processed_test_data"
    assert output.items_count == 8  # len("test_data")

@pytest.mark.asyncio
async def test_process_data_validation():
    """Test input validation."""
    activity = ProcessDataActivity()
    input_data = ProcessDataInput(data="")  # Empty data

    with pytest.raises(ValueError, match="data is required"):
        await activity.execute(input_data)
```

## Using in Workflows

```python
"""Use in your workflow."""
from temporalio import workflow
from app.temporal.activities.my_activity import process_data, ProcessDataInput

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        """Run workflow."""
        output = await workflow.execute_activity(
            process_data,
            ProcessDataInput(data=data),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return output.processed_data
```

## Advanced Features

### Custom Error Handling

```python
async def handle_error(self, error: Exception, input_data: InputType) -> ActivityError:
    """Custom error handling."""
    # Classify error as retryable or not
    is_retryable = "temporary" in str(error).lower()

    return ActivityError(
        error_type=error.__class__.__name__,
        error_message=str(error),
        is_retryable=is_retryable,
    )
```

### Custom Metrics

```python
def collect_metrics(self, input_data: InputType, output_data: OutputType) -> Dict[str, Any]:
    """Collect custom metrics."""
    metrics = super().collect_metrics(input_data, output_data)

    metrics.update({
        "data_size": len(input_data.data),
        "processing_mode": input_data.mode,
    })

    return metrics
```

### Custom Retry Logic

```python
def should_retry(self, error: ActivityError, attempt: int) -> bool:
    """Custom retry logic."""
    # Don't retry validation errors
    if error.error_type == "ValidationError":
        return False

    # Retry other errors up to 5 times
    return attempt < 5
```

## Common Patterns

### Database Activity

```python
async def execute_impl(self, input_data: InputType) -> OutputType:
    """Execute with database."""
    async def _process(db: AsyncSession) -> OutputType:
        result = await db.execute(query)
        return OutputType(data=result.scalar())

    return await run_with_session(_process)
```

### External API Activity

```python
async def execute_impl(self, input_data: InputType) -> OutputType:
    """Execute with external API."""
    client = ExternalServiceClient()
    result = await client.call(input_data.params)
    return OutputType(data=result)
```

### File Processing Activity

```python
async def execute_impl(self, input_data: InputType) -> OutputType:
    """Execute file processing."""
    with open(input_data.file_path, 'r') as f:
        content = f.read()

    processed = process_content(content)

    return OutputType(data=processed)
```

## Migration from Old Activities

**Before**:

```python
@activity.defn
async def old_activity(input: dict) -> dict:
    result = process(input["data"])
    return {"result": result}
```

**After**:

```python
@dataclass
class OldActivityInput(ActivityInput):
    data: str

@dataclass
class OldActivityOutput(ActivityOutput):
    result: str

class OldActivity(BaseActivity[OldActivityInput, OldActivityOutput]):
    async def validate_input(self, input_data: OldActivityInput) -> bool:
        await super().validate_input(input_data)
        if not input_data.data:
            raise ValueError("data is required")
        return True

    async def execute_impl(self, input_data: OldActivityInput) -> OldActivityOutput:
        result = process(input_data.data)
        return OldActivityOutput(result=result)

@activity.defn
async def old_activity(input: OldActivityInput) -> OldActivityOutput:
    activity_instance = OldActivity()
    return await activity_instance.execute(input)
```

## Checklist

Before using your activity:

- [ ] Input class extends `ActivityInput`
- [ ] Output class extends `ActivityOutput`
- [ ] Activity class extends `BaseActivity`
- [ ] `validate_input()` implemented
- [ ] `execute_impl()` implemented
- [ ] Wrapper function created
- [ ] Tests written
- [ ] Documentation updated

## Resources

- [Full Documentation](./ACTIVITY_INTERFACES.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
- [Examples](../../../tests/temporal/interfaces/)
- [Reference Implementation](../../activities/test_activities_refactored.py)

## Troubleshooting

**Problem**: Activity not found
```python
# Solution: Register activity
from app.temporal.interfaces import register_activity
register_activity("MyActivity", MyActivity)
```

**Problem**: Validation fails
```python
# Solution: Check validate_input()
async def validate_input(self, input_data: InputType) -> bool:
    await super().validate_input(input_data)  # Don't forget this!
    # Your validation
    return True
```

**Problem**: Activity not retrying
```python
# Solution: Check error classification
async def handle_error(self, error: Exception, input_data: InputType) -> ActivityError:
    return ActivityError(
        error_type=error.__class__.__name__,
        error_message=str(error),
        is_retryable=True,  # Must be True for retry
    )
```

## Next Steps

1. **Read Full Docs**: See [ACTIVITY_INTERFACES.md](./ACTIVITY_INTERFACES.md)
2. **Check Examples**: Look at [test_activities_refactored.py](../../activities/test_activities_refactored.py)
3. **Write Tests**: Create tests for your activity
4. **Migrate**: Migrate existing activities using [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)

## Need Help?

- Check the examples in the refactored activities
- Review the test files
- Read the full documentation
- Examine the reference implementations
