"""
Base Activity Implementation

Abstract base class implementing the IActivity interface.
Provides common functionality for all activities to reduce code duplication
and ensure consistency.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Generic, TypeVar

from temporalio import activity as temporal_activity

from .activity_interface import IActivity, ActivityInput, ActivityOutput, ActivityError
from .activity_result_types import (
    ActivityResult,
    SuccessResult,
    ErrorResult,
    TimeoutResult,
    ValidationErrorResult,
    create_success_result,
    create_error_result,
    create_timeout_result,
    create_validation_error_result,
)

InputType = TypeVar("InputType", bound=ActivityInput)
OutputType = TypeVar("OutputType", bound=ActivityOutput)


class BaseActivity(IActivity[InputType, OutputType], Generic[InputType, OutputType]):
    """
    Abstract base class for all Temporal activities.

    This class provides common functionality for activities:
    - Input validation with error collection
    - Standardized error handling
    - Structured logging
    - Metrics collection hooks
    - Retry policy integration

    Activities should inherit from this class and implement:
    - validate_input() - Input-specific validation
    - execute_impl() - Activity-specific business logic

    The base class handles the rest (logging, error handling, etc.).
    """

    def __init__(self):
        """Initialize the activity with logger."""
        self._logger = logging.getLogger(f"activity.{self.get_activity_name()}")
        self._start_time: datetime = None

    async def validate_input(self, input_data: InputType) -> bool:
        """
        Validate activity input before execution.

        This implementation provides basic validation. Subclasses can override
        to add input-specific validation logic.

        Args:
            input_data: Activity input to validate

        Returns:
            True if input is valid

        Raises:
            ValueError: If validation fails
        """
        if not input_data:
            raise ValueError(f"{self.get_activity_name()}: Input data cannot be None")

        # Validate required fields
        if hasattr(input_data, "activity_id") and input_data.activity_id:
            self._logger.debug(f"Validating activity {input_data.activity_id}")

        return True

    async def execute(self, input_data: InputType) -> OutputType:
        """
        Execute the activity with full lifecycle management.

        This method orchestrates the complete activity lifecycle:
        1. Log start
        2. Validate input
        3. Execute implementation
        4. Handle errors
        5. Log completion
        6. Collect metrics

        Args:
            input_data: Validated activity input

        Returns:
            ActivityOutput with execution results

        Raises:
            Exception: If execution fails (after error handling)
        """
        self._start_time = datetime.utcnow()
        activity_id = getattr(input_data, "activity_id", None)

        # Log activity start
        self.log_start(input_data)

        # Validate input
        try:
            await self.validate_input(input_data)
        except Exception as validation_error:
            self._logger.error(f"Input validation failed: {validation_error}")
            error = await self.handle_error(validation_error, input_data)
            self.log_error(error, input_data)
            raise

        # Execute implementation
        try:
            self._logger.info(
                f"Executing {self.get_activity_name()}"
                + (f" (activity_id={activity_id})" if activity_id else "")
            )

            output_data = await self.execute_impl(input_data)

            # Add execution metadata
            if hasattr(output_data, "activity_id"):
                output_data.activity_id = getattr(input_data, "activity_id", None)
            if hasattr(output_data, "activity_name"):
                output_data.activity_name = self.get_activity_name()
            if hasattr(output_data, "execution_time"):
                output_data.execution_time = datetime.utcnow()
            if hasattr(output_data, "duration_ms"):
                output_data.duration_ms = int(
                    (datetime.utcnow() - self._start_time).total_seconds() * 1000
                )

            # Log completion
            self.log_complete(output_data)

            return output_data

        except Exception as exec_error:
            self._logger.error(f"Execution failed: {exec_error}", exc_info=True)
            error = await self.handle_error(exec_error, input_data)
            self.log_error(error, input_data)

            # Re-raise for Temporal to handle
            raise

    async def execute_impl(self, input_data: InputType) -> OutputType:
        """
        Implement the activity-specific business logic.

        Subclasses MUST implement this method with their specific logic.

        Args:
            input_data: Validated activity input

        Returns:
            ActivityOutput with execution results

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute_impl()"
        )

    async def handle_error(
        self, error: Exception, input_data: InputType
    ) -> ActivityError:
        """
        Handle activity errors in a standardized way.

        This implementation provides basic error classification. Subclasses
        can override to add error-specific handling.

        Args:
            error: The exception that occurred
            input_data: Input data that caused the error

        Returns:
            Standardized ActivityError object
        """
        error_type = error.__class__.__name__
        error_message = str(error)
        is_retryable = True

        # Classify error type
        if error_type in ["ValidationError", "ValueError", "TypeError"]:
            is_retryable = False
        elif error_type in ["TimeoutError", "asyncio.TimeoutError"]:
            is_retryable = False
        elif error_type in ["ConnectionError", "OperationalError"]:
            is_retryable = True

        # Build error context
        context = {
            "activity_name": self.get_activity_name(),
            "activity_id": getattr(input_data, "activity_id", None),
            "correlation_id": getattr(input_data, "correlation_id", None),
            "error_time": datetime.utcnow().isoformat(),
        }

        return ActivityError(
            error_type=error_type,
            error_message=error_message,
            is_retryable=is_retryable,
            stack_trace=traceback.format_exc(),
            context=context,
        )

    def log_start(self, input_data: InputType) -> None:
        """
        Log activity start event with structured logging.

        Args:
            input_data: Activity input data
        """
        activity_id = getattr(input_data, "activity_id", None)
        correlation_id = getattr(input_data, "correlation_id", None)

        # Get Temporal activity info if available
        activity_info = self.get_activity_info()
        attempt = activity_info.attempt if activity_info else 1

        log_data = {
            "event": "activity_start",
            "activity_name": self.get_activity_name(),
            "activity_id": activity_id,
            "correlation_id": correlation_id,
            "attempt": attempt,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._logger.info(f"Starting {self.get_activity_name()}", extra=log_data)

    def log_complete(self, output_data: OutputType) -> None:
        """
        Log activity completion event with structured logging.

        Args:
            output_data: Activity output data
        """
        activity_id = getattr(output_data, "activity_id", None)
        duration_ms = getattr(output_data, "duration_ms", 0)

        log_data = {
            "event": "activity_complete",
            "activity_name": self.get_activity_name(),
            "activity_id": activity_id,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._logger.info(
            f"Completed {self.get_activity_name()} in {duration_ms}ms",
            extra=log_data,
        )

    def log_error(self, error: ActivityError, input_data: InputType) -> None:
        """
        Log activity error event with structured logging.

        Args:
            error: Activity error details
            input_data: Activity input data
        """
        activity_id = getattr(input_data, "activity_id", None)

        log_data = {
            "event": "activity_error",
            "activity_name": self.get_activity_name(),
            "activity_id": activity_id,
            "error_type": error.error_type,
            "is_retryable": error.is_retryable,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._logger.error(
            f"Error in {self.get_activity_name()}: {error.error_message}",
            extra=log_data,
        )

    def get_activity_name(self) -> str:
        """Get the activity name for logging and tracking."""
        return self.__class__.__name__.replace("Activity", "")

    def get_logger(self) -> logging.Logger:
        """Get logger instance for this activity."""
        return self._logger

    def get_activity_info(self) -> Any:
        """Get Temporal activity info if available."""
        try:
            return temporal_activity.info()
        except Exception:
            return None

    def collect_metrics(self, input_data: InputType, output_data: OutputType) -> Dict[str, Any]:
        """
        Collect performance metrics for the activity execution.

        Subclasses can override this to collect custom metrics.

        Args:
            input_data: Activity input data
            output_data: Activity output data

        Returns:
            Dictionary of metrics
        """
        duration_ms = getattr(output_data, "duration_ms", 0)

        metrics = {
            "activity_name": self.get_activity_name(),
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add activity-specific metrics from output
        if hasattr(output_data, "metadata"):
            metrics.update(output_data.metadata)

        return metrics

    def should_retry(self, error: ActivityError, attempt: int) -> bool:
        """
        Determine if an activity should be retried based on error and attempt count.

        Args:
            error: The error that occurred
            attempt: Current attempt number (1-based)

        Returns:
            True if activity should be retried
        """
        if not error.is_retryable:
            return False

        # Default max attempts is 3
        max_attempts = 3
        return attempt < max_attempts

    def get_retry_delay_seconds(self, error: ActivityError, attempt: int) -> int:
        """
        Calculate retry delay based on error type and attempt number.

        Args:
            error: The error that occurred
            attempt: Current attempt number (1-based)

        Returns:
            Delay in seconds before next retry
        """
        # Exponential backoff: 2^attempt seconds, max 60 seconds
        delay = min(2 ** attempt, 60)
        return delay
