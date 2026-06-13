# Execution Strategies Documentation

## Overview

The Execution Strategy Pattern allows you to add new test execution modes without modifying existing code, following the SOLID Open/Closed Principle.

## Architecture

```
ExecutionStrategy (abstract base)
    ├── ScriptExecutionStrategy (approved Playwright scripts)
    ├── NLStepExecutionStrategy (deprecated nl_steps)
    └── [Your Custom Strategy] (extensible)

ExecutionStrategyFactory (manages and selects strategies)
    └── Registry of all available strategies
```

## Current Execution Modes

| Mode | Strategy | Status | Description |
|------|----------|--------|-------------|
| `script` | ScriptExecutionStrategy | ✅ Active | Execute approved Playwright scripts |
| `nl_steps` | NLStepExecutionStrategy | ⚠️ Deprecated | Natural language steps (will be removed) |

## Adding a New Execution Mode

### Step 1: Create Your Strategy Class

Create a new file in `app/temporal/strategies/` (e.g., `custom_execution_strategy.py`):

```python
from typing import Optional
from app.temporal.strategies.execution_strategy import (
    ExecutionStrategy,
    ExecutionContext,
    ExecutionResult,
)
from datetime import datetime


class CustomExecutionStrategy(ExecutionStrategy):
    """
    Custom execution strategy for [describe your mode].

    This strategy handles [describe what it does].
    """

    @classmethod
    def can_handle(
        cls, execution_mode: str, script_status: Optional[str] = None
    ) -> bool:
        """
        Determine if this strategy can handle the execution mode.

        Args:
            execution_mode: The execution mode to check
            script_status: Optional script status for validation

        Returns:
            bool: True if this strategy handles the mode
        """
        return execution_mode == "custom"  # Your custom mode name

    def validate_context(self, context: ExecutionContext) -> None:
        """
        Validate context for custom execution.

        Args:
            context: ExecutionContext to validate

        Raises:
            ValueError: If context is invalid
        """
        # Call parent validation
        super().validate_context(context)

        # Add custom validation
        if not context.environment.get("custom_config"):
            raise ValueError("custom_config is required in environment")

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute test using custom strategy.

        Args:
            context: ExecutionContext with execution details

        Returns:
            ExecutionResult with execution results
        """
        start_time = int(datetime.utcnow().timestamp() * 1000)

        try:
            # Validate context
            self.validate_context(context)

            # Navigate to URL if provided
            if context.url:
                await context.page.goto(
                    context.url, wait_until="domcontentloaded", timeout=30000
                )

            # Your custom execution logic here
            # Example: Execute custom test framework
            result_data = await self._execute_custom_tests(context)

            # Calculate metrics
            end_time = int(datetime.utcnow().timestamp() * 1000)
            total_duration = end_time - start_time

            # Return standardized result
            return ExecutionResult(
                run_id=context.run_id,
                test_definition_id=context.test_definition_id,
                status=result_data["status"],
                test_cases=result_data["test_cases"],
                error=result_data.get("error"),
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                total_tests=result_data["total_tests"],
                passed=result_data["passed"],
                failed=result_data["failed"],
                skipped=result_data.get("skipped", 0),
                metadata={
                    "execution_mode": "custom",
                    "custom_metric": result_data.get("custom_metric"),
                },
            )

        except Exception as e:
            # Handle errors
            return self.create_error_result(context, str(e), start_time)

    async def _execute_custom_tests(self, context: ExecutionContext) -> dict:
        """
        Internal method for custom test execution.

        Args:
            context: ExecutionContext with execution details

        Returns:
            dict: Test results
        """
        # Your custom test execution logic
        # This is where you integrate your test framework
        pass
```

### Step 2: Register Your Strategy

Register your strategy with the factory. You can do this in two ways:

#### Option A: Register at Import Time (Recommended for built-in strategies)

Add to `app/temporal/strategies/__init__.py`:

```python
from .custom_execution_strategy import CustomExecutionStrategy

# Auto-register at import
ExecutionStrategyFactory.register_strategy(CustomExecutionStrategy)
```

#### Option B: Register at Runtime (For dynamic plugins)

Register in your application startup code:

```python
from app.temporal.strategies import (
    CustomExecutionStrategy,
    get_execution_strategy_factory,
)

factory = get_execution_strategy_factory()
factory.register_strategy(CustomExecutionStrategy)
```

### Step 3: Update Database Models (If Needed)

If your execution mode requires additional fields in the database:

1. Create an Alembic migration:

```bash
docker exec -it cc-test-backend alembic revision -m "add custom execution mode fields"
```

2. Edit the migration file to add your fields:

```python
def upgrade():
    op.add_column('test_definitions', sa.Column('custom_config', JSON(), nullable=True))

def downgrade():
    op.drop_column('test_definitions', 'custom_config')
```

3. Apply the migration:

```bash
docker exec -it cc-test-backend alembic upgrade head
```

### Step 4: Use Your New Execution Mode

Now you can use your new execution mode in test definitions:

```python
# Create a test definition with custom mode
test_def = TestDefinition(
    url="https://example.com",
    execution_mode="custom",  # Your custom mode
    # Add your custom fields
)
```

## Examples of Future Execution Modes

### Hybrid Execution Mode

```python
class HybridExecutionStrategy(ExecutionStrategy):
    """Mix of scripts and natural language steps."""

    @classmethod
    def can_handle(cls, execution_mode: str, script_status=None):
        return execution_mode == "hybrid"

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        # First execute the script
        script_result = await self._execute_script(context)

        # Then interpret natural language steps
        nl_result = await self._interpret_nl_steps(context)

        # Combine results
        return self._merge_results(script_result, nl_result)
```

### AI Autonomous Mode

```python
class AIAutonomousExecutionStrategy(ExecutionStrategy):
    """Fully autonomous AI-driven testing."""

    @classmethod
    def can_handle(cls, execution_mode: str, script_status=None):
        return execution_mode == "ai_autonomous"

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        # Use AI to explore the application
        exploration_result = await self._ai_explore(context)

        # Use AI to identify bugs
        bug_report = await self._ai_identify_bugs(context, exploration_result)

        return ExecutionResult(...)
```

### Visual Regression Mode

```python
class VisualRegressionExecutionStrategy(ExecutionStrategy):
    """Visual regression testing with screenshots."""

    @classmethod
    def can_handle(cls, execution_mode: str, script_status=None):
        return execution_mode == "visual"

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        # Take screenshots
        screenshots = await self._capture_screenshots(context)

        # Compare with baseline
        diff_result = await self._compare_visuals(screenshots)

        return ExecutionResult(...)
```

## Testing Your Strategy

### Unit Tests

Create tests in `app/tests/temporal/strategies/test_custom_strategy.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.temporal.strategies.custom_execution_strategy import CustomExecutionStrategy

class TestCustomExecutionStrategy:
    def test_can_handle(self):
        assert CustomExecutionStrategy.can_handle("custom") is True
        assert CustomExecutionStrategy.can_handle("script") is False

    @pytest.mark.asyncio
    async def test_execute_success(self):
        # Test successful execution
        pass
```

### Integration Tests

Test with Temporal activities:

```python
from app.temporal.activities.test_activities import BrowserAutomationInput, run_browser_automation

@pytest.mark.asyncio
async def test_custom_mode_integration():
    input_data = BrowserAutomationInput(
        execution_mode="custom",
        # ... other fields
    )

    result = await run_browser_automation(input_data)

    assert result.status == "passed"
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully and return standardized error results:

```python
try:
    result = await self._execute_logic(context)
except SpecificError as e:
    return self.create_error_result(context, str(e), start_time)
```

### 2. Context Validation

Validate the context before execution:

```python
def validate_context(self, context: ExecutionContext) -> None:
    super().validate_context(context)

    # Add your custom validation
    if not self._has_required_data(context):
        raise ValueError("Missing required data")
```

### 3. Metadata

Include useful metadata in results:

```python
metadata = {
    "execution_mode": "custom",
    "framework_version": "1.0.0",
    "custom_metrics": {...},
}
```

### 4. Logging

Log important events:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Starting custom execution for run {context.run_id}")
logger.error(f"Custom execution failed: {error}")
```

## Troubleshooting

### Strategy Not Found

If you get "No execution strategy found" error:

1. Check that your strategy is registered: `factory.list_strategies()`
2. Verify `can_handle()` returns True for your mode
3. Check for typos in execution_mode name

### Validation Errors

If context validation fails:

1. Check `validate_context()` implementation
2. Verify all required fields are present in context
3. Check validation logic in your strategy

### Execution Errors

If execution fails:

1. Check browser/page initialization
2. Verify URL navigation
3. Check custom execution logic
4. Review error logs

## Performance Considerations

- Strategy selection is O(n) where n is the number of registered strategies
- Keep `can_handle()` logic simple and fast
- Avoid heavy operations in strategy initialization
- Cache expensive operations

## Migration Guide

### Migrating from nl_steps to script mode

1. Convert natural language steps to Playwright script using AI
2. Update execution_mode from "nl_steps" to "script"
3. Set script_status to "approved"
4. Store generated script in playwright_script field

```python
# Old (deprecated)
test_def.execution_mode = "nl_steps"
test_def.test_steps = ["click button", "wait for modal"]

# New (recommended)
test_def.execution_mode = "script"
test_def.playwright_script = await generate_script(test_def.test_steps)
test_def.script_status = "approved"
```

## Support

For questions or issues with execution strategies:

1. Check this documentation
2. Review existing strategy implementations
3. Check test examples in `app/tests/temporal/strategies/`
4. Contact the development team
