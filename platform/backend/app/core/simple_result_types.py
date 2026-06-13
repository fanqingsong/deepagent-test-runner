"""
Simple Result Wrapper Types

Provides lightweight, easy-to-use result types for service responses.
Designed for immediate adoption in service layers without complexity.
"""

from typing import TypeVar, Generic, Optional, Any, Dict, TypeGuard, Union, Callable
from dataclasses import dataclass
from enum import Enum


# Type variables for generic types
T = TypeVar('T')
E = TypeVar('E')


class ResultStatus(Enum):
    """Simple result status enumeration."""
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class Result:
    """
    Base result class for operation outcomes.

    Simple, effective wrapper for service responses.
    """
    status: ResultStatus

    def is_success(self) -> bool:
        """Check if result represents success."""
        return self.status == ResultStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if result represents error."""
        return self.status == ResultStatus.ERROR

    def get_data(self) -> Any:
        """Get data from result (default implementation)."""
        return None

    def get_error(self) -> Any:
        """Get error from result (default implementation)."""
        return None


@dataclass(frozen=True)
class Success(Result, Generic[T]):
    """
    Successful operation result with data.

    Type-safe container for successful operations.
    """
    status: ResultStatus = ResultStatus.SUCCESS
    data: T = None

    def is_success(self) -> bool:
        """Success is always successful."""
        return True

    def is_error(self) -> bool:
        """Success is never an error."""
        return False

    def get_data(self) -> T:
        """Get the success data."""
        return self.data

    def get_error(self) -> None:
        """Success has no error."""
        return None


@dataclass(frozen=True)
class Error(Result, Generic[E]):
    """
    Failed operation result with error information.

    Type-safe container for failed operations.
    """
    status: ResultStatus = ResultStatus.ERROR
    message: str = ""
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Error is never successful."""
        return False

    def is_error(self) -> bool:
        """Error is always an error."""
        return True

    def get_data(self) -> None:
        """Error has no data."""
        return None

    def get_error(self) -> E:
        """Get the error information."""
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


# Type guard functions
def is_success(result: Result) -> TypeGuard[Success]:
    """Type guard for Success results."""
    return result.is_success()


def is_error(result: Result) -> TypeGuard[Error]:
    """Type guard for Error results."""
    return result.is_error()


# Helper functions for common operations
def success(data: Any = None) -> Success:
    """Create a success result with optional data."""
    return Success(data=data)


def error(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Error:
    """Create an error result with message and optional code."""
    return Error(message=message, code=code, details=details)


def not_found(resource: str, identifier: Optional[str] = None) -> Error:
    """Create a not found error result."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    return error(message, code="NOT_FOUND", details={"resource": resource, "identifier": identifier})


def validation_error(message: str, field_errors: Optional[Dict[str, str]] = None) -> Error:
    """Create a validation error result."""
    details = {"field_errors": field_errors} if field_errors else None
    return error(message, code="VALIDATION_ERROR", details=details)


def permission_denied(message: str = "Permission denied", required_permission: Optional[str] = None) -> Error:
    """Create a permission denied error result."""
    details = {"required_permission": required_permission} if required_permission else None
    return error(message, code="PERMISSION_DENIED", details=details)


# Service-level result types
@dataclass(frozen=True)
class ServiceResult(Result, Generic[T]):
    """
    Base class for service-specific results.

    Extends basic Result with service context.
    """
    service_name: Optional[str] = None
    operation_name: Optional[str] = None

    def get_http_status(self) -> int:
        """Get appropriate HTTP status code."""
        if self.is_success():
            return 200
        return 500


@dataclass(frozen=True)
class ServiceSuccess(ServiceResult, Generic[T]):
    """
    Successful service operation result.

    Extends Success with service context.
    """
    status: ResultStatus = ResultStatus.SUCCESS
    data: T = None
    metadata: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False

    def get_data(self) -> T:
        return self.data

    def get_http_status(self) -> int:
        return 200


# HTTP status code mapping for service errors
SERVICE_ERROR_HTTP_STATUS_MAP: Dict[str, int] = {
    # General errors
    "INTERNAL_ERROR": 500,
    "OPERATION_FAILED": 500,

    # Database errors
    "DATABASE_ERROR": 500,
    "NOT_FOUND": 404,
    "ALREADY_EXISTS": 409,
    "CONFLICT": 409,

    # Validation errors
    "VALIDATION_ERROR": 400,
    "INVALID_INPUT": 400,

    # Permission errors
    "PERMISSION_DENIED": 403,
    "AUTHENTICATION_REQUIRED": 401,

    # Business logic
    "INVALID_STATE": 400,
    "OPERATION_NOT_ALLOWED": 405,
}


@dataclass(frozen=True)
class ServiceError(ServiceResult, Generic[E]):
    """
    Failed service operation result.

    Extends Error with service context and HTTP status mapping.
    """
    status: ResultStatus = ResultStatus.ERROR
    message: str = ""
    error_code: str = "OPERATION_FAILED"
    details: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True

    def get_data(self) -> None:
        return None

    def get_error(self) -> E:
        return self.message

    def get_http_status(self) -> int:
        """Get HTTP status code based on error code."""
        return SERVICE_ERROR_HTTP_STATUS_MAP.get(self.error_code, 500)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "http_status": self.get_http_status()
        }


# Service-level helper functions
def service_success(data: Any = None, **metadata) -> ServiceSuccess:
    """Create a service success result with optional metadata."""
    return ServiceSuccess(data=data, metadata=metadata if metadata else None)


def service_error(
    message: str,
    error_code: str = "OPERATION_FAILED",
    details: Optional[Dict[str, Any]] = None
) -> ServiceError:
    """Create a service error result."""
    return ServiceError(message=message, error_code=error_code, details=details)


def service_not_found(resource: str, identifier: Optional[str] = None) -> ServiceError:
    """Create a service not found error."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    return service_error(
        message=message,
        error_code="NOT_FOUND",
        details={"resource": resource, "identifier": identifier}
    )


def service_validation_error(message: str, field_errors: Optional[Dict[str, str]] = None) -> ServiceError:
    """Create a service validation error."""
    details = {"field_errors": field_errors} if field_errors else None
    return service_error(message, error_code="VALIDATION_ERROR", details=details)


def service_permission_denied(message: str = "Permission denied", required_permission: Optional[str] = None) -> ServiceError:
    """Create a service permission denied error."""
    details = {"required_permission": required_permission} if required_permission else None
    return service_error(message, error_code="PERMISSION_DENIED", details=details)


# Utility functions
def fold(result: Result, on_success: callable, on_error: callable) -> Any:
    """
    Fold result into a single value using provided functions.

    Args:
        result: Result to fold
        on_success: Function called on success with data
        on_error: Function called on error with error info

    Returns:
        Result of applying appropriate function
    """
    if result.is_success():
        return on_success(result.get_data())
    return on_error(result.get_error())


def map_result(result: Result, func: callable) -> Result:
    """
    Apply function to result data if successful.

    Args:
        result: Result to map
        func: Function to apply to success data

    Returns:
        New result with transformed data or original error
    """
    if result.is_success():
        try:
            return Success(data=func(result.get_data()))
        except Exception as e:
            return Error(message=str(e))
    return result


def get_or_else(result: Result, default: Any) -> Any:
    """
    Get data from result or return default value.

    Args:
        result: Result to extract from
        default: Default value if error

    Returns:
        Data or default value
    """
    if result.is_success():
        return result.get_data()
    return default


def get_or_raise(result: Result, exception: type = ValueError) -> Any:
    """
    Get data from result or raise exception.

    Args:
        result: Result to extract from
        exception: Exception class to raise

    Returns:
        Data if success

    Raises:
        Specified exception if error
    """
    if result.is_success():
        return result.get_data()
    error_info = result.get_error()
    raise exception(error_info if isinstance(error_info, str) else "Operation failed")
