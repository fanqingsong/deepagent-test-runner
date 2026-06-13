"""
Service Result Types

Specialized result types for service layer operations.
Provides domain-specific error codes and HTTP status mappings.
"""

from typing import Optional, Dict, Any, List, Type, Set, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


T = TypeVar('T')
E = TypeVar('E')

from app.core.result_types import Result, Success, Error, ResultType


class ErrorCode(Enum):
    """Standard error codes for service operations."""

    # General errors (1000-1999)
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OPERATION_FAILED = "OPERATION_FAILED"

    # Database errors (2000-2999)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_CONSTRAINT_ERROR = "DATABASE_CONSTRAINT_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    RECORD_ALREADY_EXISTS = "RECORD_ALREADY_EXISTS"
    RECORD_CONFLICT = "RECORD_CONFLICT"

    # Validation errors (3000-3999)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_VALUE = "INVALID_VALUE"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"

    # Permission errors (4000-4999)
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    RESOURCE_FORBIDDEN = "RESOURCE_FORBIDDEN"

    # Resource errors (5000-5999)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    RESOURCE_EXPIRED = "RESOURCE_EXPIRED"

    # Business logic errors (6000-6999)
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"

    # Test execution errors (7000-7999)
    TEST_EXECUTION_ERROR = "TEST_EXECUTION_ERROR"
    TEST_TIMEOUT = "TEST_TIMEOUT"
    TEST_SETUP_FAILED = "TEST_SETUP_FAILED"
    TEST_CLEANUP_FAILED = "TEST_CLEANUP_FAILED"
    SCRIPT_VALIDATION_FAILED = "SCRIPT_VALIDATION_FAILED"
    SCRIPT_EXECUTION_FAILED = "SCRIPT_EXECUTION_FAILED"

    # Temporal errors (8000-8999)
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    ACTIVITY_ERROR = "ACTIVITY_ERROR"
    SCHEDULE_ERROR = "SCHEDULE_ERROR"
    WORKER_ERROR = "WORKER_ERROR"


class HTTPStatusMap:
    """Maps error codes to HTTP status codes."""

    MAPPING: Dict[ErrorCode, int] = {
        # General errors
        ErrorCode.INTERNAL_ERROR: 500,
        ErrorCode.OPERATION_FAILED: 500,

        # Database errors
        ErrorCode.DATABASE_ERROR: 500,
        ErrorCode.DATABASE_CONNECTION_ERROR: 503,
        ErrorCode.DATABASE_QUERY_ERROR: 500,
        ErrorCode.DATABASE_CONSTRAINT_ERROR: 400,
        ErrorCode.RECORD_NOT_FOUND: 404,
        ErrorCode.RECORD_ALREADY_EXISTS: 409,
        ErrorCode.RECORD_CONFLICT: 409,

        # Validation errors
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.INVALID_INPUT: 400,
        ErrorCode.MISSING_REQUIRED_FIELD: 400,
        ErrorCode.INVALID_FORMAT: 400,
        ErrorCode.INVALID_VALUE: 400,
        ErrorCode.CONSTRAINT_VIOLATION: 400,

        # Permission errors
        ErrorCode.PERMISSION_DENIED: 403,
        ErrorCode.AUTHENTICATION_REQUIRED: 401,
        ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
        ErrorCode.RESOURCE_FORBIDDEN: 403,

        # Resource errors
        ErrorCode.RESOURCE_NOT_FOUND: 404,
        ErrorCode.RESOURCE_ALREADY_EXISTS: 409,
        ErrorCode.RESOURCE_CONFLICT: 409,
        ErrorCode.RESOURCE_LOCKED: 423,
        ErrorCode.RESOURCE_EXPIRED: 410,

        # Business logic errors
        ErrorCode.BUSINESS_LOGIC_ERROR: 400,
        ErrorCode.INVALID_STATE_TRANSITION: 400,
        ErrorCode.OPERATION_NOT_ALLOWED: 405,
        ErrorCode.DEPENDENCY_ERROR: 400,
        ErrorCode.CIRCULAR_DEPENDENCY: 400,

        # Test execution errors
        ErrorCode.TEST_EXECUTION_ERROR: 500,
        ErrorCode.TEST_TIMEOUT: 504,
        ErrorCode.TEST_SETUP_FAILED: 500,
        ErrorCode.TEST_CLEANUP_FAILED: 500,
        ErrorCode.SCRIPT_VALIDATION_FAILED: 400,
        ErrorCode.SCRIPT_EXECUTION_FAILED: 500,

        # Temporal errors
        ErrorCode.WORKFLOW_ERROR: 500,
        ErrorCode.ACTIVITY_ERROR: 500,
        ErrorCode.SCHEDULE_ERROR: 500,
        ErrorCode.WORKER_ERROR: 503,
    }

    @classmethod
    def get_status(cls, error_code: ErrorCode) -> int:
        """Get HTTP status code for error code."""
        return cls.MAPPING.get(error_code, 500)


@dataclass(frozen=True)
class ServiceResult(Result, Generic[T]):
    """
    Base class for all service-specific results.

    Extends base Result with service-level features:
    - Error code mapping to HTTP status
    - Request tracking
    - Service context
    """

    service_name: Optional[str] = None
    operation_name: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_http_status(self) -> int:
        """Get HTTP status code for this result."""
        if self.is_success():
            return 200

        if isinstance(self, ServiceError):
            return HTTPStatusMap.get_status(self.error_code)
        return 500

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with service context."""
        base = super().to_dict()
        base.update({
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "http_status": self.get_http_status(),
        })
        return base


@dataclass(frozen=True)
class ServiceSuccess(ServiceResult, Generic[T]):
    """
    Successful service operation result.

    Extends Success with service context and metadata.
    """

    result_type: ResultType = field(default=ResultType.SUCCESS, init=False)
    data: Any = field(default_factory=lambda: None)
    metadata: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False

    def get_error_message(self) -> Optional[str]:
        return None

    def get_data(self) -> Any:
        return self.data

    def with_metadata(self, **metadata) -> 'ServiceSuccess[Any]':
        """Create new success with additional metadata."""
        current_metadata = self.metadata or {}
        return ServiceSuccess(
            data=self.data,
            metadata={**current_metadata, **metadata},
            service_name=self.service_name,
            operation_name=self.operation_name,
            request_id=self.request_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base["data"] = self.data
        base["metadata"] = self.metadata
        return base


@dataclass(frozen=True)
class ServiceError(ServiceResult, Generic[E]):
    """
    Failed service operation result.

    Extends Error with error codes and service context.
    """

    result_type: ResultType = field(default=ResultType.ERROR, init=False)
    message: str
    error_code: ErrorCode = ErrorCode.OPERATION_FAILED
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None

    def is_success(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True

    def get_error_message(self) -> str:
        return self.message

    def get_data(self) -> Any:
        raise AttributeError("ServiceError has no data")

    def get_http_status(self) -> int:
        """Get HTTP status code for this error."""
        return HTTPStatusMap.get_status(self.error_code)

    def with_detail(self, key: str, value: Any) -> 'ServiceError':
        """Create new error with additional detail."""
        current_details = self.details or {}
        return ServiceError(
            message=self.message,
            error_code=self.error_code,
            details={**current_details, key: value},
            service_name=self.service_name,
            operation_name=self.operation_name,
            request_id=self.request_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "message": self.message,
            "error_code": self.error_code.value,
            "details": self.details,
            "http_status": self.get_http_status(),
        })
        if self.stack_trace:
            base["stack_trace"] = self.stack_trace
        return base


# Specialized service error types
class DatabaseError(ServiceError):
    """Database operation error."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_ERROR,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        # Initialize as a ServiceError with proper field values
        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = error_code
        self.details = details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


class NotFoundError(ServiceError):
    """Resource not found error."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        final_details = details or {}
        final_details.update({"resource": resource, "identifier": identifier})

        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = ErrorCode.RESOURCE_NOT_FOUND
        self.details = final_details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


class ConflictError(ServiceError):
    """Resource conflict error."""

    def __init__(
        self,
        message: str,
        conflicting_resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        final_details = details or {}
        if conflicting_resource:
            final_details.update({"conflicting_resource": conflicting_resource})

        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = ErrorCode.RESOURCE_CONFLICT
        self.details = final_details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


class ServiceValidationError(ServiceError):
    """Input validation error."""

    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        final_details = details or {}
        if field_errors:
            final_details.update({"field_errors": field_errors})

        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = ErrorCode.VALIDATION_ERROR
        self.details = final_details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


class PermissionError(ServiceError):
    """Permission denied error."""

    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        final_details = details or {}
        if required_permission:
            final_details.update({"required_permission": required_permission})

        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = ErrorCode.PERMISSION_DENIED
        self.details = final_details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


class TestExecutionError(ServiceError):
    """Test execution error."""

    def __init__(
        self,
        message: str,
        test_id: Optional[str] = None,
        execution_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        final_details = details or {}
        if test_id:
            final_details.update({"test_id": test_id})
        if execution_stage:
            final_details.update({"execution_stage": execution_stage})

        self.result_type = ResultType.ERROR
        self.message = message
        self.error_code = ErrorCode.TEST_EXECUTION_ERROR
        self.details = final_details
        self.stack_trace = service_context.get('stack_trace')
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()


# Result aggregation for bulk operations
@dataclass(frozen=True)
class BulkServiceResult(ServiceResult):
    """
    Result for bulk operations with individual item results.

    Used for operations like bulk creation, updates, or deletions.
    """

    result_type: ResultType = field(default=ResultType.SUCCESS, init=False)
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    item_results: List[Result] = field(default_factory=list)

    def is_success(self) -> bool:
        """Bulk success if no items failed."""
        return self.failed_items == 0

    def is_error(self) -> bool:
        """Bulk error if any items failed."""
        return self.failed_items > 0

    def get_error_message(self) -> Optional[str]:
        """Get error message if bulk operation failed."""
        if self.is_success():
            return None
        return f"Bulk operation failed: {self.failed_items}/{self.total_items} items failed"

    def get_data(self) -> Dict[str, Any]:
        """Get bulk operation data."""
        return {
            "total_items": self.total_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "success_rate": self.successful_items / self.total_items if self.total_items > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "total_items": self.total_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "item_results": [r.to_dict() for r in self.item_results]
        })
        return base
