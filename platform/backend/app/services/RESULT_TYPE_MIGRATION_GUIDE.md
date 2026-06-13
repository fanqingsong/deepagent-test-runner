# Result Type Migration Guide

## Overview

Core services have been migrated to use the new Result wrapper types for consistent error handling and type safety. This guide explains the changes and how to use the new Result-based methods.

## Migrated Services

### 1. ExecutionService (`execution_service.py`)

**New Result-based Methods:**

- `resolve_target_tests_v2()` → `ServiceSuccess[List[int]] | ServiceError`
- `create_test_run_v2()` → `ServiceSuccess[TestRun] | ServiceError`
- `update_run_status_v2()` → `ServiceSuccess[TestRun] | ServiceError`
- `save_test_results_v2()` → `ServiceSuccess[TestRun] | ServiceError`

**Legacy Methods (maintained for backward compatibility):**

- `resolve_target_tests()` → Returns `List[int]` directly
- `create_test_run()` → Returns `TestRun` directly
- `update_run_status()` → Returns `TestRun` directly
- `save_test_results()` → Returns `TestRun` directly

**Usage Example:**

```python
# New Result-based approach
result = await execution_service.create_test_run_v2(
    run_id="test-123",
    test_definition_ids=[10, 20],
    environment={},
    db=session
)

if result.is_success():
    test_run = result.get_data()
    metadata = result.metadata
    logger.info(f"Created test run with {metadata['test_count']} tests")
else:
    error = result.get_error()
    http_status = result.get_http_status()
    logger.error(f"Failed to create test run: {error}")
    # Handle error based on result.error_code
```

### 2. SuiteService (`suite_service.py`)

**New Result-based Methods:**

- `resolve_suite_entries_v2()` → `ServiceSuccess[List[Dict]] | ServiceError`
- `resolve_dynamic_suite_v2()` → `ServiceSuccess[List[Dict]] | ServiceError`
- `create_suite_run_v2()` → `ServiceSuccess[SuiteRun] | ServiceError`
- `get_suite_run_with_entries_v2()` → `ServiceSuccess[SuiteRun] | ServiceError`
- `cancel_suite_run_v2()` → `ServiceSuccess[SuiteRun] | ServiceError`

**Legacy Methods (maintained for backward compatibility):**

- `resolve_suite_entries()` → Returns `List[Dict]` directly
- `resolve_dynamic_suite()` → Returns `List[Dict]` directly
- `create_suite_run()` → Returns `SuiteRun` directly
- `get_suite_run_with_entries()` → Returns `SuiteRun` or `None`
- `cancel_suite_run()` → Returns `SuiteRun` directly

**Usage Example:**

```python
# New Result-based approach
result = await suite_service.create_suite_run_v2(
    suite_id=1,
    triggered_by="manual"
)

if result.is_success():
    suite_run = result.get_data()
    entry_count = result.metadata.get('entry_count', 0)
    logger.info(f"Created suite run with {entry_count} entries")
else:
    error = result.get_error()
    if result.error_code == "NOT_FOUND":
        logger.error("Suite not found")
    elif result.error_code == "VALIDATION_ERROR":
        logger.error(f"Validation error: {error}")
    else:
        logger.error(f"Failed to create suite run: {error}")
```

### 3. ScriptValidationService (`script_validation_service.py`)

**New Result-based Methods:**

- `validate_script_v2()` → `ServiceSuccess[Dict] | ServiceError`
- `validate_script_with_metadata_v2()` → `ServiceSuccess[Dict] | ServiceError`
- `determine_script_status_v2()` → `ServiceSuccess[str] | ServiceError`

**Legacy Methods (maintained for backward compatibility):**

- `validate_script()` → Returns `Dict` directly
- `validate_script_with_metadata()` → Returns `Dict` directly
- `determine_script_status()` → Returns `str` directly

**Usage Example:**

```python
# New Result-based approach
result = await validation_service.validate_script_v2(script, url="https://example.com")

if result.is_success():
    validation_data = result.get_data()
    status = validation_data.get('status')
    step_results = validation_data.get('step_results', [])
    logger.info(f"Validation passed: {status}")
else:
    error = result.get_error()
    if result.error_code == "VALIDATION_ERROR":
        logger.error(f"Script validation failed: {error}")
    elif result.error_code == "EXECUTION_ERROR":
        logger.error(f"Script execution failed: {error}")
```

## Error Codes and HTTP Status Mapping

All ServiceError results include proper error codes and HTTP status mappings:

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input or validation failure |
| `NOT_FOUND` | 404 | Resource not found |
| `EXECUTION_ERROR` | 500 | Script or execution failure |
| `CREATE_ERROR` | 500 | Database creation error |
| `UPDATE_ERROR` | 500 | Database update error |
| `SAVE_ERROR` | 500 | Database save error |
| `RESOLVE_ERROR` | 500 | Resolution error |
| `CANCEL_ERROR` | 500 | Cancellation error |
| `METADATA_ERROR` | 500 | Metadata processing error |
| `STATUS_ERROR` | 500 | Status determination error |

## Migration Strategy

### For New Code

Always use the `*_v2` Result-based methods:

```python
# ✅ Good - Use Result-based methods
result = await service.create_test_run_v2(...)
if result.is_success():
    data = result.get_data()
else:
    error = result.get_error()

# ❌ Avoid - Don't use legacy methods in new code
test_run = await service.create_test_run(...)
```

### For Existing Code

Legacy methods are maintained for backward compatibility. You can migrate gradually:

```python
# Phase 1: Keep legacy methods working
test_run = await service.create_test_run(...)

# Phase 2: Migrate to Result-based methods
result = await service.create_test_run_v2(...)
if result.is_success():
    test_run = result.get_data()
```

### Error Handling Patterns

#### 1. Success/Error Branching

```python
result = await service.some_method_v2(...)

if result.is_success():
    data = result.get_data()
    metadata = result.metadata
    # Handle success
else:
    error = result.get_error()
    error_code = result.error_code
    http_status = result.get_http_status()
    # Handle error
```

#### 2. Pattern Matching (Python 3.10+)

```python
match result:
    case ServiceSuccess(data=data, metadata=metadata):
        # Handle success
        pass
    case ServiceError(message=msg, error_code=code):
        # Handle error
        pass
```

#### 3. Early Return Pattern

```python
result = await service.some_method_v2(...)
if result.is_error():
    return result  # Propagate error

data = result.get_data()
# Continue with success path
```

#### 4. Chaining Operations

```python
# Chain multiple operations
create_result = await service.create_test_run_v2(...)
if create_result.is_error():
    return create_result

update_result = await service.update_run_status_v2(...)
if update_result.is_error():
    return update_result

# All operations succeeded
```

## Benefits of Result Types

1. **Type Safety**: Clear success/error types with proper type hints
2. **Consistent Error Handling**: All services use same error patterns
3. **Better Error Messages**: Structured error information with codes and details
4. **HTTP Mapping**: Built-in HTTP status code mapping for API responses
5. **Chainability**: Can chain service calls without exception handling
6. **Metadata**: Additional context in successful operations
7. **No Hidden Exceptions**: Errors are explicit, not thrown

## Testing

All Result-based methods have comprehensive tests:

```bash
# Run tests for Result type migration
pytest platform/backend/app/tests/services/test_execution_service_result_types.py
pytest platform/backend/app/tests/services/test_suite_service_result_types.py
pytest platform/backend/app/tests/services/test_script_validation_service_result_types.py
```

## Next Steps

1. **Migrate All Callers**: Update existing code to use Result-based methods
2. **Add Result Types to Other Services**: Apply same pattern to remaining services
3. **Update API Endpoints**: Use Result types in endpoint responses
4. **Documentation**: Update API docs with new error codes and responses
5. **Monitoring**: Track error codes in logging and metrics

## Common Patterns

### Repository Integration

```python
async def some_service_method(self, id: int) -> ServiceSuccess[Model] | ServiceError:
    try:
        entity = await self.repository.get_by_id(id)
        if not entity:
            return service_not_found("Entity", str(id))
        return service_success(entity)
    except Exception as e:
        return service_error(f"Operation failed: {str(e)}", "OPERATION_ERROR")
```

### Validation Integration

```python
async def validate_input(self, data: Dict) -> ServiceSuccess[Dict] | ServiceError:
    if not data.get("required_field"):
        return service_validation_error(
            "Missing required field",
            field_errors={"required_field": "This field is required"}
        )
    return service_success(data)
```

### API Endpoint Integration

```python
@router.post("/test-runs")
async def create_test_run(request: Request):
    result = await execution_service.create_test_run_v2(...)
    if result.is_error():
        return JSONResponse(
            status_code=result.get_http_status(),
            content=result.to_dict()
        )
    return JSONResponse(
        status_code=200,
        content={"data": result.get_data(), "metadata": result.metadata}
    )
```

## Troubleshooting

### Type Hints Not Working

Make sure to import the Result types:

```python
from app.core.simple_result_types import (
    ServiceSuccess, ServiceError,
    service_success, service_error
)
```

### Backward Compatibility Issues

Legacy methods are maintained. If you need to update legacy code, test thoroughly:

```python
# Old code
test_run = await service.create_test_run(...)

# New code
result = await service.create_test_run_v2(...)
test_run = result.get_data() if result.is_success() else None
```

### Error Code Mismatches

Check the error code mappings in `simple_result_types.py`:

```python
SERVICE_ERROR_HTTP_STATUS_MAP: Dict[str, int] = {
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    # ... more mappings
}
```

## Summary

The Result type migration provides:

- ✅ Consistent error handling across services
- ✅ Type-safe success/error returns
- ✅ Better error messages with codes and HTTP mapping
- ✅ Backward compatibility with legacy methods
- ✅ Comprehensive test coverage
- ✅ Clear migration path for existing code

All new code should use the `*_v2` Result-based methods, while existing code can migrate gradually at its own pace.
