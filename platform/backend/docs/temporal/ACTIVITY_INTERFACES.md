# Temporal Activity Interfaces

## Overview

The Temporal Activity Interfaces provide a standardized framework for implementing Temporal activities following SOLID principles, particularly the **Liskov Substitution Principle**. This ensures that any activity can be swapped with another without breaking the workflow, as long as they implement the same interface.

## Architecture

```
IActivity (Interface)
    ↓
BaseActivity (Abstract Base Class)
    ↓
Concrete Activities (PrepareTestActivity, BrowserAutomationActivity, etc.)
```

## Key Components

### 1. Activity Interface (`activity_interface.py`)

Defines the contract that all activities must follow:

- **IActivity**: Base interface for all activities
- **ActivityInput**: Base class for activity inputs
- **ActivityOutput**: Base class for activity outputs
- **ActivityError**: Standardized error representation

### 2. Result Types (`activity_result_types.py`)

Standardized result types for consistent error handling:

- **ActivityResult**: Base result type
- **SuccessResult**: Successful execution
- **ErrorResult**: Failed execution with error details
- **TimeoutResult**: Timeout with partial results
- **ValidationErrorResult**: Input validation failures

### 3. Base Activity (`base_activity.py`)

Abstract base class providing common functionality:

- Input validation
- Error handling and classification
- Structured logging
- Metrics collection hooks
- Retry logic integration

### 4. Activity Factory (`activity_factory.py`)

Factory pattern for type-safe activity creation:

- Activity registration and discovery
- Singleton pattern support
- Dependency injection
- Activity decorator for automatic registration

## Creating a New Activity

### Step 1: Define Input/Output Types

```python
from app.temporal.interfaces import ActivityInput, ActivityOutput

@dataclass
class MyActivityInput(ActivityInput):
    """Input for MyActivity."""
    required_field: str
    optional_field: int = 0

@dataclass
class MyActivityOutput(ActivityOutput):
    """Output from MyActivity."""
    result_field: str
    status: str = "completed"
```

### Step 2: Implement Activity Class

```python
from app.temporal.interfaces import BaseActivity

class MyActivity(BaseActivity[MyActivityInput, MyActivityOutput]):
    """Activity description."""

    async def validate_input(self, input_data: MyActivityInput) -> bool:
        """Validate input."""
        await super().validate_input(input_data)

        if not input_data.required_field:
            raise ValueError("required_field is required")

        return True

    async def execute_impl(self, input_data: MyActivityInput) -> MyActivityOutput:
        """Execute activity logic."""
        # Your implementation here
        result = f"processed_{input_data.required_field}"

        return MyActivityOutput(
            result_field=result,
            status="completed",
        )
```

### Step 3: Create Temporal Activity Wrapper

```python
from temporalio import activity

@activity.defn
async def my_activity(input: MyActivityInput) -> MyActivityOutput:
    """Temporal activity wrapper."""
    activity_instance = MyActivity()
    return await activity_instance.execute(input)
```

### Step 4: Register Activity (Optional)

```python
from app.temporal.interfaces import register_activity

register_activity("MyActivity", MyActivity)
```

## Activity Lifecycle

```
1. Input Validation (validate_input)
    ↓
2. Log Start (log_start)
    ↓
3. Execute Implementation (execute_impl)
    ↓
4. Handle Errors (handle_error) - if exception occurs
    ↓
5. Log Complete (log_complete) - or log_error if failed
    ↓
6. Collect Metrics (collect_metrics)
```

## Error Handling

### Error Classification

Errors are automatically classified by type:

- **Not Retryable**: `ValidationError`, `ValueError`, `TypeError`, `TimeoutError`
- **Retryable**: `ConnectionError`, `OperationalError`

### Custom Error Handling

Override `handle_error()` for custom classification:

```python
async def handle_error(self, error: Exception, input_data: InputType) -> ActivityError:
    """Custom error handling."""
    error_type = error.__class__.__name__

    # Custom classification
    if "temporary" in str(error).lower():
        is_retryable = True
    elif "critical" in str(error).lower():
        is_retryable = False

    return ActivityError(
        error_type=error_type,
        error_message=str(error),
        is_retryable=is_retryable,
        context={"activity": self.get_activity_name()},
    )
```

## Logging

### Structured Logging

Activities use structured logging with consistent fields:

```python
{
    "event": "activity_start" | "activity_complete" | "activity_error",
    "activity_name": str,
    "activity_id": str,
    "correlation_id": str,
    "attempt": int,
    "timestamp": ISO datetime,
}
```

### Custom Logging

Override logging methods for custom behavior:

```python
def log_start(self, input_data: InputType) -> None:
    """Custom start logging."""
    extra_fields = {
        "custom_field": getattr(input_data, "custom_field", None),
    }
    self.get_logger().info(f"Starting {self.get_activity_name()}", extra=extra_fields)
```

## Metrics Collection

### Default Metrics

Base activities automatically collect:

- `activity_name`: Name of the activity
- `duration_ms`: Execution duration
- `timestamp`: Completion timestamp

### Custom Metrics

Override `collect_metrics()` for custom metrics:

```python
def collect_metrics(self, input_data: InputType, output_data: OutputType) -> Dict[str, Any]:
    """Collect custom metrics."""
    metrics = super().collect_metrics(input_data, output_data)

    metrics.update({
        "custom_metric": getattr(output_data, "custom_field", None),
        "input_size": len(str(input_data)),
    })

    return metrics
```

## Retry Logic

### Retry Decision

Override `should_retry()` to customize retry logic:

```python
def should_retry(self, error: ActivityError, attempt: int) -> bool:
    """Custom retry logic."""
    # Don't retry validation errors
    if error.error_type == "ValidationError":
        return False

    # Retry up to 5 times for temporary errors
    if "temporary" in error.error_message.lower():
        return attempt < 5

    # Default behavior
    return super().should_retry(error, attempt)
```

### Retry Delay

Override `get_retry_delay_seconds()` for custom delays:

```python
def get_retry_delay_seconds(self, error: ActivityError, attempt: int) -> int:
    """Custom retry delay."""
    # Longer delay for critical errors
    if "critical" in error.error_message.lower():
        return 120  # 2 minutes

    # Default exponential backoff
    return super().get_retry_delay_seconds(error, attempt)
```

## Testing

### Unit Tests

```python
@pytest.mark.asyncio
async def test_my_activity_success():
    """Test successful execution."""
    activity = MyActivity()
    input_data = MyActivityInput(required_field="test")

    output = await activity.execute(input_data)

    assert output.status == "completed"
    assert output.result_field == "processed_test"
```

### Mock Tests

```python
@pytest.mark.asyncio
async def test_my_activity_with_mock_db():
    """Test with mocked database."""
    activity = MyActivity()
    input_data = MyActivityInput(required_field="test")

    with patch('app.services.my_service.process') as mock_process:
        mock_process.return_value = "mock_result"

        output = await activity.execute(input_data)

        assert output.result_field == "processed_test"
        mock_process.assert_called_once()
```

## Migration Guide

### Migrating Existing Activities

**Before** (old style):

```python
@activity.defn
async def my_old_activity(input_data: dict) -> dict:
    """Old-style activity."""
    result = await process(input_data)
    return {"result": result}
```

**After** (new style):

```python
@dataclass
class MyActivityInput(ActivityInput):
    required_field: str

@dataclass
class MyActivityOutput(ActivityOutput):
    result_field: str

class MyActivity(BaseActivity[MyActivityInput, MyActivityOutput]):
    async def validate_input(self, input_data: MyActivityInput) -> bool:
        await super().validate_input(input_data)
        if not input_data.required_field:
            raise ValueError("required_field is required")
        return True

    async def execute_impl(self, input_data: MyActivityInput) -> MyActivityOutput:
        result = await process(input_data.required_field)
        return MyActivityOutput(result_field=result)

@activity.defn
async def my_activity(input: MyActivityInput) -> MyActivityOutput:
    """Temporal activity wrapper."""
    activity_instance = MyActivity()
    return await activity_instance.execute(input)
```

## Best Practices

### 1. Always Validate Input

```python
async def validate_input(self, input_data: InputType) -> bool:
    await super().validate_input(input_data)
    # Add custom validation
    return True
```

### 2. Use Specific Error Types

```python
# Good
raise ValueError("Invalid input: field cannot be empty")

# Avoid
raise Exception("Something went wrong")
```

### 3. Log Important Events

```python
self.get_logger().info(f"Processing {input_data.id}")
self.get_logger().error(f"Failed to process: {error}")
```

### 4. Collect Meaningful Metrics

```python
def collect_metrics(self, input_data, output_data) -> Dict[str, Any]:
    metrics = super().collect_metrics(input_data, output_data)
    metrics.update({
        "items_processed": output_data.processed_count,
        "success_rate": output_data.success_rate,
    })
    return metrics
```

### 5. Handle Errors Gracefully

```python
try:
    result = await risky_operation()
except SpecificError as e:
    # Handle specific error
    self.get_logger().warning(f"Specific error occurred: {e}")
    raise
except Exception as e:
    # Handle unexpected errors
    self.get_logger().error(f"Unexpected error: {e}", exc_info=True)
    raise
```

## Benefits

### 1. Liskov Substitution

Any activity implementing `IActivity` can be swapped with another:

```python
# Both work identically from workflow perspective
activity1 = PrepareTestActivity()
activity2 = AlternativePrepareActivity()  # Different implementation, same interface
```

### 2. Consistency

All activities follow the same patterns:
- Input validation
- Error handling
- Logging
- Metrics collection

### 3. Testability

Easy to test with consistent interfaces:

```python
# Mock input/output for testing
input_data = MyActivityInput(required_field="test")
output = await activity.execute(input_data)
assert output.status == "completed"
```

### 4. Maintainability

Clear patterns for new activities:
- Inherit from `BaseActivity`
- Implement required methods
- Follow lifecycle hooks

### 5. Observability

Consistent logging and metrics across all activities:
- Structured logs
- Standard metrics
- Error classification

## Examples

See refactored activities in `app/temporal/activities/test_activities_refactored.py`:

- `PrepareTestActivity`
- `BrowserAutomationActivity`
- `SaveResultsActivity`
- `MarkRunFailedActivity`

## Troubleshooting

### Activity Not Found

**Error**: `ValueError: Activity 'MyActivity' not registered`

**Solution**: Register the activity or use direct instantiation:

```python
# Option 1: Register
register_activity("MyActivity", MyActivity)

# Option 2: Direct instantiation
activity = MyActivity()
```

### Validation Fails

**Error**: `ValueError: Input validation failed`

**Solution**: Check validation logic and input requirements:

```python
async def validate_input(self, input_data: InputType) -> bool:
    await super().validate_input(input_data)
    # Add validation checks
    if not input_data.required_field:
        raise ValueError("required_field is required")
    return True
```

### Activity Not Retrying

**Error**: Activity fails but doesn't retry

**Solution**: Check error classification:

```python
async def handle_error(self, error: Exception, input_data: InputType) -> ActivityError:
    error_type = error.__class__.__name__
    is_retryable = error_type not in ["ValidationError", "TimeoutError"]

    return ActivityError(
        error_type=error_type,
        error_message=str(error),
        is_retryable=is_retryable,  # Must be True for retry
    )
```

## References

- [Temporal Python SDK Documentation](https://docs.temporal.io/dev-guide/python)
- [Activity Best Practices](https://docs.temporal.io/dev-guide/python/activities)
- [Error Handling](https://docs.temporal.io/dev-guide/python/activities#error-handling)
