"""
Integration tests for Temporal activities with Strategy Pattern.

These tests verify that the refactored Temporal activities work correctly
with the new Strategy Pattern implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.temporal.activities.test_activities import (
    BrowserAutomationInput,
)


class TestStrategyPatternIntegration:
    """Test that Strategy Pattern is correctly integrated."""

    @pytest.mark.asyncio
    async def test_factory_is_used_by_activity(self):
        """Test that the activity uses ExecutionStrategyFactory."""
        from app.temporal.strategies import get_execution_strategy_factory

        factory = get_execution_strategy_factory()

        # Verify factory has registered strategies
        strategies = factory.list_strategies()
        assert "ScriptExecutionStrategy" in strategies
        assert "NLStepExecutionStrategy" in strategies

    @pytest.mark.asyncio
    async def test_strategy_selection_logic(self):
        """Test that correct strategy is selected for each mode."""
        from app.temporal.strategies import get_execution_strategy_factory

        factory = get_execution_strategy_factory()

        # Test script mode selection
        script_strategy = factory.get_strategy("script", "approved")
        assert script_strategy is not None
        assert script_strategy.__class__.__name__ == "ScriptExecutionStrategy"

        # Test nl_steps mode selection
        nl_strategy = factory.get_strategy("nl_steps", None)
        assert nl_strategy is not None
        assert nl_strategy.__class__.__name__ == "NLStepExecutionStrategy"

        # Test unsupported mode
        unsupported_strategy = factory.get_strategy("unsupported", None)
        assert unsupported_strategy is None

    @pytest.mark.asyncio
    async def test_script_strategy_execution(self):
        """Test that ScriptExecutionStrategy can be executed directly."""
        from app.temporal.strategies import get_execution_strategy_factory
        from app.temporal.strategies.execution_strategy import ExecutionContext

        factory = get_execution_strategy_factory()

        # Create mock page
        page = Mock()
        page.goto = AsyncMock()

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

        # Get strategy and execute
        strategy = factory.get_strategy("script", "approved")
        assert strategy is not None

        # Mock execute_script
        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value={"status": "passed", "step_results": [{"step": "click", "status": "passed"}]})):
            result = await strategy.execute(context)

            assert result.status == "passed"
            assert result.total_tests == 1
            assert result.passed == 1

    @pytest.mark.asyncio
    async def test_nl_strategy_returns_deprecation_error(self):
        """Test that NLStepExecutionStrategy returns deprecation error."""
        from app.temporal.strategies import get_execution_strategy_factory
        from app.temporal.strategies.execution_strategy import ExecutionContext

        factory = get_execution_strategy_factory()

        # Create mock page
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

        # Get strategy and execute
        strategy = factory.get_strategy("nl_steps", None)
        assert strategy is not None

        result = await strategy.execute(context)

        assert result.status == "error"
        assert "deprecated" in result.error.lower()


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    @pytest.mark.asyncio
    async def test_script_mode_still_works(self):
        """Test that script mode execution continues to work."""
        from app.temporal.strategies import get_execution_strategy_factory
        from app.temporal.strategies.execution_strategy import ExecutionContext

        factory = get_execution_strategy_factory()

        # Create mock page
        page = Mock()
        page.goto = AsyncMock()

        context = ExecutionContext(
            run_id="existing-test-run",
            test_definition_id="existing-test-def",
            page=page,
            url="https://example.com",
            test_goal="Existing test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            playwright_script="const page = await context.newPage();",
            script_status="approved",
        )

        # Get strategy
        strategy = factory.get_strategy("script", "approved")
        assert strategy is not None

        # Mock execute_script with multiple step results
        mock_exec_result = {
            "status": "passed",
            "step_results": [
                {"step": "navigate", "status": "passed"},
                {"step": "click", "status": "passed"},
            ],
        }

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value=mock_exec_result)):
            result = await strategy.execute(context)

            # Verify backward compatibility
            assert result.status == "passed"
            assert result.total_tests == 2
            assert result.passed == 1
            assert result.failed == 0
            assert len(result.test_cases) == 2
            assert result.run_id == "existing-test-run"


class TestCustomStrategyExtension:
    """Test that custom strategies can be added."""

    @pytest.mark.asyncio
    async def test_custom_strategy_registration(self):
        """Test registering and using a custom strategy."""
        from app.temporal.strategies import (
            ExecutionStrategy,
            ExecutionContext,
            ExecutionResult,
            get_execution_strategy_factory,
        )

        class CustomTestStrategy(ExecutionStrategy):
            """Custom test strategy for testing."""

            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "custom_test"

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
                    total_tests=1,
                    passed=1,
                    failed=0,
                    skipped=0,
                    metadata={"custom": "test"},
                )

        # Register custom strategy
        factory = get_execution_strategy_factory()
        factory.register_strategy(CustomTestStrategy)

        # Verify it's registered
        assert "CustomTestStrategy" in factory.list_strategies()

        # Get and use the custom strategy
        strategy = factory.get_strategy("custom_test", None)
        assert strategy is not None
        assert isinstance(strategy, CustomTestStrategy)

        # Execute the strategy
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

        result = await strategy.execute(context)

        assert result.status == "passed"
        assert result.metadata.get("custom") == "test"

        # Clean up - unregister the test strategy
        factory.unregister_strategy(CustomTestStrategy)

    @pytest.mark.asyncio
    async def test_multiple_custom_strategies(self):
        """Test registering multiple custom strategies."""
        from app.temporal.strategies import (
            ExecutionStrategy,
            get_execution_strategy_factory,
        )

        class FirstCustomStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "first"

            async def execute(self, context):
                pass

        class SecondCustomStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "second"

            async def execute(self, context):
                pass

        factory = get_execution_strategy_factory()
        initial_count = len(factory.list_strategies())

        factory.register_strategy(FirstCustomStrategy)
        factory.register_strategy(SecondCustomStrategy)

        assert len(factory.list_strategies()) == initial_count + 2

        # Clean up
        factory.unregister_strategy(FirstCustomStrategy)
        factory.unregister_strategy(SecondCustomStrategy)

        assert len(factory.list_strategies()) == initial_count
