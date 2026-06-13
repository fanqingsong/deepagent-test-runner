"""
Tests for NLStepExecutionStrategy.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.temporal.strategies.nl_step_execution_strategy import NLStepExecutionStrategy
from app.temporal.strategies.execution_strategy import ExecutionContext


class TestNLStepExecutionStrategy:
    """Tests for NLStepExecutionStrategy (deprecated)."""

    def test_can_handle_with_nl_steps_mode(self):
        """Test can_handle returns True for nl_steps mode."""
        assert NLStepExecutionStrategy.can_handle("nl_steps", None) is True
        assert NLStepExecutionStrategy.can_handle("nl_steps", "any_status") is True

    def test_can_handle_with_different_mode(self):
        """Test can_handle returns False for non-nl_steps modes."""
        assert NLStepExecutionStrategy.can_handle("script", None) is False
        assert NLStepExecutionStrategy.can_handle("custom", None) is False

    def test_validate_context_with_test_steps(self):
        """Test validate_context with valid nl_steps context."""
        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],  # Has steps
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        # Should not raise exception, but should log deprecation warning
        strategy.validate_context(context)

    def test_validate_context_without_test_steps(self):
        """Test validate_context without test steps."""
        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],  # Empty steps
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        with pytest.raises(ValueError, match="No test steps provided"):
            strategy.validate_context(context)

    @pytest.mark.asyncio
    async def test_execute_returns_deprecation_error(self):
        """Test that execute returns deprecation error."""
        page = Mock()
        page.goto = AsyncMock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        result = await strategy.execute(context)

        assert result.status == "error"
        assert "deprecated" in result.error.lower()
        assert "no longer supported" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_navigates_to_url(self):
        """Test that execute navigates to URL before returning error."""
        page = Mock()
        page.goto = AsyncMock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        result = await strategy.execute(context)

        # Should navigate even though mode is deprecated
        page.goto.assert_called_once_with(
            "https://example.com", wait_until="domcontentloaded", timeout=30000
        )
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_execute_without_url(self):
        """Test execute without URL."""
        page = Mock()
        page.goto = AsyncMock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url=None,  # No URL
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        result = await strategy.execute(context)

        # Should not navigate if no URL
        page.goto.assert_not_called()
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_execute_with_validation_error(self):
        """Test execute with validation error."""
        page = Mock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],  # Invalid: no steps
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        result = await strategy.execute(context)

        assert result.status == "error"
        assert "No test steps provided" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test execute with runtime exception."""
        page = Mock()
        page.goto = AsyncMock(side_effect=Exception("Navigation failed"))

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()
        result = await strategy.execute(context)

        assert result.status == "error"
        assert "Navigation failed" in result.error


class TestNLStepExecutionStrategyDeprecation:
    """Tests for deprecation warnings and messages."""

    @pytest.mark.asyncio
    async def test_deprecation_message_contains_helpful_info(self, caplog):
        """Test that deprecation message contains migration guidance."""
        import logging

        page = Mock()
        page.goto = AsyncMock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[{"step": "click button"}],
            environment={},
            mode="execute_only",
            playwright_script=None,
            script_status=None,
        )

        strategy = NLStepExecutionStrategy()

        with caplog.at_level(logging.WARNING):
            result = await strategy.execute(context)

        # Check that deprecation warning was logged
        assert any("deprecated" in record.message.lower() for record in caplog.records)

        # Check error message content
        assert result.status == "error"
        assert "deprecated" in result.error.lower()
        assert "script mode" in result.error.lower()
        assert "playwright scripts" in result.error.lower()
