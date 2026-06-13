"""
Natural Language Step Execution Strategy

Handles deprecated natural language step execution mode.
Maintained for backward compatibility only.
"""

from typing import Optional
import logging

from .execution_strategy import ExecutionStrategy, ExecutionContext, ExecutionResult

logger = logging.getLogger(__name__)


class NLStepExecutionStrategy(ExecutionStrategy):
    """
    Execution strategy for natural language steps (DEPRECATED).

    This strategy is maintained for backward compatibility only.
    The nl_steps mode was replaced by the script mode with AI-generated
    Playwright scripts.

    ⚠️ DEPRECATED: This mode will be removed in a future version.
    Use script mode with AI-generated Playwright scripts instead.

    Migration Guide:
    - Old: execution_mode = "nl_steps", test_steps = [natural language steps]
    - New: execution_mode = "script", playwright_script = [AI-generated script]
    """

    @classmethod
    def can_handle(
        cls, execution_mode: str, script_status: Optional[str] = None
    ) -> bool:
        """
        Check if this strategy can handle the execution mode.

        Args:
            execution_mode: Must be "nl_steps"
            script_status: Not used for this mode

        Returns:
            bool: True if mode is nl_steps (for backward compatibility)
        """
        return execution_mode == "nl_steps"

    def validate_context(self, context: ExecutionContext) -> None:
        """
        Validate context for nl_steps execution.

        Args:
            context: ExecutionContext to validate

        Raises:
            ValueError: If nl_steps are not provided or mode is deprecated
        """
        super().validate_context(context)

        # Log deprecation warning
        logger.warning(
            f"DEPRECATED: nl_steps execution mode is being used for run {context.run_id}. "
            f"This mode will be removed in a future version. "
            f"Please migrate to script mode with AI-generated Playwright scripts."
        )

        if not context.test_steps:
            raise ValueError("No test steps provided for nl_steps execution")

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute natural language steps (DEPRECATED).

        This method returns an error because nl_steps mode is no longer supported.
        The actual execution logic has been removed.

        Args:
            context: ExecutionContext with natural language steps

        Returns:
            ExecutionResult with deprecation error
        """
        from datetime import datetime

        start_time = int(datetime.utcnow().timestamp() * 1000)

        try:
            # Validate context
            self.validate_context(context)

            # Navigate to URL if provided (for consistency)
            if context.url:
                logger.info(f"Navigating to URL: {context.url}")
                await context.page.goto(context.url, wait_until="domcontentloaded", timeout=30000)

            # Return deprecation error
            error_message = (
                "The nl_steps execution mode is deprecated and no longer supported. "
                "Please use script mode with AI-generated Playwright scripts instead. "
                "Contact your system administrator to migrate your test definitions."
            )

            logger.error(f"nl_steps execution attempted for run {context.run_id}")

            return self.create_error_result(context, error_message, start_time)

        except ValueError as validation_error:
            logger.error(f"nl_steps validation failed for run {context.run_id}: {validation_error}")
            return self.create_error_result(context, str(validation_error), start_time)

        except Exception as e:
            logger.error(f"nl_steps execution failed for run {context.run_id}: {e}")
            return self.create_error_result(context, str(e), start_time)
