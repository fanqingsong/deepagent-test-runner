"""
Activity Interface

Defines the standard interface that all Temporal activities must follow.
This ensures Liskov Substitution Principle compliance.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic

from temporalio import activity

# Type variables for generic input/output
InputType = TypeVar("InputType", bound="ActivityInput")
OutputType = TypeVar("OutputType", bound="ActivityOutput")


@dataclass
class ActivityInput:
    """
    Base class for all activity inputs.

    All activity input dataclasses should inherit from this class to ensure
    consistency across activities and support Liskov Substitution Principle.

    Attributes:
        activity_id: Optional unique identifier for this activity invocation
        activity_name: Name of the activity being executed
        correlation_id: Optional correlation ID for tracking across activities
        metadata: Optional metadata dictionary for extensibility
    """

    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation."""
        if self.activity_name is None:
            # Auto-detect activity name from class if not provided
            self.activity_name = self.__class__.__name__.replace("Input", "")


@dataclass
class ActivityOutput:
    """
    Base class for all activity outputs.

    All activity output dataclasses should inherit from this class to ensure
    consistency across activities and support Liskov Substitution Principle.

    Attributes:
        activity_id: Optional unique identifier (should match input)
        activity_name: Name of the activity that was executed
        correlation_id: Optional correlation ID for tracking
        execution_time: Timestamp when activity completed
        duration_ms: Execution duration in milliseconds
        metadata: Optional metadata dictionary for extensibility
    """

    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    correlation_id: Optional[str] = None
    execution_time: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityError:
    """
    Standardized error representation for activities.

    Attributes:
        error_type: Type/class of the error
        error_message: Human-readable error message
        error_details: Additional error details
        is_retryable: Whether this error is retryable
        retry_after_seconds: Suggested retry delay in seconds
        stack_trace: Optional stack trace for debugging
        context: Additional context about when/where error occurred
    """

    error_type: str
    error_message: str
    error_details: Dict[str, Any] = field(default_factory=dict)
    is_retryable: bool = True
    retry_after_seconds: Optional[int] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "is_retryable": self.is_retryable,
            "retry_after_seconds": self.retry_after_seconds,
            "context": self.context,
        }


class IActivity(ABC, Generic[InputType, OutputType]):
    """
    Interface for all Temporal activities.

    This interface defines the contract that all activities must follow,
    ensuring Liskov Substitution Principle compliance. Any activity can be
    swapped with another as long as it implements this interface.

    Activities implementing this interface should:
    1. Accept standardized input (ActivityInput subclass)
    2. Return standardized output (ActivityOutput subclass)
    3. Handle errors consistently
    4. Log activity lifecycle events
    5. Support metrics collection
    """

    @abstractmethod
    async def validate_input(self, input_data: InputType) -> bool:
        """
        Validate activity input before execution.

        Args:
            input_data: Activity input to validate

        Returns:
            True if input is valid, False otherwise

        Raises:
            ValidationError: If input validation fails with details
        """
        pass

    @abstractmethod
    async def execute(self, input_data: InputType) -> OutputType:
        """
        Execute the activity logic.

        This is the main method that implements the activity's business logic.
        It should handle all errors and return a standardized output.

        Args:
            input_data: Validated activity input

        Returns:
            ActivityOutput with execution results

        Raises:
            ActivityError: If execution fails with error details
        """
        pass

    @abstractmethod
    async def handle_error(
        self, error: Exception, input_data: InputType
    ) -> ActivityError:
        """
        Handle activity errors in a standardized way.

        This method should:
        1. Classify the error (retryable, non-retryable, timeout, etc.)
        2. Extract relevant error details
        3. Suggest retry strategy if applicable
        4. Log the error appropriately

        Args:
            error: The exception that occurred
            input_data: Input data that caused the error

        Returns:
            Standardized ActivityError object
        """
        pass

    @abstractmethod
    def log_start(self, input_data: InputType) -> None:
        """
        Log activity start event.

        Args:
            input_data: Activity input data
        """
        pass

    @abstractmethod
    def log_complete(self, output_data: OutputType) -> None:
        """
        Log activity completion event.

        Args:
            output_data: Activity output data
        """
        pass

    @abstractmethod
    def log_error(self, error: ActivityError, input_data: InputType) -> None:
        """
        Log activity error event.

        Args:
            error: Activity error details
            input_data: Activity input data
        """
        pass

    def get_activity_name(self) -> str:
        """
        Get the activity name for logging and tracking.

        Returns:
            Activity name string
        """
        return self.__class__.__name__.replace("Activity", "")

    def get_logger(self) -> logging.Logger:
        """
        Get logger instance for this activity.

        Returns:
            Logger instance with activity context
        """
        return logging.getLogger(f"activity.{self.get_activity_name()}")

    def get_activity_info(self) -> Any:
        """
        Get Temporal activity info if available.

        Returns:
            Temporal activity info object or None
        """
        try:
            return activity.info()
        except Exception:
            return None
