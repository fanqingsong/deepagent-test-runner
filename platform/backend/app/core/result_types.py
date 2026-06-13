"""
Result Wrapper Types

Provides standardized result types for consistent service responses following SOLID principles.
Base classes and interfaces for result handling.
"""

from abc import ABC, abstractmethod
from typing import (
    TypeVar, Generic, Optional, Any, Callable, TypeGuard, Union,
    Type, Dict, List, Tuple, get_origin, get_args
)
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json


T = TypeVar('T')
E = TypeVar('E')
U = TypeVar('U')


class ResultType(Enum):
    """Enumeration of possible result types."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"


@dataclass(frozen=True)
class Result(ABC):
    """
    Abstract base class for all result types.

    Provides common interface and functionality for all result wrappers.
    Following SOLID principles:
    - Single Responsibility: Each result type handles one specific outcome
    - Open/Closed: Open for extension (new result types), closed for modification
    - Liskov Substitution: All results can be used interchangeably
    - Interface Segregation: Clean, focused interfaces
    - Dependency Inversion: Depends on abstractions (ABC), not concretions
    """

    result_type: ResultType

    @abstractmethod
    def is_success(self) -> bool:
        """Check if result represents a successful operation."""
        pass

    @abstractmethod
    def is_error(self) -> bool:
        """Check if result represents a failed operation."""
        pass

    def is_timeout(self) -> bool:
        """Check if result represents a timeout."""
        return self.result_type == ResultType.TIMEOUT

    def is_validation_error(self) -> bool:
        """Check if result represents a validation error."""
        return self.result_type == ResultType.VALIDATION_ERROR

    @abstractmethod
    def get_error_message(self) -> Optional[str]:
        """Get error message if available."""
        pass

    def map(self, func: Callable[[Any], 'Result[U]']) -> 'Result[U]':
        """
        Apply function to result data if successful.

        Args:
            func: Function to apply to success data

        Returns:
            New result with transformed data or error propagated
        """
        if self.is_success():
            try:
                return func(self.get_data())
            except Exception as e:
                return Error(str(e))
        return self

    def flat_map(self, func: Callable[[Any], 'Result[U]']) -> 'Result[U]':
        """
        Apply function that returns result to success data.

        Args:
            func: Function returning new result

        Returns:
            Result from function or error propagated
        """
        if self.is_success():
            try:
                return func(self.get_data())
            except Exception as e:
                return Error(str(e))
        return self

    def filter(self, predicate: Callable[[Any], bool], error_message: str = "Filter condition failed") -> 'Result[T]':
        """
        Filter success result with predicate.

        Args:
            predicate: Function to test data
            error_message: Error message if predicate returns False

        Returns:
            Success if predicate passes, Error otherwise
        """
        if self.is_success() and not predicate(self.get_data()):
            return Error(error_message)
        return self

    @abstractmethod
    def get_data(self) -> Any:
        """Get data from result if available."""
        pass

    def get_or_else(self, default: T) -> T:
        """Get data or return default value."""
        if self.is_success():
            return self.get_data()
        return default

    def get_or_raise(self, exception: Type[Exception] = ValueError) -> T:
        """Get data or raise exception."""
        if self.is_success():
            return self.get_data()
        raise exception(self.get_error_message() or "Operation failed")

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "result_type": self.result_type.value,
            "is_success": self.is_success(),
            "is_error": self.is_error(),
        }

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Result':
        """Create result from dictionary representation."""
        result_type = data.get("result_type")

        if result_type == ResultType.SUCCESS.value:
            return Success(data.get("data"))
        elif result_type == ResultType.VALIDATION_ERROR.value:
            return ValidationError(data.get("message"), data.get("errors"))
        elif result_type == ResultType.TIMEOUT.value:
            return Timeout(data.get("message"), data.get("timeout_seconds"))
        else:
            return Error(data.get("message"), data.get("code"), data.get("details"))


@dataclass(frozen=True)
class Success(Result, Generic[T]):
    """
    Represents a successful operation result.

    Type-safe success container that can hold any successful operation result.
    """

    result_type: ResultType = field(default=ResultType.SUCCESS, init=False)
    data: T = field(default_factory=lambda: None)

    def is_success(self) -> bool:
        """Success is always successful."""
        return True

    def is_error(self) -> bool:
        """Success is never an error."""
        return False

    def get_error_message(self) -> Optional[str]:
        """Success has no error message."""
        return None

    def get_data(self) -> T:
        """Get the success data."""
        return self.data

    def map(self, func: Callable[[T], U]) -> 'Success[U]':
        """Apply function to success data."""
        try:
            return Success(func(self.data))
        except Exception as e:
            return Error(str(e))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base["data"] = self.data
        return base

    def __repr__(self) -> str:
        return f"Success({self.data!r})"


@dataclass(frozen=True)
class Error(Result, Generic[E]):
    """
    Represents a failed operation result.

    Type-safe error container with detailed error information.
    """

    result_type: ResultType = field(default=ResultType.ERROR, init=False)
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Error is never successful."""
        return False

    def is_error(self) -> bool:
        """Error is always an error."""
        return True

    def get_error_message(self) -> str:
        """Get the error message."""
        return self.message

    def get_data(self) -> Any:
        """Error has no data."""
        raise AttributeError("Error result has no data")

    def add_detail(self, key: str, value: Any) -> 'Error[E]':
        """Add detail to error information."""
        current_details = self.details or {}
        return Error(self.message, self.code, {**current_details, key: value})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "message": self.message,
            "code": self.code,
            "details": self.details
        })
        return base

    def __repr__(self) -> str:
        return f"Error({self.message!r}, code={self.code!r})"


@dataclass(frozen=True)
class Timeout(Result):
    """
    Represents an operation timeout result.

    Specialized error type for timeout scenarios with duration information.
    """

    result_type: ResultType = field(default=ResultType.TIMEOUT, init=False)
    message: str = "Operation timed out"
    timeout_seconds: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Timeout is never successful."""
        return False

    def is_error(self) -> bool:
        """Timeout is always an error."""
        return True

    def get_error_message(self) -> str:
        """Get timeout message."""
        return self.message

    def get_data(self) -> Any:
        """Timeout has no data."""
        raise AttributeError("Timeout result has no data")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "message": self.message,
            "timeout_seconds": self.timeout_seconds,
            "details": self.details
        })
        return base

    def __repr__(self) -> str:
        return f"Timeout({self.message!r}, timeout={self.timeout_seconds})"


@dataclass(frozen=True)
class ValidationError(Result):
    """
    Represents a validation error result.

    Specialized error type for input validation failures with field-level details.
    """

    result_type: ResultType = field(default=ResultType.VALIDATION_ERROR, init=False)
    message: str = "Validation failed"
    errors: Optional[Dict[str, List[str]]] = None

    def is_success(self) -> bool:
        """Validation error is never successful."""
        return False

    def is_error(self) -> bool:
        """Validation error is always an error."""
        return True

    def get_error_message(self) -> str:
        """Get validation error message."""
        return self.message

    def get_data(self) -> Any:
        """Validation error has no data."""
        raise AttributeError("ValidationError has no data")

    def add_field_error(self, field: str, error: str) -> 'ValidationError':
        """Add field-level validation error."""
        current_errors = self.errors or {}
        field_errors = current_errors.get(field, [])
        return ValidationError(self.message, {
            **current_errors,
            field: [*field_errors, error]
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "message": self.message,
            "errors": self.errors
        })
        return base

    def __repr__(self) -> str:
        return f"ValidationError({self.message!r}, errors={self.errors!r})"


# Type guard functions
def is_success(result: Result) -> TypeGuard[Success]:
    """Type guard for Success results."""
    return result.is_success()


def is_error(result: Result) -> TypeGuard[Union[Error, Timeout, ValidationError]]:
    """Type guard for any error result."""
    return result.is_error()


def is_timeout(result: Result) -> TypeGuard[Timeout]:
    """Type guard for Timeout results."""
    return result.is_timeout()


def is_validation_error(result: Result) -> TypeGuard[ValidationError]:
    """Type guard for ValidationError results."""
    return result.is_validation_error()


# Higher-order utilities
def fold(
    result: Result,
    on_success: Callable[[Any], T],
    on_error: Callable[[Result], T]
) -> T:
    """
    Fold result into a single value using provided functions.

    Args:
        result: Result to fold
        on_success: Function called on success
        on_error: Function called on error

    Returns:
        Result of applying appropriate function
    """
    if result.is_success():
        return on_success(result.get_data())
    return on_error(result)


def match(result: Result, *cases: Tuple[Type[Result], Callable[..., T]]) -> Optional[T]:
    """
    Pattern matching for results.

    Args:
        result: Result to match
        *cases: Tuple of (result type, handler function)

    Returns:
        Result of matched handler or None if no match
    """
    for result_type, handler in cases:
        if isinstance(result, result_type):
            return handler(result)
    return None


def combine_results(*results: Result) -> Result:
    """
    Combine multiple results into one.

    Args:
        *results: Results to combine

    Returns:
        First error if any errors, Success with list of data otherwise
    """
    # Check for any errors
    errors = [r for r in results if r.is_error()]
    if errors:
        return Error(f"Multiple operations failed: {len(errors)} errors")

    # All successes - extract data
    data_list = [r.get_data() for r in results if is_success(r)]
    return Success(data_list)


def sequence_results(results: List[Any]) -> Any:
    """
    Sequence a list of results into a result of list.

    Args:
        results: List of results to sequence

    Returns:
        Success with list of data if all succeed, Error otherwise
    """
    errors = [r for r in results if r.is_error()]
    if errors:
        return Error(f"Failed to sequence results: {len(errors)} errors")

    return Success([r.get_data() for r in results])


# Decorator for result-returning functions
def result_decorator(
    on_exception: Callable[[Exception], Result] = None
):
    """
    Decorator to convert exceptions to error results.

    Args:
        on_exception: Optional function to convert exception to error result
    """
    if on_exception is None:
        on_exception = lambda e: Error(str(e))

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return on_exception(e)
        return wrapper
    return decorator


# Async version of the decorator
def async_result_decorator(
    on_exception: Callable[[Exception], Result] = None
):
    """Async decorator to convert exceptions to error results."""
    if on_exception is None:
        on_exception = lambda e: Error(str(e))

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return on_exception(e)
        return wrapper
    return decorator
