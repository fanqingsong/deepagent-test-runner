"""
Unit tests for BaseActivity.

Tests the base activity implementation and common functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.temporal.interfaces.base_activity import BaseActivity
from app.temporal.interfaces.activity_interface import (
    ActivityInput,
    ActivityOutput,
    ActivityError,
)
from app.temporal.interfaces.activity_result_types import (
    SuccessResult,
    ErrorResult,
    ActivityStatus,
)


class MockInput(ActivityInput):
    """Mock input for testing."""

    test_field: str = "test_value"


class MockOutput(ActivityOutput):
    """Mock output for testing."""

    result_field: str = "result_value"


class MockActivity(BaseActivity[MockInput, MockOutput]):
    """Mock activity for testing."""

    def __init__(self):
        super().__init__()
        self.execute_impl_called = False
        self.validate_input_called = False

    async def validate_input(self, input_data: MockInput) -> bool:
        """Mock validation."""
        self.validate_input_called = True
        await super().validate_input(input_data)
        if not input_data.test_field:
            raise ValueError("test_field is required")
        return True

    async def execute_impl(self, input_data: MockInput) -> MockOutput:
        """Mock implementation."""
        self.execute_impl_called = True
        return MockOutput(
            result_field=f"processed_{input_data.test_field}",
        )


class TestBaseActivity:
    """Test BaseActivity implementation."""

    @pytest.mark.asyncio
    async def test_base_activity_initialization(self):
        """Test BaseActivity initialization."""
        activity = MockActivity()

        assert activity.get_activity_name() == "Mock"
        assert activity.get_logger() is not None

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful activity execution."""
        activity = MockActivity()
        input_data = MockInput(test_field="test_value")

        output = await activity.execute(input_data)

        assert isinstance(output, MockOutput)
        assert output.result_field == "processed_test_value"
        assert activity.execute_impl_called is True
        assert activity.validate_input_called is True

    @pytest.mark.asyncio
    async def test_execute_validation_failure(self):
        """Test activity execution with validation failure."""
        activity = MockActivity()
        input_data = MockInput(test_field="")  # Invalid input

        with pytest.raises(ValueError, match="test_field is required"):
            await activity.execute(input_data)

        assert activity.validate_input_called is True
        assert activity.execute_impl_called is False

    @pytest.mark.asyncio
    async def test_execute_implementation_failure(self):
        """Test activity execution with implementation failure."""

        class FailingActivity(MockActivity):
            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                raise RuntimeError("Implementation failed")

        activity = FailingActivity()
        input_data = MockInput(test_field="test_value")

        with pytest.raises(RuntimeError, match="Implementation failed"):
            await activity.execute(input_data)

        assert activity.execute_impl_called is True

    @pytest.mark.asyncio
    async def test_validate_input_defaults(self):
        """Test default validation logic."""
        activity = MockActivity()

        # Should raise ValueError for None input
        with pytest.raises(ValueError, match="Input data cannot be None"):
            await activity.validate_input(None)

        # Should pass for valid input
        input_data = MockInput(test_field="test")
        result = await activity.validate_input(input_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_error_classification(self):
        """Test error classification in handle_error."""
        activity = MockActivity()
        input_data = MockInput(test_field="test")

        # Test ValidationError (not retryable)
        validation_error = ValueError("Invalid input")
        error_result = await activity.handle_error(validation_error, input_data)

        assert isinstance(error_result, ActivityError)
        assert error_result.error_type == "ValueError"
        assert error_result.is_retryable is False

        # Test ConnectionError (retryable)
        connection_error = ConnectionError("Database unavailable")
        error_result = await activity.handle_error(connection_error, input_data)

        assert isinstance(error_result, ActivityError)
        assert error_result.error_type == "ConnectionError"
        assert error_result.is_retryable is True

        # Test TimeoutError (not retryable)
        timeout_error = TimeoutError("Operation timed out")
        error_result = await activity.handle_error(timeout_error, input_data)

        assert isinstance(error_result, ActivityError)
        assert error_result.error_type == "TimeoutError"
        assert error_result.is_retryable is False

    @pytest.mark.asyncio
    async def test_log_start(self):
        """Test log_start method."""
        activity = MockActivity()
        input_data = MockInput(
            activity_id="test-123",
            correlation_id="corr-456",
            test_field="test",
        )

        with patch.object(activity.get_logger(), 'info') as mock_log:
            activity.log_start(input_data)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "Starting Mock" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_log_complete(self):
        """Test log_complete method."""
        activity = MockActivity()
        output_data = MockOutput(
            activity_id="test-123",
            result_field="result",
            duration_ms=1500,
        )

        with patch.object(activity.get_logger(), 'info') as mock_log:
            activity.log_complete(output_data)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "Completed Mock" in call_args[0][0]
            assert "1500ms" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_log_error(self):
        """Test log_error method."""
        activity = MockActivity()
        input_data = MockInput(test_field="test")
        error = ActivityError(
            error_type="ValueError",
            error_message="Invalid input",
            is_retryable=False,
        )

        with patch.object(activity.get_logger(), 'error') as mock_log:
            activity.log_error(error, input_data)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "Error in Mock" in call_args[0][0]
            assert "Invalid input" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_output_metadata_enrichment(self):
        """Test that output metadata is enriched during execution."""
        activity = MockActivity()
        input_data = MockInput(
            activity_id="test-123",
            test_field="test",
        )

        output = await activity.execute(input_data)

        # Check that metadata was added
        assert output.activity_id == "test-123"
        assert output.activity_name == "Mock"
        assert output.execution_time is not None
        assert output.duration_ms > 0

    @pytest.mark.asyncio
    async def test_collect_metrics(self):
        """Test metrics collection."""
        activity = MockActivity()
        input_data = MockInput(test_field="test")
        output_data = MockOutput(
            duration_ms=1500,
            metadata={"custom_metric": "value"},
        )

        metrics = activity.collect_metrics(input_data, output_data)

        assert metrics["activity_name"] == "Mock"
        assert metrics["duration_ms"] == 1500
        assert metrics["custom_metric"] == "value"
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_should_retry(self):
        """Test retry decision logic."""
        activity = MockActivity()

        # Retryable error
        retryable_error = ActivityError(
            error_type="ConnectionError",
            error_message="Database unavailable",
            is_retryable=True,
        )

        assert activity.should_retry(retryable_error, 1) is True
        assert activity.should_retry(retryable_error, 2) is True
        assert activity.should_retry(retryable_error, 3) is False  # Max attempts

        # Non-retryable error
        non_retryable_error = ActivityError(
            error_type="ValidationError",
            error_message="Invalid input",
            is_retryable=False,
        )

        assert activity.should_retry(non_retryable_error, 1) is False

    @pytest.mark.asyncio
    async def test_get_retry_delay_seconds(self):
        """Test retry delay calculation."""
        activity = MockActivity()
        error = ActivityError(
            error_type="ConnectionError",
            error_message="Database unavailable",
        )

        # Exponential backoff: 2^attempt, max 60 seconds
        assert activity.get_retry_delay_seconds(error, 1) == 2
        assert activity.get_retry_delay_seconds(error, 2) == 4
        assert activity.get_retry_delay_seconds(error, 3) == 8
        assert activity.get_retry_delay_seconds(error, 4) == 16
        assert activity.get_retry_delay_seconds(error, 5) == 32
        assert activity.get_retry_delay_seconds(error, 6) == 60  # Capped
        assert activity.get_retry_delay_seconds(error, 10) == 60  # Still capped

    @pytest.mark.asyncio
    async def test_get_activity_info(self):
        """Test getting Temporal activity info."""
        activity = MockActivity()

        # Should not raise exception even if not in Temporal context
        info = activity.get_activity_info()
        # Outside Temporal context, should return None
        assert info is None

    @pytest.mark.asyncio
    async def test_not_implemented_error(self):
        """Test that NotImplementedError is raised if execute_impl not implemented."""

        class IncompleteActivity(BaseActivity[MockInput, MockOutput]):
            pass

        activity = IncompleteActivity()
        input_data = MockInput(test_field="test")

        with pytest.raises(NotImplementedError, match="must implement execute_impl"):
            await activity.execute(input_data)


class TestActivityExecutionFlow:
    """Test complete activity execution flow."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execution flow with logging and metrics."""
        activity = MockActivity()
        input_data = MockInput(
            activity_id="test-123",
            correlation_id="corr-456",
            test_field="test_value",
        )

        with patch.object(activity.get_logger(), 'info') as mock_log:
            output = await activity.execute(input_data)

            # Verify execution
            assert output.result_field == "processed_test_value"

            # Verify logging calls
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("Starting" in call for call in log_calls)
            assert any("Completed" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_execution_with_error_recovery(self):
        """Test error handling and recovery."""

        class RecoveryActivity(MockActivity):
            def __init__(self):
                super().__init__()
                self.attempt_count = 0

            async def execute_impl(self, input_data: MockInput) -> MockOutput:
                self.attempt_count += 1
                if self.attempt_count == 1:
                    raise ConnectionError("Temporary failure")
                return MockOutput(result_field="recovered")

        activity = RecoveryActivity()
        input_data = MockInput(test_field="test")

        # First attempt should fail
        with pytest.raises(ConnectionError):
            await activity.execute(input_data)

        assert activity.attempt_count == 1

        # Second attempt would succeed (simulating retry)
        # In real scenario, Temporal would handle retry
