"""
Execution Strategies Package

This package implements the Strategy Pattern for test execution modes,
following the SOLID Open/Closed Principle.

Available Strategies:
- ScriptExecutionStrategy: Execute approved Playwright scripts
- NLStepExecutionStrategy: Deprecated natural language steps (backward compatibility)

Adding New Execution Modes:
1. Create a new strategy class inheriting from ExecutionStrategy
2. Implement can_handle() and execute() methods
3. Register with ExecutionStrategyFactory.register_strategy()
4. No need to modify existing code!

Example:
    from app.temporal.strategies import ExecutionStrategy, ExecutionStrategyFactory

    class CustomExecutionStrategy(ExecutionStrategy):
        @classmethod
        def can_handle(cls, execution_mode: str, script_status: Optional[str] = None) -> bool:
            return execution_mode == "custom"

        async def execute(self, context: ExecutionContext) -> ExecutionResult:
            # Custom execution logic
            pass

    # Register the strategy
    ExecutionStrategyFactory.register_strategy(CustomExecutionStrategy)
"""

from .execution_strategy import (
    ExecutionStrategy,
    ExecutionContext,
    ExecutionResult,
)
from .script_execution_strategy import ScriptExecutionStrategy
from .nl_step_execution_strategy import NLStepExecutionStrategy
from .execution_strategy_factory import (
    ExecutionStrategyFactory,
    get_execution_strategy_factory,
)

__all__ = [
    # Core interfaces
    "ExecutionStrategy",
    "ExecutionContext",
    "ExecutionResult",
    # Concrete strategies
    "ScriptExecutionStrategy",
    "NLStepExecutionStrategy",
    # Factory
    "ExecutionStrategyFactory",
    "get_execution_strategy_factory",
]
