"""
Script Execution Strategy

Handles execution of approved Playwright scripts.
This is the primary execution mode for the system.
"""

from typing import Optional
import logging

from .execution_strategy import ExecutionStrategy, ExecutionContext, ExecutionResult

logger = logging.getLogger(__name__)


class ScriptExecutionStrategy(ExecutionStrategy):
    """
    Execution strategy for approved Playwright scripts.

    This strategy:
    1. Validates that a script exists and is approved
    2. Executes the Playwright script in a sandboxed environment
    3. Returns standardized execution results

    Status Flow: draft -> validated -> approved -> [this strategy executes]
    """

    @classmethod
    def can_handle(
        cls, execution_mode: str, script_status: Optional[str] = None
    ) -> bool:
        """
        Check if this strategy can handle the execution mode.

        Args:
            execution_mode: Must be "script"
            script_status: Must be "approved"

        Returns:
            bool: True if mode is script and status is approved
        """
        return execution_mode == "script" and script_status == "approved"

    def validate_context(self, context: ExecutionContext) -> None:
        """
        Validate context for script execution.

        Args:
            context: ExecutionContext to validate

        Raises:
            ValueError: If script is not present or not approved
        """
        super().validate_context(context)

        if not context.playwright_script:
            raise ValueError("No Playwright script provided")

        if context.script_status != "approved":
            raise ValueError(
                f"Script must be approved for execution, current status: {context.script_status}"
            )

        # Log script execution details
        logger.info(
            f"Script execution validated for run {context.run_id}, "
            f"test_definition_id: {context.test_definition_id}"
        )

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute the approved Playwright script.

        Args:
            context: ExecutionContext with script and page

        Returns:
            ExecutionResult with script execution results
        """
        from datetime import datetime
        from app.agents.test_composer.lib import execute_script

        start_time = int(datetime.utcnow().timestamp() * 1000)

        try:
            # Validate context before execution
            self.validate_context(context)

            # Navigate to URL if provided
            if context.url:
                logger.info(f"Navigating to URL: {context.url}")
                await context.page.goto(context.url, wait_until="domcontentloaded", timeout=30000)

            # Execute the Playwright script
            logger.info(
                f"Executing Playwright script for run {context.run_id}, "
                f"test_definition_id: {context.test_definition_id}"
            )

            exec_result = await execute_script(
                context.playwright_script, context.page, timeout=120
            )

            # Calculate execution metrics
            end_time = int(datetime.utcnow().timestamp() * 1000)
            total_duration = end_time - start_time

            # Extract results
            status = exec_result.get("status", "failed")
            step_results = exec_result.get("step_results", [])
            error = exec_result.get("error")

            # Count test cases
            total_tests = len(step_results) if step_results else 1
            passed = 1 if status == "passed" else 0
            failed = 1 if status != "passed" else 0

            logger.info(
                f"Script execution completed for run {context.run_id}: "
                f"status={status}, total_tests={total_tests}, "
                f"passed={passed}, failed={failed}, duration={total_duration}ms"
            )

            return ExecutionResult(
                run_id=context.run_id,
                test_definition_id=context.test_definition_id,
                status=status,
                test_cases=step_results,
                error=error,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=0,
                metadata={
                    "execution_mode": "script",
                    "script_status": context.script_status,
                },
            )

        except ValueError as validation_error:
            # Handle validation errors
            logger.error(f"Script validation failed for run {context.run_id}: {validation_error}")
            return self.create_error_result(context, str(validation_error), start_time)

        except Exception as e:
            # Handle execution errors
            logger.error(f"Script execution failed for run {context.run_id}: {e}")
            return self.create_error_result(context, str(e), start_time)
