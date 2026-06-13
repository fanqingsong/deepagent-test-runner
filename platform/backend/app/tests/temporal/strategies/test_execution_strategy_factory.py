"""
Tests for ExecutionStrategyFactory.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.temporal.strategies.execution_strategy_factory import (
    ExecutionStrategyFactory,
    get_execution_strategy_factory,
)
from app.temporal.strategies.execution_strategy import (
    ExecutionStrategy,
    ExecutionContext,
    ExecutionResult,
)
from app.temporal.strategies.script_execution_strategy import ScriptExecutionStrategy
from app.temporal.strategies.nl_step_execution_strategy import NLStepExecutionStrategy


class TestExecutionStrategyFactory:
    """Tests for ExecutionStrategyFactory."""

    def test_factory_initialization(self):
        """Test factory initialization registers default strategies."""
        factory = ExecutionStrategyFactory()

        # Should have registered default strategies
        strategies = factory.list_strategies()
        assert "ScriptExecutionStrategy" in strategies
        assert "NLStepExecutionStrategy" in strategies

    def test_get_strategy_for_script_mode(self):
        """Test getting strategy for script mode."""
        factory = ExecutionStrategyFactory()

        strategy = factory.get_strategy("script", "approved")

        assert strategy is not None
        assert isinstance(strategy, ScriptExecutionStrategy)

    def test_get_strategy_for_nl_steps_mode(self):
        """Test getting strategy for nl_steps mode."""
        factory = ExecutionStrategyFactory()

        strategy = factory.get_strategy("nl_steps", None)

        assert strategy is not None
        assert isinstance(strategy, NLStepExecutionStrategy)

    def test_get_strategy_for_unsupported_mode(self):
        """Test getting strategy for unsupported execution mode."""
        factory = ExecutionStrategyFactory()

        strategy = factory.get_strategy("unsupported_mode", None)

        assert strategy is None

    def test_get_strategy_for_script_with_wrong_status(self):
        """Test that script mode with non-approved status returns None."""
        factory = ExecutionStrategyFactory()

        strategy = factory.get_strategy("script", "draft")

        assert strategy is None

    def test_register_custom_strategy(self):
        """Test registering a custom strategy."""

        class CustomExecutionStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "custom"

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
                    metadata={"custom": "value"},
                )

        factory = ExecutionStrategyFactory()
        factory.register_strategy(CustomExecutionStrategy)

        # Verify strategy is registered
        strategies = factory.list_strategies()
        assert "CustomExecutionStrategy" in strategies

        # Verify strategy can be retrieved
        strategy = factory.get_strategy("custom", None)
        assert strategy is not None
        assert isinstance(strategy, CustomExecutionStrategy)

    def test_register_strategy_twice(self, caplog):
        """Test that registering same strategy twice is idempotent."""
        factory = ExecutionStrategyFactory()

        # Register same strategy twice
        factory.register_strategy(ScriptExecutionStrategy)
        factory.register_strategy(ScriptExecutionStrategy)

        # Should only appear once in list
        strategies = factory.list_strategies()
        script_count = strategies.count("ScriptExecutionStrategy")
        assert script_count == 1

    def test_register_non_strategy_class(self):
        """Test that registering non-strategy class raises error."""
        factory = ExecutionStrategyFactory()

        class NotAStrategy:
            pass

        with pytest.raises(TypeError, match="must inherit from ExecutionStrategy"):
            factory.register_strategy(NotAStrategy)

    def test_unregister_strategy(self):
        """Test unregistering a strategy."""

        class CustomExecutionStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "custom_unregister_test"

            async def execute(self, context):
                pass

        factory = ExecutionStrategyFactory()

        # Get initial count
        initial_strategies = ExecutionStrategyFactory.list_strategies()
        initial_count = len(initial_strategies)

        factory.register_strategy(CustomExecutionStrategy)

        # Verify it's registered
        assert "CustomExecutionStrategy" in ExecutionStrategyFactory.list_strategies()
        assert len(ExecutionStrategyFactory.list_strategies()) == initial_count + 1

        # Unregister
        ExecutionStrategyFactory.unregister_strategy(CustomExecutionStrategy)

        # Verify it's removed
        current_strategies = ExecutionStrategyFactory.list_strategies()
        assert "CustomExecutionStrategy" not in current_strategies
        assert len(current_strategies) == initial_count

    def test_unregister_non_registered_strategy(self):
        """Test unregistering a strategy that's not registered."""
        factory = ExecutionStrategyFactory()

        class NonRegisteredStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return False

            async def execute(self, context):
                pass

        # Should not raise exception
        factory.unregister_strategy(NonRegisteredStrategy)

    @pytest.mark.asyncio
    async def test_execute_with_strategy_success(self):
        """Test execute_with_strategy for successful execution."""
        from unittest.mock import patch

        factory = ExecutionStrategyFactory()

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

        with patch("app.agents.test_composer.lib.execute_script", new=AsyncMock(return_value={"status": "passed", "step_results": [{"step": "click", "status": "passed"}]})):
            result = await factory.execute_with_strategy("script", context, "approved")

            assert result.status == "passed"
            assert result.total_tests == 1
            assert result.passed == 1

    @pytest.mark.asyncio
    async def test_execute_with_strategy_no_strategy_found(self):
        """Test execute_with_strategy when no strategy is found."""
        factory = ExecutionStrategyFactory()

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

        with pytest.raises(ValueError, match="No execution strategy found"):
            await factory.execute_with_strategy("nonexistent_mode", context)

    def test_clear_registry(self):
        """Test clearing the strategy registry."""
        factory = ExecutionStrategyFactory()

        # Should have strategies
        assert len(factory.list_strategies()) > 0

        # Clear registry
        ExecutionStrategyFactory.clear_registry()

        # Should be empty
        assert len(factory.list_strategies()) == 0

        # Re-initialize factory to restore defaults
        factory = ExecutionStrategyFactory()
        assert len(factory.list_strategies()) > 0


class TestGetExecutionStrategyFactory:
    """Tests for get_execution_strategy_factory function."""

    def test_returns_factory_instance(self):
        """Test that function returns a factory instance."""
        factory = get_execution_strategy_factory()

        assert isinstance(factory, ExecutionStrategyFactory)

    def test_returns_same_instance(self):
        """Test that function returns the same instance (singleton)."""
        factory1 = get_execution_strategy_factory()
        factory2 = get_execution_strategy_factory()

        assert factory1 is factory2


class TestStrategySelectionPriority:
    """Tests for strategy selection when multiple strategies could match."""

    def test_first_registered_strategy_wins(self):
        """Test that first matching strategy is selected."""

        class FirstStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "both"

            async def execute(self, context):
                return ExecutionResult(
                    run_id=context.run_id,
                    test_definition_id=context.test_definition_id,
                    status="first",
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

        class SecondStrategy(ExecutionStrategy):
            @classmethod
            def can_handle(cls, execution_mode: str, script_status=None):
                return execution_mode == "both"

            async def execute(self, context):
                return ExecutionResult(
                    run_id=context.run_id,
                    test_definition_id=context.test_definition_id,
                    status="second",
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

        factory = ExecutionStrategyFactory()
        factory.register_strategy(FirstStrategy)
        factory.register_strategy(SecondStrategy)

        strategy = factory.get_strategy("both", None)

        # Should get FirstStrategy (registered first)
        assert isinstance(strategy, FirstStrategy)


class TestGetAvailableExecutionModes:
    """Tests for _get_available_execution_modes method."""

    def test_lists_available_modes(self):
        """Test that available modes are listed correctly."""
        factory = ExecutionStrategyFactory()

        modes = factory._get_available_execution_modes()

        # Should contain script and nl_steps modes
        # The method extracts mode names from class names
        assert len(modes) > 0  # At least some modes should be detected
