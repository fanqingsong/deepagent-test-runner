# Result Wrapper Types - Complete Guide

## Overview

This guide covers the standardized result wrapper types system for consistent service responses following SOLID principles.

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Result Types](#basic-result-types)
3. [Service Result Types](#service-result-types)
4. [Result Helpers](#result-helpers)
5. [Result Builders](#result-builders)
6. [Usage Patterns](#usage-patterns)
7. [Migration Guide](#migration-guide)
8. [Best Practices](#best-practices)
9. [API Reference](#api-reference)

## Introduction

### Problem Statement

Services previously returned inconsistent types:
- Some returned model objects directly
- Some returned tuples
- Some returned dicts
- Error handling varied
- No consistent pattern for success/error/timeout

### Solution

Standardized result wrapper types provide:
- **Consistency**: All services return consistent types
- **Type Safety**: Strong typing for result handling
- **Error Handling**: Explicit error types and handling
- **Chainability**: Functional composition patterns
- **Testability**: Easy to test success/error scenarios
- **API Integration**: Easy HTTP response mapping

### Architecture

```
Result Types System
├── Base Result Types (result_types.py)
│   ├── Result (abstract base)
│   ├── Success[T]
│   ├── Error[E]
│   ├── Timeout
│   └── ValidationError
├── Service Result Types (service_result_types.py)
│   ├── ServiceResult (base)
│   ├── ServiceSuccess[T]
│   ├── ServiceError[E]
│   ├── DatabaseError
│   ├── NotFoundError
│   ├── ConflictError
│   └── Specialized errors
├── Result Helpers (result_helpers.py)
│   ├── Factory functions
│   ├── Type guards
│   ├── Data extraction
│   └── Transformation
└── Result Builders (result_builders.py)
    ├── ResultBuilder
    ├── ServiceResultBuilder
    ├── ErrorResponseBuilder
    └── ValidationBuilder
```

## Basic Result Types

### Success

Represents successful operation results.

```python
from app.core.result_types import Success

# Create success with data
result = Success({"user_id": 123, "email": "test@example.com"})

# Check success status
if result.is_success():
    data = result.get_data()

# Chain operations
result = Success(5).map(lambda x: x * 2)  # Success(10)

# Pattern matching
if isinstance(result, Success):
    value = result.data
```

### Error

Represents failed operation results.

```python
from app.core.result_types import Error

# Create error with message
result = Error("Operation failed")

# Create error with code and details
result = Error(
    "Database connection failed",
    code="DB_ERROR",
    details={"retry_after": 30}
)

# Check error status
if result.is_error():
    message = result.get_error_message()

# Add details
enhanced = result.add_detail("connection_string", "postgresql://...")

# Error propagates through operations
result.map(lambda x: x * 2)  # Still Error("Operation failed")
```

### Timeout

Represents operation timeout scenarios.

```python
from app.core.result_types import Timeout

# Create timeout with default message
result = Timeout()

# Create timeout with custom information
result = Timeout(
    message="API call timed out",
    timeout_seconds=30.0,
    details={"endpoint": "/api/v1/users"}
)

# Check for timeout
if result.is_timeout():
    logger.warning(f"Operation timed out after {result.timeout_seconds}s")
```

### ValidationError

Represents input validation failures with field-level errors.

```python
from app.core.result_types import ValidationError

# Create validation error with field errors
result = ValidationError(
    "User validation failed",
    errors={
        "email": ["Invalid format", "Already registered"],
        "age": ["Must be positive", "Must be over 18"]
    }
)

# Add field errors dynamically
result = (ValidationError()
          .add_field_error("email", "Invalid format")
          .add_field_error("name", "Required"))

# Check for validation errors
if result.is_validation_error():
    for field, errors in result.errors.items():
        print(f"{field}: {', '.join(errors)}")
```

## Service Result Types

### ServiceSuccess

Enhanced success result with service context.

```python
from app.core.service_result_types import ServiceSuccess

# Create service success
result = ServiceSuccess(
    data={"test_id": 123, "status": "passed"},
    service_name="ExecutionService",
    operation_name="create_test_run",
    metadata={"duration_ms": 1500}
)

# Access service context
print(result.service_name)  # "ExecutionService"
print(result.operation_name)  # "create_test_run"

# Add metadata
result = result.with_metadata(
    retry_count=0,
    executed_at="2024-01-01T00:00:00Z"
)

# Get HTTP status
status = result.get_http_status()  # 200
```

### ServiceError

Enhanced error result with error codes and HTTP mapping.

```python
from app.core.service_result_types import ServiceError, ErrorCode

# Create service error
result = ServiceError(
    message="Database connection failed",
    error_code=ErrorCode.DATABASE_ERROR,
    service_name="ExecutionService",
    operation_name="save_test_results"
)

# Get HTTP status
status = result.get_http_status()  # 500

# Add details
result = result.with_detail("connection_string", "postgresql://...")
result = result.with_detail("retry_attempts", 3)

# Convert to HTTP response
from app.core.result_helpers import to_http_response
response = to_http_response(result)
# {
#     "success": false,
#     "status": 500,
#     "error": {
#         "message": "Database connection failed",
#         "code": "DATABASE_ERROR"
#     }
# }
```

### Specialized Service Errors

#### NotFoundError
```python
from app.core.service_result_types import NotFoundError

result = NotFoundError("TestDefinition", "test-123")
# message: "TestDefinition not found: test-123"
# http_status: 404
```

#### ConflictError
```python
from app.core.service_result_types import ConflictError

result = ConflictError(
    "Test run already exists",
    conflicting_resource="run-123"
)
# http_status: 409
```

#### DatabaseError
```python
from app.core.service_result_types import DatabaseError

result = DatabaseError(
    "Failed to execute query",
    error_code=ErrorCode.DATABASE_QUERY_ERROR,
    details={"query": "SELECT * FROM users WHERE id = $1"}
)
```

#### PermissionError
```python
from app.core.service_result_types import PermissionError

result = PermissionError(
    "Insufficient permissions",
    required_permission="test:execute"
)
# http_status: 403
```

#### TestExecutionError
```python
from app.core.service_result_types import TestExecutionError

result = TestExecutionError(
    "Script validation failed",
    test_id="test-123",
    execution_stage="validation"
)
```

## Result Helpers

### Factory Functions

Quick creation of common result types.

```python
from app.core.result_helpers import (
    success, error, timeout, validation_error,
    service_success, service_error, not_found, conflict
)

# Basic results
success({"id": 123})
error("Operation failed")
timeout(timeout_seconds=30.0)
validation_error(errors={"email": ["Invalid"]})

# Service results
service_success(data={"id": 123}, service_name="UserService")
service_error("Failed", ErrorCode.OPERATION_FAILED)
not_found("TestDefinition", "test-123")
conflict("Resource already exists", "resource-123")
```

### Type Guards

Type-safe result checking.

```python
from app.core.result_helpers import is_success, is_error, is_timeout

result = Success(42)

if is_success(result):
    # Type narrowed to Success
    value = result.data  # int
    print(f"Success: {value}")

if is_error(result):
    # Type narrowed to Error
    message = result.message  # str
    print(f"Error: {message}")
```

### Data Extraction

Safe data extraction with defaults.

```python
from app.core.result_helpers import get_data, get_error, get_or_raise

result = Success(42)

# Get data or default
value = get_data(result, default=0)  # 42

# Get error message or default
error_msg = get_error(result, default="No error")  # "No error"

# Get data or raise exception
try:
    value = get_or_raise(result)  # 42
except ValueError as e:
    print(f"Failed: {e}")
```

### Transformation

Functional transformation of results.

```python
from app.core.result_helpers import map_result, filter_result

result = Success(5)

# Map success data
doubled = map_result(result, lambda x: x * 2)  # Success(10)

# Filter success data
positive = filter_result(
    Success(42),
    lambda x: x > 0,
    "Must be positive"
)  # Success(42)

# Error propagates through transformations
error_result = Error("Failed")
mapped_error = map_result(error_result, lambda x: x * 2)  # Still Error("Failed")
```

### Aggregation

Combine multiple results.

```python
from app.core.result_helpers import combine_results, sequence_results

# Combine results
results = combine_results(
    Success(1),
    Success(2),
    Success(3)
)  # Success([1, 2, 3])

# Any error causes failure
results = combine_results(
    Success(1),
    Error("Failed"),
    Success(3)
)  # Error("Multiple operations failed: 1 errors")

# Sequence results
result_list = [Success(1), Success(2), Success(3)]
sequenced = sequence_results(result_list)  # Success([1, 2, 3])
```

### Exception Handling

Convert exceptions to error results.

```python
from app.core.result_helpers import catch_exception, async_catch_exception

# Sync exception handling
def risky_operation():
    raise ValueError("Something went wrong")

result = catch_exception(
    risky_operation,
    error_message="Operation failed",
    error_code=ErrorCode.INTERNAL_ERROR
)  # ServiceError("Operation failed: Something went wrong")

# Async exception handling
async def async_risky_operation():
    raise ValueError("Async error")

result = await async_catch_exception(
    async_risky_operation,
    error_message="Async operation failed",
    error_code=ErrorCode.INTERNAL_ERROR
)
```

### Decorators

Automatic exception handling for functions.

```python
from app.core.result_helpers import result_decorator, async_result_decorator

@result_decorator("Calculation failed", ErrorCode.INTERNAL_ERROR)
def calculate(x, y):
    return x / y

result = calculate(10, 2)  # Success(5.0)
result = calculate(10, 0)  # ServiceError("Calculation failed: division by zero")

@async_result_decorator("Async operation failed")
async def fetch_data():
    await asyncio.sleep(0.1)
    return {"data": "value"}

result = await fetch_data()  # ServiceSuccess(data={"data": "value"})
```

## Result Builders

### ResultBuilder

Fluent construction of basic results.

```python
from app.core.result_builders import ResultBuilder

# Build success
result = (ResultBuilder()
          .with_data(42)
          .build())  # Success(42)

# Build error
result = (ResultBuilder()
          .with_error("Operation failed", code="OP_FAILED")
          .build())  # Error("Operation failed", code="OP_FAILED")

# Build with validation
result = (ResultBuilder()
          .add_validator(lambda x: x > 0, "Must be positive")
          .with_data(42)
          .build())  # Success(42)

# Build with transformation
result = (ResultBuilder()
          .add_transformer(lambda x: x * 2)
          .with_data(21)
          .build())  # Success(42)

# Build timeout
result = (ResultBuilder()
          .with_timeout(timeout_seconds=30.0)
          .build())  # Timeout(timeout_seconds=30.0)

# Build validation error
result = (ResultBuilder()
          .with_validation_error()
          .add_field_error("email", "Invalid format")
          .add_field_error("age", "Must be positive")
          .build())  # ValidationError(errors={"email": ["Invalid format"], ...})
```

### ServiceResultBuilder

Fluent construction of service results.

```python
from app.core.result_builders import ServiceResultBuilder

# Build service success
result = (ServiceResultBuilder()
          .with_service("ExecutionService")
          .with_operation("create_test_run")
          .with_data({"run_id": "test-123", "status": "running"})
          .with_metadata(duration_ms=1500, retry_count=0)
          .build())  # ServiceSuccess(data={...}, service_name="ExecutionService")

# Build service error
result = (ServiceResultBuilder()
          .with_service("ExecutionService")
          .with_error("Failed to create test run", ErrorCode.OPERATION_FAILED)
          .add_detail("error_code", "VALIDATION_FAILED")
          .build())  # ServiceError(message="Failed to create test run", ...)

# Build not found error
result = (ServiceResultBuilder()
          .with_service("TestDefinitionService")
          .with_not_found("TestDefinition", "test-123")
          .build())  # NotFoundError(resource="TestDefinition", identifier="test-123")
```

### ErrorResponseBuilder

Build detailed HTTP error responses.

```python
from app.core.result_builders import ErrorResponseBuilder

# Build error response
response = (ErrorResponseBuilder()
            .with_message("Validation failed")
            .with_code("VALIDATION_ERROR")
            .with_status(400)
            .add_field_error("email", "Invalid format")
            .add_field_error("age", "Must be positive")
            .add_suggestion("Check email format")
            .add_suggestion("Verify age is positive")
            .with_documentation_url("https://docs.example.com/errors")
            .build())

# {
#     "error": true,
#     "message": "Validation failed",
#     "code": "VALIDATION_ERROR",
#     "status": 400,
#     "field_errors": {
#         "email": ["Invalid format"],
#         "age": ["Must be positive"]
#     },
#     "suggestions": [
#         "Check email format",
#         "Verify age is positive"
#     ],
#     "documentation_url": "https://docs.example.com/errors"
# }

# Build from service error
from app.core.service_result_types import NotFoundError
service_error = NotFoundError("TestDefinition", "test-123")

response = (ErrorResponseBuilder()
            .from_service_error(service_error)
            .add_suggestion("Check test definition ID")
            .build())
```

### ValidationBuilder

Build complex validation results.

```python
from app.core.result_builders import ValidationBuilder

# Build validation result
result = (ValidationBuilder()
          .with_message("User validation failed")
          .add_field_error("email", "Invalid format")
          .add_field_error("email", "Already registered")
          .add_field_error("age", "Must be positive")
          .add_global_error("Password confirmation required")
          .add_warning("Email will be verified")
          .build())  # ValidationError(message="User validation failed", errors={...})

# Check for errors
builder = ValidationBuilder()
builder.add_field_error("email", "Invalid")

if builder.has_errors():
    result = builder.build()
    # Handle validation error
```

### BulkOperationBuilder

Build bulk operation results.

```python
from app.core.result_builders import BulkOperationBuilder

# Build bulk result
result = (BulkOperationBuilder()
          .add_success({"id": 1, "status": "created"})
          .add_success({"id": 2, "status": "created"})
          .add_error("Failed to create item 3")
          .add_success({"id": 4, "status": "created"})
          .build())  # BulkServiceResult(total_items=4, successful_items=3, failed_items=1)

# Access bulk statistics
print(f"Total: {result.total_items}")
print(f"Success: {result.successful_items}")
print(f"Failed: {result.failed_items}")
print(f"Success rate: {result.successful_items / result.total_items}")

# Build as regular result
result = (BulkOperationBuilder()
          .add_success()
          .add_error("Failed")
          .build_result())  # Error if any failures
```

## Usage Patterns

### Pattern 1: Service Layer Success Flow

```python
from app.core.service_result_types import ServiceSuccess, ServiceError, ErrorCode
from app.core.result_helpers import service_success, service_error

def create_user(user_data: dict) -> ServiceSuccess:
    """Create user with validation."""
    # Validate input
    if not user_data.get("email"):
        return service_error(
            "Email is required",
            ErrorCode.VALIDATION_ERROR,
            service_name="UserService",
            operation_name="create_user"
        )

    if "@" not in user_data["email"]:
        return service_error(
            "Invalid email format",
            ErrorCode.VALIDATION_ERROR,
            service_name="UserService",
            operation_name="create_user"
        )

    # Create user
    try:
        created_user = {"id": 123, **user_data}
        return service_success(
            data=created_user,
            service_name="UserService",
            operation_name="create_user",
            metadata={"created_at": "2024-01-01T00:00:00Z"}
        )
    except Exception as e:
        return service_error(
            f"Failed to create user: {str(e)}",
            ErrorCode.INTERNAL_ERROR,
            service_name="UserService",
            operation_name="create_user"
        )
```

### Pattern 2: Chained Operations

```python
def process_test_run(run_id: str) -> ServiceResult:
    """Process test run with chained operations."""
    # Step 1: Validate input
    validation_result = validate_run_id(run_id)
    if validation_result.is_error():
        return validation_result

    # Step 2: Load test run
    run_result = load_test_run(run_id)
    if run_result.is_error():
        return run_result

    test_run = run_result.get_data()

    # Step 3: Execute tests
    execution_result = execute_tests(test_run)
    if execution_result.is_error():
        return execution_result

    # Step 4: Save results
    save_result = save_test_results(run_id, execution_result.get_data())
    return save_result
```

### Pattern 3: Error Propagation

```python
from app.core.result_helpers import map_result, flat_map_result

def process_user_data(data: dict) -> ServiceResult:
    """Process user data with error propagation."""
    # Validate
    validated = validate_user(data)
    if validated.is_error():
        return validated

    # Transform (errors propagate automatically)
    transformed = map_result(validated, normalize_user_data)
    if transformed.is_error():
        return transformed

    # Save (flat_map allows returning ServiceResult)
    saved = flat_map_result(transformed, save_user_to_db)
    return saved
```

### Pattern 4: Aggregation

```python
from app.core.result_helpers import combine_results

def execute_bulk_tests(test_ids: List[str]) -> ServiceResult:
    """Execute multiple tests and aggregate results."""
    # Execute all tests
    results = [execute_test(test_id) for test_id in test_ids]

    # Combine results
    combined = combine_results(*results)

    if combined.is_success():
        test_data = combined.get_data()
        return service_success(
            data={"executed": len(test_data), "results": test_data},
            service_name="TestExecutionService"
        )
    else:
        return service_error(
            "Bulk test execution failed",
            ErrorCode.TEST_EXECUTION_ERROR,
            details={"failed_count": sum(1 for r in results if r.is_error())}
        )
```

### Pattern 5: Pattern Matching

```python
from app.core.result_types import match

def handle_result(result: Result) -> str:
    """Handle result with pattern matching."""
    return match(
        result,
        (Success, lambda r: f"Success: {r.get_data()}"),
        (Error, lambda r: f"Error: {r.get_error_message()}"),
        (Timeout, lambda r: f"Timeout: {r.timeout_seconds}s"),
        (ValidationError, lambda r: f"Validation: {r.errors}")
    )
```

## Migration Guide

### Phase 1: Add Result Types (No Breaking Changes)

```python
# Existing service methods still work
class ExecutionService:
    async def resolve_target_tests(self, schedule, db) -> List[int]:
        """Backward compatible method."""
        test_ids = await self.schedule_resolver.resolve_schedule(schedule, db)
        return test_ids

# New result-based methods added alongside
class ExecutionServiceWithResults:
    async def resolve_target_tests_result(self, schedule, db) -> ServiceSuccess[List[int]]:
        """New result-based method."""
        test_ids = await self.schedule_resolver.resolve_schedule(schedule, db)
        return service_success(data=test_ids, service_name="ExecutionService")
```

### Phase 2: Gradual Migration

```python
# Mix old and new styles during migration
async def execute_scheduled_test(schedule: Schedule, db: AsyncSession):
    service = ExecutionServiceWithResults(db_session=db)

    # Use new result-based methods where beneficial
    test_ids_result = await service.resolve_target_tests_result(schedule, db)

    if test_ids_result.is_error():
        logger.error(f"Failed to resolve tests: {test_ids_result.get_error_message()}")
        return None

    test_definition_ids = test_ids_result.get_data()

    # Use old style for now, migrate later
    environment = service.build_environment(schedule)
```

### Phase 3: Complete Migration

```python
# All methods use result types
async def execute_scheduled_test(schedule: Schedule, db: AsyncSession):
    service = ExecutionServiceWithResults(db_session=db)

    # All operations use result types
    test_ids_result = await service.resolve_target_tests_result(schedule, db)
    if test_ids_result.is_error():
        return test_ids_result

    env_result = service.build_environment_result(schedule)
    if env_result.is_error():
        return env_result

    run_result = await service.create_test_run_result(
        run_id="test-123",
        test_definition_ids=test_ids_result.get_data(),
        environment=env_result.get_data(),
        db=db
    )

    return run_result
```

## Best Practices

### DO ✅

1. **Use result types for all service operations**
   ```python
   async def create_user(data: dict) -> ServiceSuccess[User]:
       return service_success(data=created_user, service_name="UserService")
   ```

2. **Provide meaningful error messages**
   ```python
   return service_error(
       "Failed to connect to database: connection timeout",
       ErrorCode.DATABASE_CONNECTION_ERROR
   )
   ```

3. **Use specialized error types**
   ```python
   return not_found("TestDefinition", test_id)
   return conflict("Test run already exists", run_id)
   ```

4. **Chain operations for complex logic**
   ```python
   result = (Success(input_data)
             .map(validate)
             .flat_map(process)
             .map(save))
   ```

5. **Add metadata for debugging**
   ```python
   return service_success(
       data=result,
       service_name="TestService",
       operation_name="execute_test",
       metadata={"duration_ms": 1500, "retry_count": 0}
   )
   ```

### DON'T ❌

1. **Don't return raw exceptions from services**
   ```python
   # Bad
   async def create_user(data):
       raise ValueError("Invalid email")

   # Good
   async def create_user(data):
       return service_error("Invalid email", ErrorCode.VALIDATION_ERROR)
   ```

2. **Don't mix result types with raw returns**
   ```python
   # Bad
   async def get_user(user_id: int) -> Union[User, ServiceError]:
       if user_id < 0:
           return service_error("Invalid ID")
       return user  # Returns User, not ServiceSuccess

   # Good
   async def get_user(user_id: int) -> ServiceResult:
       if user_id < 0:
           return service_error("Invalid ID")
       return service_success(data=user)
   ```

3. **Don't ignore error handling**
   ```python
   # Bad
   result = await service.create_user(data)
   user = result.get_data()  # Crashes if result is error

   # Good
   result = await service.create_user(data)
   if result.is_success():
       user = result.get_data()
   else:
       handle_error(result)
   ```

## API Reference

### Result Types Module

#### Classes

- `Result` - Abstract base class for all results
- `Success[T]` - Success result with data of type T
- `Error[E]` - Error result with error details
- `Timeout` - Timeout result with duration information
- `ValidationError` - Validation error with field-level errors

#### Functions

- `is_success(result: Result) -> bool` - Type guard for Success
- `is_error(result: Result) -> bool` - Type guard for errors
- `is_timeout(result: Result) -> bool` - Type guard for Timeout
- `is_validation_error(result: Result) -> bool` - Type guard for ValidationError
- `fold(result, on_success, on_error) -> T` - Fold result to single value
- `match(result, *cases) -> Optional[T]` - Pattern matching for results
- `combine_results(*results) -> Result` - Combine multiple results
- `sequence_results(results: List[Result]) -> Result[List]` - Sequence results

### Service Result Types Module

#### Classes

- `ServiceResult` - Base class for service results
- `ServiceSuccess[T]` - Service success with context
- `ServiceError[E]` - Service error with codes
- `DatabaseError` - Database operation error
- `NotFoundError` - Resource not found error
- `ConflictError` - Resource conflict error
- `ServiceValidationError` - Input validation error
- `PermissionError` - Permission denied error
- `TestExecutionError` - Test execution error
- `BulkServiceResult` - Bulk operation result

#### Enums

- `ErrorCode` - Standard error codes
- `HTTPStatusMap` - Maps error codes to HTTP status

### Result Helpers Module

#### Factory Functions

- `success(data) -> Success` - Create success result
- `error(message, code, details) -> Error` - Create error result
- `timeout(message, timeout_seconds, details) -> Timeout` - Create timeout result
- `validation_error(message, errors) -> ValidationError` - Create validation error
- `service_success(data, **context) -> ServiceSuccess` - Create service success
- `service_error(message, error_code, **context) -> ServiceError` - Create service error
- `not_found(resource, identifier) -> NotFoundError` - Create not found error
- `conflict(message, conflicting_resource) -> ConflictError` - Create conflict error
- `database_error(message, **context) -> DatabaseError` - Create database error
- `permission_error(message, required_permission) -> PermissionError` - Create permission error
- `test_execution_error(message, **context) -> TestExecutionError` - Create test execution error

#### Type Guards

- `is_success(result: Result) -> bool` - Check if success
- `is_error(result: Result) -> bool` - Check if error
- `is_timeout(result: Result) -> bool` - Check if timeout
- `is_validation_error(result: Result) -> bool` - Check if validation error

#### Data Extraction

- `get_data(result: Result, default) -> Any` - Extract data or default
- `get_error(result: Result, default) -> Optional[str]` - Extract error or default
- `get_or_raise(result: Result, exception) -> Any` - Extract data or raise

#### Transformation

- `map_result(result, func) -> Result` - Apply function to result
- `flat_map_result(result, func) -> Result` - Apply result-returning function
- `filter_result(result, predicate, error_message) -> Result` - Filter result

#### Aggregation

- `combine_results(*results) -> Result` - Combine multiple results
- `sequence_results(results: List[Result]) -> Result[List]` - Sequence results
- `all_success(*results) -> bool` - Check if all results are success
- `any_success(*results) -> bool` - Check if any result is success

#### Exception Handling

- `catch_exception(func, **context) -> ServiceResult` - Convert exceptions to errors
- `async_catch_exception(func, **context) -> ServiceResult` - Async exception handling
- `result_decorator(error_message, error_code)` - Decorator for exception handling
- `async_result_decorator(error_message, error_code)` - Async decorator

#### Conversion

- `to_http_response(result: ServiceResult) -> Dict` - Convert to HTTP response
- `from_exception(exception, **context) -> ServiceError` - Convert exception to error

### Result Builders Module

#### Classes

- `ResultBuilder` - Builder for basic results
- `ServiceResultBuilder` - Builder for service results
- `ErrorResponseBuilder` - Builder for HTTP error responses
- `ValidationBuilder` - Builder for validation results
- `BulkOperationBuilder` - Builder for bulk operations

## Quick Reference

### Creating Results

```python
# Basic results
Success(data)
Error(message, code, details)
Timeout(message, timeout_seconds)
ValidationError(message, errors)

# Service results
ServiceSuccess(data, **context)
ServiceError(message, error_code, **context)
NotFoundError(resource, identifier)
ConflictError(message, conflicting_resource)
```

### Working with Results

```python
# Type checking
result.is_success()
result.is_error()
result.is_timeout()

# Data access
result.get_data()
result.get_error_message()
result.get_or_else(default)
result.get_or_raise(exception)

# Transformation
result.map(func)
result.flat_map(func)
result.filter(predicate, error_message)
```

### HTTP Responses

```python
# Convert service result to HTTP response
from app.core.result_helpers import to_http_response

response = to_http_response(service_result)
# {
#     "success": True/False,
#     "status": 200/400/404/500,
#     "data": {...},  # if success
#     "error": {...}  # if error
# }
```

## Support

For questions or issues with the result types system:

1. Check this guide for common patterns
2. Review unit tests in `tests/test_core_result_types.py`
3. See example usage in `services/execution_service_result_types.py`
4. Consult API reference above

## Changelog

### Version 1.0.0 (2024-01-01)

- Initial release of result wrapper types system
- Base result types (Success, Error, Timeout, ValidationError)
- Service result types with HTTP status mapping
- Result helpers for common operations
- Result builders for fluent construction
- Comprehensive test coverage
- Complete documentation
