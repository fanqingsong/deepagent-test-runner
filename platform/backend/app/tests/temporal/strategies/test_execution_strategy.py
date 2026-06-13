"""
Tests for Execution Strategy base classes and interfaces.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.temporal.strategies.execution_strategy import (
    ExecutionStrategy,
    ExecutionContext,
    ExecutionResult,
)


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_create_context_with_minimal_fields(self):
        """Test creating context with required fields only."""
        page = Mock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        assert context.run_id == "test-run-1"
        assert context.test_definition_id == "test-def-1"
        assert context.page == page
        assert context.metadata == {}  # Should be initialized

    def test_create_context_with_all_fields(self):
        """Test creating context with all fields."""
        page = Mock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click"}],
            environment={"key": "value"},
            mode="execute_only",
            playwright_script="const page = await context.newPage();",
            script_status="approved",
            metadata={"custom": "value"},
        )

        assert context.url == "https://example.com"
        assert context.test_goal == "Test goal"
        assert context.playwright_script == "const page = await context.newPage();"
        assert context.script_status == "approved"
        assert context.metadata == {"custom": "value"}

    def test_create_context_with_none_metadata(self):
        """Test that metadata is initialized when None is passed."""
        page = Mock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
            metadata=None,  # Explicitly pass None
        )

        assert context.metadata == {}


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_result_with_minimal_fields(self):
        """Test creating result with required fields only."""
        start_time = int(datetime.utcnow().timestamp() * 1000)
        end_time = start_time + 1000

        result = ExecutionResult(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            status="passed",
            test_cases=[],
            error=None,
            start_time=start_time,
            end_time=end_time,
            total_duration=1000,
            total_tests=1,
            passed=1,
            failed=0,
            skipped=0,
        )

        assert result.run_id == "test-run-1"
        assert result.status == "passed"
        assert result.metadata == {}  # Should be initialized

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        start_time = int(datetime.utcnow().timestamp() * 1000)
        end_time = start_time + 1000

        result = ExecutionResult(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            status="passed",
            test_cases=[{"step": "click", "status": "passed"}],
            error=None,
            start_time=start_time,
            end_time=end_time,
            total_duration=1000,
            total_tests=1,
            passed=1,
            failed=0,
            skipped=0,
            metadata={"custom": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["run_id"] == "test-run-1"
        assert result_dict["status"] == "passed"
        assert result_dict["test_cases"] == [{"step": "click", "status": "passed"}]
        assert result_dict["metadata"] == {"custom": "value"}
        assert result_dict["total_duration"] == 1000


class TestExecutionStrategy:
    """Tests for ExecutionStrategy abstract base class."""

    def test_cannot_instantiate_base_class(self):
        """Test that ExecutionStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ExecutionStrategy()

    def test_create_error_result(self):
        """Test create_error_result helper method."""

        class ConcreteStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return True

            async def execute(self, context):
                pass

        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = ConcreteStrategy()
        start_time = int(datetime.utcnow().timestamp() * 1000)

        error_result = strategy.create_error_result(context, "Test error", start_time)

        assert error_result.status == "error"
        assert error_result.error == "Test error"
        assert error_result.run_id == "test-run-1"
        assert error_result.total_tests == 0
        assert error_result.passed == 0
        assert error_result.failed == 0

    def test_validate_context_with_valid_context(self):
        """Test validate_context with valid context."""

        class ConcreteStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return True

            async def execute(self, context):
                pass

        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = ConcreteStrategy()
        # Should not raise any exception
        strategy.validate_context(context)

    def test_validate_context_with_missing_run_id(self):
        """Test validate_context with missing run_id."""

        class ConcreteStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return True

            async def execute(self, context):
                pass

        page = Mock()
        context = ExecutionContext(
            run_id="",  # Empty run_id
            test_definition_id="test-def-1",
            page=page,
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = ConcreteStrategy()
        with pytest.raises(ValueError, match="run_id is required"):
            strategy.validate_context(context)

    def test_validate_context_with_missing_page(self):
        """Test validate_context with missing page."""

        class ConcreteStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return True

            async def execute(self, context):
                pass

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=None,  # Missing page
            url=None,
            test_goal=None,
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = ConcreteStrategy()
        with pytest.raises(ValueError, match="page is required"):
            strategy.validate_context(context)

    def test_concrete_strategy_must_implement_abstract_methods(self):
        """Test that concrete strategy must implement abstract methods."""

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):

            class IncompleteStrategy(ExecutionStrategy):
                # Missing can_handle and execute methods
                pass

            IncompleteStrategy()

    def test_concrete_strategy_with_valid_implementation(self):
        """Test that concrete strategy with all methods works."""

        class ValidStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "valid"

            async def execute(self, context):
                return ExecutionResult(
                    run_id=context.run_id,
                    test_definition_id=context.test_definition_id,
                    status="passed",
                    test_cases=[],
                    error=None,
                    start_time=int(datetime.utcnow().timestamp() * 1000),
                    end_time=int(datetime.utcnow().timestamp() * 1000) + 100,
                    total_duration=100,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                )

        # Should not raise any exception
        strategy = ValidStrategy()
        assert strategy.can_handle("valid") is True
        assert strategy.can_handle("invalid") is False
