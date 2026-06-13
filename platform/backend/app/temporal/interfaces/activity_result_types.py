"""
Activity Result Types

Standardized result types for all activities to ensure consistent
error handling, logging, and monitoring.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar

from .activity_interface import ActivityError

T = TypeVar("T")


class ActivityStatus(str, Enum):
    """Standard activity execution statuses."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    VALIDATION_ERROR = "validation_error"


@dataclass
class ActivityResult:
    """
    Base result type for all activities.

    Provides a consistent structure for activity execution results,
    supporting both success and failure scenarios.

    Attributes:
        status: Activity execution status
        activity_name: Name of the activity that was executed
        start_time: Activity start timestamp
        end_time: Activity end timestamp
        duration_ms: Execution duration in milliseconds
        error: Optional error details if activity failed
        metadata: Additional metadata for extensibility
        metrics: Optional performance metrics
    """

    status: ActivityStatus
    activity_name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    error: Optional[ActivityError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate duration if end_time is provided."""
        if self.end_time and self.duration_ms == 0:
            delta = self.end_time - self.start_time
            self.duration_ms = int(delta.total_seconds() * 1000)

    def is_success(self) -> bool:
        """Check if activity executed successfully."""
        return self.status == ActivityStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if activity execution failed."""
        return self.status in [
            ActivityStatus.FAILED,
            ActivityStatus.TIMEOUT,
            ActivityStatus.VALIDATION_ERROR,
        ]

    def is_retryable(self) -> bool:
        """Check if this failure is retryable."""
        return self.error.is_retryable if self.error else False

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "status": self.status.value,
            "activity_name": self.activity_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "error": self.error.to_dict() if self.error else None,
            "metadata": self.metadata,
            "metrics": self.metrics,
        }


@dataclass
class SuccessResult(ActivityResult):
    """
    Result for successful activity execution.

    Attributes:
        data: Optional result data from activity execution
        message: Optional success message
    """

    data: Any = None
    message: Optional[str] = None

    def __post_init__(self):
        """Set status to success on initialization."""
        self.status = ActivityStatus.SUCCESS
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with success-specific fields."""
        base_dict = super().to_dict()
        base_dict.update({
            "data": self.data,
            "message": self.message,
        })
        return base_dict


@dataclass
class ErrorResult(ActivityResult):
    """
    Result for failed activity execution.

    Attributes:
        error_details: Detailed error information
        recovery_suggestions: Optional suggestions for recovery
        fallback_data: Optional fallback data if execution failed but returned partial results
    """

    error_details: Dict[str, Any] = field(default_factory=dict)
    recovery_suggestions: List[str] = field(default_factory=list)
    fallback_data: Any = None

    def __post_init__(self):
        """Set status to failed on initialization."""
        self.status = ActivityStatus.FAILED
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with error-specific fields."""
        base_dict = super().to_dict()
        base_dict.update({
            "error_details": self.error_details,
            "recovery_suggestions": self.recovery_suggestions,
            "fallback_data": self.fallback_data,
        })
        return base_dict


@dataclass
class TimeoutResult(ActivityResult):
    """
    Result for activity timeout.

    Attributes:
        timeout_seconds: Timeout threshold in seconds
        partial_data: Any partial results collected before timeout
        progress_before_timeout: Optional progress percentage (0-100)
    """

    timeout_seconds: int = 0
    partial_data: Any = None
    progress_before_timeout: Optional[float] = None

    def __post_init__(self):
        """Set status to timeout on initialization."""
        self.status = ActivityStatus.TIMEOUT
        # Timeouts are generally not retryable for the same input
        if self.error:
            self.error.is_retryable = False
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with timeout-specific fields."""
        base_dict = super().to_dict()
        base_dict.update({
            "timeout_seconds": self.timeout_seconds,
            "partial_data": self.partial_data,
            "progress_before_timeout": self.progress_before_timeout,
        })
        return base_dict


@dataclass
class ValidationErrorResult(ActivityResult):
    """
    Result for input validation failures.

    Attributes:
        validation_errors: List of validation error messages
        invalid_fields: Dictionary of field names to error messages
        corrected_input: Optional corrected input if auto-correction was attempted
    """

    validation_errors: List[str] = field(default_factory=list)
    invalid_fields: Dict[str, str] = field(default_factory=dict)
    corrected_input: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Set status to validation_error on initialization."""
        self.status = ActivityStatus.VALIDATION_ERROR
        # Validation errors are generally not retryable without input modification
        if self.error:
            self.error.is_retryable = False
        super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with validation-specific fields."""
        base_dict = super().to_dict()
        base_dict.update({
            "validation_errors": self.validation_errors,
            "invalid_fields": self.invalid_fields,
            "corrected_input": self.corrected_input,
        })
        return base_dict


def create_success_result(
    activity_name: str,
    data: Any = None,
    message: str = None,
    start_time: datetime = None,
    metrics: Dict[str, Any] = None,
) -> SuccessResult:
    """
    Factory function to create a SuccessResult.

    Args:
        activity_name: Name of the activity
        data: Optional result data
        message: Optional success message
        start_time: Optional start time (defaults to now)
        metrics: Optional performance metrics

    Returns:
        SuccessResult instance
    """
    return SuccessResult(
        activity_name=activity_name,
        data=data,
        message=message,
        start_time=start_time or datetime.utcnow(),
        end_time=datetime.utcnow(),
        metrics=metrics or {},
    )


def create_error_result(
    activity_name: str,
    error: ActivityError,
    start_time: datetime = None,
    error_details: Dict[str, Any] = None,
    recovery_suggestions: List[str] = None,
    fallback_data: Any = None,
) -> ErrorResult:
    """
    Factory function to create an ErrorResult.

    Args:
        activity_name: Name of the activity
        error: ActivityError with error details
        start_time: Optional start time (defaults to now)
        error_details: Optional additional error details
        recovery_suggestions: Optional recovery suggestions
        fallback_data: Optional fallback data

    Returns:
        ErrorResult instance
    """
    return ErrorResult(
        activity_name=activity_name,
        error=error,
        start_time=start_time or datetime.utcnow(),
        end_time=datetime.utcnow(),
        error_details=error_details or {},
        recovery_suggestions=recovery_suggestions or [],
        fallback_data=fallback_data,
    )


def create_timeout_result(
    activity_name: str,
    timeout_seconds: int,
    error: ActivityError = None,
    partial_data: Any = None,
    progress_before_timeout: float = None,
    start_time: datetime = None,
) -> TimeoutResult:
    """
    Factory function to create a TimeoutResult.

    Args:
        activity_name: Name of the activity
        timeout_seconds: Timeout threshold in seconds
        error: Optional ActivityError
        partial_data: Optional partial results
        progress_before_timeout: Optional progress percentage
        start_time: Optional start time (defaults to now)

    Returns:
        TimeoutResult instance
    """
    if error is None:
        error = ActivityError(
            error_type="TimeoutError",
            error_message=f"Activity {activity_name} timed out after {timeout_seconds} seconds",
            is_retryable=False,
        )

    return TimeoutResult(
        activity_name=activity_name,
        error=error,
        timeout_seconds=timeout_seconds,
        partial_data=partial_data,
        progress_before_timeout=progress_before_timeout,
        start_time=start_time or datetime.utcnow(),
        end_time=datetime.utcnow(),
    )


def create_validation_error_result(
    activity_name: str,
    validation_errors: List[str],
    invalid_fields: Dict[str, str] = None,
    corrected_input: Dict[str, Any] = None,
    start_time: datetime = None,
) -> ValidationErrorResult:
    """
    Factory function to create a ValidationErrorResult.

    Args:
        activity_name: Name of the activity
        validation_errors: List of validation error messages
        invalid_fields: Optional dictionary of field errors
        corrected_input: Optional corrected input
        start_time: Optional start time (defaults to now)

    Returns:
        ValidationErrorResult instance
    """
    error = ActivityError(
        error_type="ValidationError",
        error_message=f"Activity {activity_name} input validation failed",
        error_details={"validation_errors": validation_errors},
        is_retryable=False,
    )

    return ValidationErrorResult(
        activity_name=activity_name,
        error=error,
        validation_errors=validation_errors,
        invalid_fields=invalid_fields or {},
        corrected_input=corrected_input,
        start_time=start_time or datetime.utcnow(),
        end_time=datetime.utcnow(),
    )
