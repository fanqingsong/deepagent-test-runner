"""
Result Helpers

Utility functions for creating and working with result types.
Provides convenient factory functions and utilities for common operations.
"""

from typing import Any, Optional, Dict, List, Type, Callable, TypeVar, Union
from functools import wraps
import traceback

from app.core.result_types import Result, Success, Error, Timeout, ValidationError
from app.core.error_codes import ErrorCode


T = TypeVar('T')
U = TypeVar('U')


# ============================================================================
# Basic Result Creation Helpers
# ============================================================================

def success(data: Any = None) -> Success:
    """
    Create a success result with data.

    Args:
        data: Success data (default: None)

    Returns:
        Success result containing the data

    Examples:
        >>> success({"user_id": 123})
        Success({'user_id': 123})
        >>> success()
        Success(None)
    """
    return Success(data)


def error(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Error:
    """
    Create an error result.

    Args:
        message: Error message
        code: Optional error code
        details: Optional error details dictionary

    Returns:
        Error result with provided information

    Examples:
        >>> error("User not found")
        Error('User not found', code=None)
        >>> error("Validation failed", code="VALIDATION_ERROR")
        Error('Validation failed', code='VALIDATION_ERROR')
    """
    return Error(message, code, details)


def timeout(
    message: str = "Operation timed out",
    timeout_seconds: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> Timeout:
    """
    Create a timeout result.

    Args:
        message: Timeout message (default: "Operation timed out")
        timeout_seconds: Optional timeout duration
        details: Optional timeout details

    Returns:
        Timeout result

    Examples:
        >>> timeout(timeout_seconds=30.0)
        Timeout('Operation timed out', timeout_seconds=30.0)
    """
    return Timeout(message, timeout_seconds, details)


def validation_error(
    message: str = "Validation failed",
    errors: Optional[Dict[str, List[str]]] = None
) -> ValidationError:
    """
    Create a validation error result.

    Args:
        message: Validation error message (default: "Validation failed")
        errors: Optional field-level validation errors

    Returns:
        ValidationError result

    Examples:
        >>> validation_error(errors={"email": ["Invalid format"]})
        ValidationError('Validation failed', errors={'email': ['Invalid format']})
    """
    return ValidationError(message, errors)


# ============================================================================
# Service Result Creation Helpers
# ============================================================================

def service_success(
    data: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    **service_context
) -> Success:
    """
    Create a service success result.

    Args:
        data: Success data
        metadata: Optional metadata dictionary
        **service_context: Service context (service_name, operation_name, etc.)

    Returns:
        ServiceSuccess result

    Examples:
        >>> service_success(data={"test_id": 123}, service_name="ExecutionService")
        ServiceSuccess(data={'test_id': 123}, service_name='ExecutionService')
    """
    # For now, return a basic Success with context stored in data
    result_data = {
        'data': data,
        'metadata': metadata,
        'service_context': service_context
    }
    return Success(result_data)


def service_error(
    message: str,
    error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
    details: Optional[Dict[str, Any]] = None,
    **service_context
) -> Error:
    """
    Create a service error result.

    Args:
        message: Error message
        error_code: Error code enum (default: OPERATION_FAILED)
        details: Optional error details
        **service_context: Service context

    Returns:
        ServiceError result

    Examples:
        >>> service_error("Database connection failed", ErrorCode.DATABASE_ERROR)
        ServiceError('Database connection failed', error_code=ErrorCode.DATABASE_ERROR)
    """
    # For now, return a basic Error with context
    return Error(
        message=message,
        code=error_code.value,
        details={**details, 'service_context': service_context} if details else {'service_context': service_context}
    )


def not_found(
    resource: str,
    identifier: Optional[str] = None,
    **service_context
) -> Error:
    """Create a not found error result."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"

    return Error(
        message=message,
        code="NOT_FOUND",
        details={"resource": resource, "identifier": identifier, "service_context": service_context}
    )


def conflict(
    message: str,
    conflicting_resource: Optional[str] = None,
    **service_context
) -> Error:
    """Create a conflict error result."""
    return Error(
        message=message,
        code="CONFLICT",
        details={"conflicting_resource": conflicting_resource, "service_context": service_context}
    )


def database_error(
    message: str,
    error_code: ErrorCode = ErrorCode.DATABASE_ERROR,
    details: Optional[Dict[str, Any]] = None,
    **service_context
) -> Error:
    """Create a database error result."""
    return Error(message, code=error_code.value, details=details)


def permission_error(
    message: str,
    required_permission: Optional[str] = None,
    **service_context
) -> Error:
    """Create a permission error result."""
    return Error(message, code="PERMISSION_DENIED", details={"required_permission": required_permission})


def test_execution_error(
    message: str,
    test_id: Optional[str] = None,
    execution_stage: Optional[str] = None,
    **service_context
) -> Error:
    """Create a test execution error result."""
    return Error(message, code="TEST_EXECUTION_ERROR", details={"test_id": test_id, "execution_stage": execution_stage})


# ============================================================================
# Result Inspection Helpers
# ============================================================================

def is_success(result: Result) -> bool:
    """
    Check if result is successful.

    Args:
        result: Result to check

    Returns:
        True if result is success, False otherwise

    Examples:
        >>> is_success(Success(42))
        True
        >>> is_success(Error("Failed"))
        False
    """
    return result.is_success()


def is_error(result: Result) -> bool:
    """
    Check if result is an error.

    Args:
        result: Result to check

    Returns:
        True if result is error, False otherwise
    """
    return result.is_error()


def is_timeout(result: Result) -> bool:
    """
    Check if result is a timeout.

    Args:
        result: Result to check

    Returns:
        True if result is timeout, False otherwise
    """
    return result.is_timeout()


def is_validation_error(result: Result) -> bool:
    """
    Check if result is a validation error.

    Args:
        result: Result to check

    Returns:
        True if result is validation error, False otherwise
    """
    return result.is_validation_error()


# ============================================================================
# Data Extraction Helpers
# ============================================================================

def get_data(result: Result, default: Any = None) -> Any:
    """
    Extract data from success result or return default.

    Args:
        result: Result to extract data from
        default: Default value if result is error (default: None)

    Returns:
        Result data or default value

    Examples:
        >>> get_data(Success(42))
        42
        >>> get_data(Error("Failed"), default=0)
        0
    """
    if result.is_success():
        return result.get_data()
    return default


def get_error(result: Result, default: Optional[str] = None) -> Optional[str]:
    """
    Extract error message from error result or return default.

    Args:
        result: Result to extract error from
        default: Default value if result is success (default: None)

    Returns:
        Error message or default value

    Examples:
        >>> get_error(Error("Failed"))
        'Failed'
        >>> get_error(Success(42), default="No error")
        'No error'
    """
    if result.is_error():
        return result.get_error_message()
    return default


def get_or_raise(result: Result, exception: Type[Exception] = ValueError) -> Any:
    """
    Get data from result or raise exception.

    Args:
        result: Result to extract data from
        exception: Exception type to raise (default: ValueError)

    Returns:
        Result data if success

    Raises:
        exception: If result is error

    Examples:
        >>> get_or_raise(Success(42))
        42
        >>> get_or_raise(Error("Failed"))
        ValueError: Failed
    """
    return result.get_or_raise(exception)


# ============================================================================
# Result Transformation Helpers
# ============================================================================

def map_result(
    result: Result,
    func: Callable[[Any], Any]
) -> Result:
    """
    Apply function to result data if successful.

    Args:
        result: Result to transform
        func: Function to apply to success data

    Returns:
        Transformed result or original error

    Examples:
        >>> map_result(Success(42), lambda x: x * 2)
        Success(84)
        >>> map_result(Error("Failed"), lambda x: x * 2)
        Error('Failed')
    """
    return result.map(func)


def flat_map_result(
    result: Result,
    func: Callable[[Any], Result]
) -> Result:
    """
    Apply function returning result to success data.

    Args:
        result: Result to transform
        func: Function that returns a new result

    Returns:
        Result from function or original error
    """
    return result.flat_map(func)


def filter_result(
    result: Result,
    predicate: Callable[[Any], bool],
    error_message: str = "Filter condition failed"
) -> Result:
    """
    Filter success result with predicate.

    Args:
        result: Result to filter
        predicate: Function to test data
        error_message: Error message if predicate fails

    Returns:
        Filtered result or error

    Examples:
        >>> filter_result(Success(42), lambda x: x > 0)
        Success(42)
        >>> filter_result(Success(-1), lambda x: x > 0)
        Error('Filter condition failed')
    """
    return result.filter(predicate, error_message)


# ============================================================================
# Result Aggregation Helpers
# ============================================================================

def combine_results(*results: Result) -> Result:
    """
    Combine multiple results into one.

    Args:
        *results: Results to combine

    Returns:
        First error if any errors, Success with list of data otherwise

    Examples:
        >>> combine_results(Success(1), Success(2), Success(3))
        Success([1, 2, 3])
        >>> combine_results(Success(1), Error("Failed"))
        Error('Multiple operations failed: 1 errors')
    """
    errors = [r for r in results if r.is_error()]
    if errors:
        return Error(f"Multiple operations failed: {len(errors)} errors")

    data_list = [r.get_data() for r in results if is_success(r)]
    return Success(data_list)


def sequence_results(results: List[Any]) -> Any:
    """
    Sequence a list of results into a result of list.

    Args:
        results: List of results to sequence

    Returns:
        Success with list of data if all succeed, Error otherwise

    Examples:
        >>> sequence_results([Success(1), Success(2), Success(3)])
        Success([1, 2, 3])
        >>> sequence_results([Success(1), Error("Failed")])
        Error('Failed to sequence results: 1 errors')
    """
    from app.core.result_types import sequence_results as base_sequence
    return base_sequence(results)


def all_success(*results: Result) -> bool:
    """
    Check if all results are successful.

    Args:
        *results: Results to check

    Returns:
        True if all results are successful, False otherwise

    Examples:
        >>> all_success(Success(1), Success(2))
        True
        >>> all_success(Success(1), Error("Failed"))
        False
    """
    return all(r.is_success() for r in results)


def any_success(*results: Result) -> bool:
    """
    Check if any result is successful.

    Args:
        *results: Results to check

    Returns:
        True if any result is successful, False otherwise

    Examples:
        >>> any_success(Success(1), Error("Failed"))
        True
        >>> any_success(Error("Failed"), Error("Failed"))
        False
    """
    return any(r.is_success() for r in results)


# ============================================================================
# Exception Handling Helpers
# ============================================================================

def catch_exception(
    func: Callable,
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    **service_context
) -> Result:
    """
    Execute function and convert exceptions to error results.

    Args:
        func: Function to execute
        error_message: Error message if exception occurs
        error_code: Error code for the error result
        **service_context: Service context

    Returns:
        Service result from function or error result

    Examples:
        >>> def risky_operation():
        ...     raise ValueError("Something went wrong")
        >>> catch_exception(risky_operation)
        ServiceError('Operation failed')
    """
    try:
        result = func()
        if isinstance(result, Result):
            return result
        return service_success(data=result, **service_context)
    except Exception as e:
        return service_error(
            message=f"{error_message}: {str(e)}",
            error_code=error_code,
            details={"exception_type": type(e).__name__},
            **service_context
        )


async def async_catch_exception(
    func: Callable,
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    **service_context
) -> Result:
    """
    Execute async function and convert exceptions to error results.

    Args:
        func: Async function to execute
        error_message: Error message if exception occurs
        error_code: Error code for the error result
        **service_context: Service context

    Returns:
        Service result from function or error result
    """
    try:
        result = await func()
        if isinstance(result, Result):
            return result
        return service_success(data=result, **service_context)
    except Exception as e:
        return service_error(
            message=f"{error_message}: {str(e)}",
            error_code=error_code,
            details={"exception_type": type(e).__name__, "stack_trace": traceback.format_exc()},
            **service_context
        )


def result_decorator(
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
):
    """
    Decorator to convert exceptions to error results.

    Args:
        error_message: Error message prefix
        error_code: Error code for exceptions

    Returns:
        Decorator function

    Examples:
        >>> @result_decorator("Calculation failed")
        ... def calculate(x, y):
        ...     return x / y
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return service_error(
                    message=f"{error_message}: {str(e)}",
                    error_code=error_code,
                    details={"exception_type": type(e).__name__}
                )
        return wrapper
    return decorator


def async_result_decorator(
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
):
    """
    Async decorator to convert exceptions to error results.

    Args:
        error_message: Error message prefix
        error_code: Error code for exceptions

    Returns:
        Decorator function

    Examples:
        >>> @async_result_decorator("Async operation failed")
        ... async def fetch_data():
        ...     await asyncio.sleep(0.1)
        ...     return {"data": "value"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return service_error(
                    message=f"{error_message}: {str(e)}",
                    error_code=error_code,
                    details={"exception_type": type(e).__name__, "stack_trace": traceback.format_exc()}
                )
        return wrapper
    return decorator


# ============================================================================
# Conversion Helpers
# ============================================================================

def to_http_response(result: Result) -> Dict[str, Any]:
    """
    Convert service result to HTTP response format.

    Args:
        result: Service result to convert

    Returns:
        Dictionary with status, data, and error fields

    Examples:
        >>> to_http_response(service_success(data={"id": 123}))
        {'status': 200, 'success': True, 'data': {'id': 123}}
        >>> to_http_response(not_found("Test", "123"))
        {'status': 404, 'success': False, 'error': {'message': 'Test not found: 123'}}
    """
    if result.is_success():
        return {
            "status": result.get_http_status(),
            "success": True,
            "data": result.get_data(),
            "metadata": getattr(result, 'metadata', None)
        }

    return {
        "status": result.get_http_status(),
        "success": False,
        "error": {
            "message": result.get_error_message(),
            "code": getattr(result, 'error_code', None),
            "details": getattr(result, 'details', None)
        }
    }


def from_exception(
    exception: Exception,
    error_message: Optional[str] = None,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    **service_context
) -> Error:
    """
    Convert exception to service error result.

    Args:
        exception: Exception to convert
        error_message: Optional error message (uses exception message if not provided)
        error_code: Error code for the error
        **service_context: Service context

    Returns:
        Service error result from exception

    Examples:
        >>> from_exception(ValueError("Invalid input"))
        ServiceError('Invalid input', error_code=ErrorCode.INTERNAL_ERROR)
    """
    message = error_message or str(exception)
    return service_error(
        message=message,
        error_code=error_code,
        details={"exception_type": type(exception).__name__},
        **service_context
    )
