"""
Execution Strategy Factory

Factory for creating and managing execution strategies.
Implements the Factory Pattern with a registry for dynamic strategy registration.

This allows new execution modes to be added without modifying existing code,
following the SOLID Open/Closed Principle.
"""

from typing import Dict, List, Optional, Type
import logging

from .execution_strategy import ExecutionStrategy, ExecutionContext, ExecutionResult
from .script_execution_strategy import ScriptExecutionStrategy
from .nl_step_execution_strategy import NLStepExecutionStrategy

logger = logging.getLogger(__name__)


class ExecutionStrategyFactory:
    """
    Factory for creating execution strategy instances.

    This factory:
    1. Maintains a registry of available strategies
    2. Selects the appropriate strategy based on execution mode
    3. Allows dynamic registration of new strategies
    4. Provides fallback to default strategy if no match found

    Usage:
        # Get strategy for execution mode
        factory = ExecutionStrategyFactory()
        strategy = factory.get_strategy("script", "approved")
        result = await strategy.execute(context)

        # Register custom strategy
        factory.register_strategy(CustomExecutionStrategy)

        # List available strategies
        strategies = factory.list_strategies()
    """

    # Class-level registry of available strategies
    _strategy_registry: List[Type[ExecutionStrategy]] = []

    def __init__(self):
        """Initialize factory and register default strategies."""
        # Register built-in strategies if not already registered
        self._ensure_default_strategies()

    @classmethod
    def _ensure_default_strategies(cls):
        """Ensure default strategies are registered."""
        # Only register if not already present
        if not cls._strategy_registry:
            cls.register_strategy(ScriptExecutionStrategy)
            cls.register_strategy(NLStepExecutionStrategy)

    @classmethod
    def register_strategy(cls, strategy_class: Type[ExecutionStrategy]) -> None:
        """
        Register a new execution strategy.

        This allows custom execution modes to be added at runtime
        without modifying existing code.

        Args:
            strategy_class: Strategy class (not instance) to register

        Example:
            class CustomExecutionStrategy(ExecutionStrategy):
                @classmethod
                def can_handle(cls, execution_mode: str, script_status: Optional[str] = None) -> bool:
                    return execution_mode == "custom"

                async def execute(self, context: ExecutionContext) -> ExecutionResult:
                    # Custom execution logic
                    pass

            ExecutionStrategyFactory.register_strategy(CustomExecutionStrategy)
        """
        if not issubclass(strategy_class, ExecutionStrategy):
            raise TypeError(f"{strategy_class.__name__} must inherit from ExecutionStrategy")

        if strategy_class not in cls._strategy_registry:
            cls._strategy_registry.append(strategy_class)
            logger.info(f"Registered execution strategy: {strategy_class.__name__}")
        else:
            logger.warning(f"Strategy {strategy_class.__name__} already registered")

    @classmethod
    def unregister_strategy(cls, strategy_class: Type[ExecutionStrategy]) -> None:
        """
        Unregister an execution strategy.

        Args:
            strategy_class: Strategy class to unregister
        """
        if strategy_class in cls._strategy_registry:
            cls._strategy_registry.remove(strategy_class)
            logger.info(f"Unregistered execution strategy: {strategy_class.__name__}")
        else:
            logger.warning(f"Strategy {strategy_class.__name__} not found in registry")

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        List all registered strategy names.

        Returns:
            List of strategy class names
        """
        return [strategy.__name__ for strategy in cls._strategy_registry]

    @classmethod
    def clear_registry(cls) -> None:
        """
        Clear all registered strategies.

        ⚠️ WARNING: This will remove all strategies including built-in ones.
        Use only for testing purposes.
        """
        cls._strategy_registry.clear()
        logger.warning("Cleared all execution strategies from registry")

    def get_strategy(
        self, execution_mode: str, script_status: Optional[str] = None
    ) -> Optional[ExecutionStrategy]:
        """
        Get the appropriate strategy for the given execution mode.

        Searches through registered strategies to find one that can handle
        the given execution mode and script status.

        Args:
            execution_mode: The execution mode (e.g., "script", "nl_steps")
            script_status: Optional script status for validation

        Returns:
            ExecutionStrategy instance if found, None otherwise

        Example:
            factory = ExecutionStrategyFactory()
            strategy = factory.get_strategy("script", "approved")
            if strategy:
                result = await strategy.execute(context)
        """
        # Ensure default strategies are registered
        self._ensure_default_strategies()

        # Search for a strategy that can handle this mode
        for strategy_class in self._strategy_registry:
            try:
                if strategy_class.can_handle(execution_mode, script_status):
                    strategy_instance = strategy_class()
                    logger.info(
                        f"Selected strategy {strategy_class.__name__} "
                        f"for execution_mode={execution_mode}, script_status={script_status}"
                    )
                    return strategy_instance
            except Exception as e:
                logger.error(
                    f"Error checking if {strategy_class.__name__} can handle "
                    f"execution_mode={execution_mode}: {e}"
                )
                continue

        # No strategy found
        logger.warning(
            f"No strategy found for execution_mode={execution_mode}, "
            f"script_status={script_status}"
        )
        return None

    async def execute_with_strategy(
        self, execution_mode: str, context: ExecutionContext, script_status: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute test using the appropriate strategy.

        Convenience method that combines get_strategy and execute.

        Args:
            execution_mode: The execution mode to use
            context: ExecutionContext with execution details
            script_status: Optional script status for validation

        Returns:
            ExecutionResult from strategy execution

        Raises:
            ValueError: If no strategy can handle the execution mode
        """
        strategy = self.get_strategy(execution_mode, script_status)

        if not strategy:
            # Create a detailed error message
            available_modes = self._get_available_execution_modes()
            error_message = (
                f"No execution strategy found for execution_mode='{execution_mode}'"
                f", script_status='{script_status}'. "
                f"Available execution modes: {available_modes}"
            )
            raise ValueError(error_message)

        # Execute with the selected strategy
        return await strategy.execute(context)

    def _get_available_execution_modes(self) -> List[str]:
        """
        Get list of available execution modes from registered strategies.

        Returns:
            List of execution mode names
        """
        modes = []
        for strategy_class in self._strategy_registry:
            # Try to infer mode name from class name
            class_name = strategy_class.__name__.lower()
            if "script" in class_name:
                modes.append("script")
            elif "nl_step" in class_name or "natural" in class_name:
                modes.append("nl_steps")
            else:
                # Generic fallback
                mode_name = class_name.replace("executionstrategy", "").replace("strategy", "")
                if mode_name:
                    modes.append(mode_name)

        return list(set(modes))  # Remove duplicates


# Global factory instance for convenience
_default_factory = None


def get_execution_strategy_factory() -> ExecutionStrategyFactory:
    """
    Get the default execution strategy factory instance.

    Returns:
        ExecutionStrategyFactory: Global factory instance

    Example:
        factory = get_execution_strategy_factory()
        strategy = factory.get_strategy("script", "approved")
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ExecutionStrategyFactory()
    return _default_factory
