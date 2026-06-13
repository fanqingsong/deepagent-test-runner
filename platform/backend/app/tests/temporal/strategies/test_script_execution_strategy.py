"""
Tests for ScriptExecutionStrategy.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.temporal.strategies.script_execution_strategy import ScriptExecutionStrategy
from app.temporal.strategies.execution_strategy import ExecutionContext


class TestScriptExecutionStrategy:
    """Tests for ScriptExecutionStrategy."""

    def test_can_handle_with_script_mode_and_approved_status(self):
        """Test can_handle returns True for script mode with approved status."""
        assert ScriptExecutionStrategy.can_handle("script", "approved") is True

    def test_can_handle_with_script_mode_and_different_status(self):
        """Test can_handle returns False for script mode with non-approved status."""
        assert ScriptExecutionStrategy.can_handle("script", "draft") is False
        assert ScriptExecutionStrategy.can_handle("script", "validated") is False
        assert ScriptExecutionStrategy.can_handle("script", None) is False

    def test_can_handle_with_different_mode(self):
        """Test can_handle returns False for non-script modes."""
        assert ScriptExecutionStrategy.can_handle("nl_steps", None) is False
        assert ScriptExecutionStrategy.can_handle("custom", None) is False
        assert ScriptExecutionStrategy.can_handle("hybrid", None) is False

    def test_validate_context_with_valid_script(self):
        """Test validate_context with valid script context."""
        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script="const page = await context.newPage();",
            script_status="approved",
        )

        strategy = ScriptExecutionStrategy()
        # Should not raise any exception
        strategy.validate_context(context)

    def test_validate_context_with_missing_script(self):
        """Test validate_context with missing script."""
        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,  # Missing script
            script_status="approved",
        )

        strategy = ScriptExecutionStrategy()
        with pytest.raises(ValueError, match="No Playwright script provided"):
            strategy.validate_context(context)

    def test_validate_context_with_non_approved_status(self):
        """Test validate_context with non-approved script status."""
        page = Mock()
        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script="const page = await context.newPage();",
            script_status="draft",  # Not approved
        )

        strategy = ScriptExecutionStrategy()
        with pytest.raises(ValueError, match="Script must be approved"):
            strategy.validate_context(context)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful script execution."""
        from unittest.mock import patch

        page = Mock()
        page.goto = AsyncMock()

        # Mock execute_script function
        mock_exec_result = {
            "status": "passed",
            "step_results": [
                {"step": "click", "status": "passed"},
                {"step": "wait", "status": "passed"},
            ],
        }

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value=mock_exec_result)):
            context = ExecutionContext(
                run_id="test-run-1",
                test_definition_id="test-def-1",
                page=page,
                url="https://example.com",
                test_goal="Test goal",
                test_steps=[],
                environment={},
                mode="execute_only",
                playwright_script="const page = await context.newPage();",
                script_status="approved",
            )

            strategy = ScriptExecutionStrategy()
            result = await strategy.execute(context)

            assert result.status == "passed"
            assert result.total_tests == 2
            assert result.passed == 1
            assert result.failed == 0
            assert len(result.test_cases) == 2
            assert result.error is None
            assert result.metadata["execution_mode"] == "script"
            assert result.metadata["script_status"] == "approved"

            # Verify navigation was called
            page.goto.assert_called_once_with(
                "https://example.com", wait_until="domcontentloaded", timeout=30000
            )

    @pytest.mark.asyncio
    async def test_execute_with_failure(self):
        """Test script execution with failure."""
        from unittest.mock import patch

        page = Mock()
        page.goto = AsyncMock()

        mock_exec_result = {
            "status": "failed",
            "step_results": [{"step": "click", "status": "failed"}],
            "error": "Element not found",
        }

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value=mock_exec_result)):
            context = ExecutionContext(
                run_id="test-run-1",
                test_definition_id="test-def-1",
                page=page,
                url="https://example.com",
                test_goal="Test goal",
                test_steps=[],
                environment={},
                mode="execute_only",
                playwright_script="const page = await context.newPage();",
                script_status="approved",
            )

            strategy = ScriptExecutionStrategy()
            result = await strategy.execute(context)

            assert result.status == "failed"
            assert result.passed == 0
            assert result.failed == 1
            assert result.error == "Element not found"

    @pytest.mark.asyncio
    async def test_execute_without_url(self):
        """Test script execution without URL."""
        from unittest.mock import patch

        page = Mock()
        page.goto = AsyncMock()  # Should not be called

        mock_exec_result = {"status": "passed", "step_results": []}

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value=mock_exec_result)):
            context = ExecutionContext(
                run_id="test-run-1",
                test_definition_id="test-def-1",
                page=page,
                url=None,  # No URL
                test_goal="Test goal",
                test_steps=[],
                environment={},
                mode="execute_only",
                playwright_script="const page = await context.newPage();",
                script_status="approved",
            )

            strategy = ScriptExecutionStrategy()
            result = await strategy.execute(context)

            assert result.status == "passed"
            page.goto.assert_not_called()  # Should not navigate

    @pytest.mark.asyncio
    async def test_execute_with_validation_error(self):
        """Test execution with validation error."""
        page = Mock()

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script=None,  # Invalid: no script
            script_status="approved",
        )

        strategy = ScriptExecutionStrategy()
        result = await strategy.execute(context)

        assert result.status == "error"
        assert "No Playwright script provided" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test execution with runtime exception."""
        page = Mock()
        page.goto = AsyncMock(side_effect=Exception("Navigation failed"))

        context = ExecutionContext(
            run_id="test-run-1",
            test_definition_id="test-def-1",
            page=page,
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script="const page = await context.newPage();",
            script_status="approved",
        )

        strategy = ScriptExecutionStrategy()
        result = await strategy.execute(context)

        assert result.status == "error"
        assert "Navigation failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_empty_step_results(self):
        """Test execution when script returns no step results."""
        from unittest.mock import patch

        page = Mock()
        page.goto = AsyncMock()

        mock_exec_result = {"status": "passed", "step_results": []}

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value=mock_exec_result)):
            context = ExecutionContext(
                run_id="test-run-1",
                test_definition_id="test-def-1",
                page=page,
                url="https://example.com",
                test_goal="Test goal",
                test_steps=[],
                environment={},
                mode="execute_only",
                playwright_script="const page = await context.newPage();",
                script_status="approved",
            )

            strategy = ScriptExecutionStrategy()
            result = await strategy.execute(context)

            assert result.status == "passed"
            assert result.total_tests == 1  # Default to 1 if no steps
            assert result.passed == 1
            assert result.failed == 0
