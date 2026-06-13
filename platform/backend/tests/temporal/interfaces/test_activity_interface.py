"""
Unit tests for Activity Interface.

Tests the standardized activity interface compliance.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.temporal.interfaces.activity_interface import (
    IActivity,
    ActivityInput,
    ActivityOutput,
    ActivityError,
)
from app.temporal.interfaces.activity_result_types import (
    ActivityResult,
    SuccessResult,
    ErrorResult,
    TimeoutResult,
    ValidationErrorResult,
    ActivityStatus,
    create_success_result,
    create_error_result,
    create_timeout_result,
    create_validation_error_result,
)


class TestActivityInput:
    """Test ActivityInput base class."""

    def test_activity_input_creation(self):
        """Test creating ActivityInput."""
        input_data = ActivityInput(
            activity_id="test-123",
            activity_name="TestActivity",
            correlation_id="corr-456",
        )

        assert input_data.activity_id == "test-123"
        assert input_data.activity_name == "TestActivity"
        assert input_data.correlation_id == "corr-456"
        assert input_data.metadata == {}

    def test_activity_input_defaults(self):
        """Test ActivityInput default values."""
        input_data = ActivityInput()

        assert input_data.activity_id is None
        assert input_data.activity_name is None
        assert input_data.correlation_id is None
        assert input_data.metadata == {}

    def test_activity_input_auto_detect_name(self):
        """Test automatic activity name detection."""
        class CustomInput(ActivityInput):
            pass

        input_data = CustomInput()
        assert input_data.activity_name == "Custom"

    def test_activity_input_metadata(self):
        """Test metadata functionality."""
        input_data = ActivityInput()
        input_data.metadata["key1"] = "value1"
        input_data.metadata["key2"] = 123

        assert len(input_data.metadata) == 2
        assert input_data.metadata["key1"] == "value1"
        assert input_data.metadata["key2"] == 123


class TestActivityOutput:
    """Test ActivityOutput base class."""

    def test_activity_output_creation(self):
        """Test creating ActivityOutput."""
        output = ActivityOutput(
            activity_id="test-123",
            activity_name="TestActivity",
            duration_ms=1500,
        )

        assert output.activity_id == "test-123"
        assert output.activity_name == "TestActivity"
        assert output.duration_ms == 1500
        assert isinstance(output.execution_time, datetime)

    def test_activity_output_defaults(self):
        """Test ActivityOutput default values."""
        output = ActivityOutput()

        assert output.activity_id is None
        assert output.activity_name is None
        assert output.duration_ms == 0
        assert output.metadata == {}
        assert isinstance(output.execution_time, datetime)


class TestActivityError:
    """Test ActivityError class."""

    def test_activity_error_creation(self):
        """Test creating ActivityError."""
        error = ActivityError(
            error_type="ValueError",
            error_message="Invalid input",
            is_retryable=False,
            retry_after_seconds=60,
        )

        assert error.error_type == "ValueError"
        assert error.error_message == "Invalid input"
        assert error.is_retryable is False
        assert error.retry_after_seconds == 60

    def test_activity_error_defaults(self):
        """Test ActivityError default values."""
        error = ActivityError(
            error_type="RuntimeError",
            error_message="Something went wrong",
        )

        assert error.is_retryable is True  # Default
        assert error.retry_after_seconds is None
        assert error.error_details == {}
        assert error.context == {}

    def test_activity_error_to_dict(self):
        """Test ActivityError serialization."""
        error = ActivityError(
            error_type="ValueError",
            error_message="Invalid input",
            error_details={"field": "test_id"},
            is_retryable=False,
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "ValueError"
        assert error_dict["error_message"] == "Invalid input"
        assert error_dict["is_retryable"] is False
        assert error_dict["error_details"]["field"] == "test_id"


class TestActivityResult:
    """Test ActivityResult base class."""

    def test_activity_result_creation(self):
        """Test creating ActivityResult."""
        result = ActivityResult(
            status=ActivityStatus.SUCCESS,
            activity_name="TestActivity",
        )

        assert result.status == ActivityStatus.SUCCESS
        assert result.activity_name == "TestActivity"
        assert isinstance(result.start_time, datetime)
        assert result.end_time is None
        assert result.duration_ms == 0

    def test_activity_result_is_success(self):
        """Test is_success method."""
        result = ActivityResult(
            status=ActivityStatus.SUCCESS,
            activity_name="TestActivity",
        )

        assert result.is_success() is True
        assert result.is_failure() is False

    def test_activity_result_is_failure(self):
        """Test is_failure method."""
        result = ActivityResult(
            status=ActivityStatus.FAILED,
            activity_name="TestActivity",
        )

        assert result.is_success() is False
        assert result.is_failure() is True

    def test_activity_result_timeout(self):
        """Test timeout status."""
        result = ActivityResult(
            status=ActivityStatus.TIMEOUT,
            activity_name="TestActivity",
        )

        assert result.is_success() is False
        assert result.is_failure() is True

    def test_activity_result_duration_calculation(self):
        """Test automatic duration calculation."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 5)  # 5 seconds later

        result = ActivityResult(
            status=ActivityStatus.SUCCESS,
            activity_name="TestActivity",
            start_time=start,
            end_time=end,
        )

        # Should calculate 5000ms (5 seconds)
        assert result.duration_ms == 5000

    def test_activity_result_to_dict(self):
        """Test ActivityResult serialization."""
        result = ActivityResult(
            status=ActivityStatus.SUCCESS,
            activity_name="TestActivity",
            duration_ms=1000,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "success"
        assert result_dict["activity_name"] == "TestActivity"
        assert result_dict["duration_ms"] == 1000
        assert result_dict["error"] is None


class TestSuccessResult:
    """Test SuccessResult class."""

    def test_success_result_creation(self):
        """Test creating SuccessResult."""
        result = SuccessResult(
            activity_name="TestActivity",
            data={"test_key": "test_value"},
            message="Activity completed successfully",
        )

        assert result.status == ActivityStatus.SUCCESS
        assert result.data == {"test_key": "test_value"}
        assert result.message == "Activity completed successfully"

    def test_success_result_to_dict(self):
        """Test SuccessResult serialization."""
        result = SuccessResult(
            activity_name="TestActivity",
            data={"result": "passed"},
            message="Success",
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "success"
        assert result_dict["data"]["result"] == "passed"
        assert result_dict["message"] == "Success"


class TestErrorResult:
    """Test ErrorResult class."""

    def test_error_result_creation(self):
        """Test creating ErrorResult."""
        error = ActivityError(
            error_type="ValueError",
            error_message="Invalid input",
            is_retryable=False,
        )

        result = ErrorResult(
            activity_name="TestActivity",
            error=error,
            error_details={"field": "test_id"},
        )

        assert result.status == ActivityStatus.FAILED
        assert result.error.error_type == "ValueError"
        assert result.error_details["field"] == "test_id"

    def test_error_result_retryable(self):
        """Test retryable status."""
        error_retryable = ActivityError(
            error_type="ConnectionError",
            error_message="Connection failed",
            is_retryable=True,
        )

        result = ErrorResult(
            activity_name="TestActivity",
            error=error_retryable,
        )

        assert result.is_retryable() is True

    def test_error_result_not_retryable(self):
        """Test non-retryable status."""
        error_not_retryable = ActivityError(
            error_type="ValidationError",
            error_message="Invalid input",
            is_retryable=False,
        )

        result = ErrorResult(
            activity_name="TestActivity",
            error=error_not_retryable,
        )

        assert result.is_retryable() is False


class TestTimeoutResult:
    """Test TimeoutResult class."""

    def test_timeout_result_creation(self):
        """Test creating TimeoutResult."""
        result = TimeoutResult(
            activity_name="TestActivity",
            timeout_seconds=60,
            progress_before_timeout=75.0,
        )

        assert result.status == ActivityStatus.TIMEOUT
        assert result.timeout_seconds == 60
        assert result.progress_before_timeout == 75.0

    def test_timeout_result_not_retryable(self):
        """Test timeout is not retryable."""
        error = ActivityError(
            error_type="TimeoutError",
            error_message="Activity timed out",
            is_retryable=True,  # Try to set as retryable
        )

        result = TimeoutResult(
            activity_name="TestActivity",
            error=error,
            timeout_seconds=60,
        )

        # Should be overridden to False
        assert result.error.is_retryable is False
        assert result.is_retryable() is False


class TestValidationErrorResult:
    """Test ValidationErrorResult class."""

    def test_validation_error_result_creation(self):
        """Test creating ValidationErrorResult."""
        result = ValidationErrorResult(
            activity_name="TestActivity",
            validation_errors=["Field 'test_id' is required"],
            invalid_fields={"test_id": "Required field missing"},
        )

        assert result.status == ActivityStatus.VALIDATION_ERROR
        assert len(result.validation_errors) == 1
        assert result.invalid_fields["test_id"] == "Required field missing"

    def test_validation_error_result_not_retryable(self):
        """Test validation errors are not retryable."""
        result = ValidationErrorResult(
            activity_name="TestActivity",
            validation_errors=["Invalid input"],
        )

        assert result.is_retryable() is False


class TestResultFactoryFunctions:
    """Test result factory functions."""

    def test_create_success_result(self):
        """Test create_success_result factory."""
        result = create_success_result(
            activity_name="TestActivity",
            data={"result": "passed"},
            message="Success",
        )

        assert isinstance(result, SuccessResult)
        assert result.activity_name == "TestActivity"
        assert result.data["result"] == "passed"
        assert result.message == "Success"

    def test_create_error_result(self):
        """Test create_error_result factory."""
        error = ActivityError(
            error_type="ValueError",
            error_message="Invalid input",
        )

        result = create_error_result(
            activity_name="TestActivity",
            error=error,
            error_details={"field": "test_id"},
        )

        assert isinstance(result, ErrorResult)
        assert result.error.error_type == "ValueError"
        assert result.error_details["field"] == "test_id"

    def test_create_timeout_result(self):
        """Test create_timeout_result factory."""
        result = create_timeout_result(
            activity_name="TestActivity",
            timeout_seconds=60,
            progress_before_timeout=50.0,
        )

        assert isinstance(result, TimeoutResult)
        assert result.timeout_seconds == 60
        assert result.progress_before_timeout == 50.0

    def test_create_validation_error_result(self):
        """Test create_validation_error_result factory."""
        result = create_validation_error_result(
            activity_name="TestActivity",
            validation_errors=["Invalid input"],
            invalid_fields={"field": "value"},
        )

        assert isinstance(result, ValidationErrorResult)
        assert result.validation_errors == ["Invalid input"]
        assert result.invalid_fields["field"] == "value"
