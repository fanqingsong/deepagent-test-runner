"""
Test Execution Workflows with Token Integration

Enhanced Temporal workflows that integrate token checking and tracking
into the test execution pipeline.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError

from app.temporal.activities.test_activities_with_tokens import (
    PrepareTestInput,
    PrepareTestOutput,
    BrowserAutomationInput,
    BrowserAutomationOutput,
    SaveResultsInput,
    MarkRunFailedInput,
    check_test_execution_tokens,
    track_test_execution_tokens,
)
from app.temporal.activities import (
    get_default_retry_policy,
    get_long_running_retry_policy,
)
from app.temporal.workflows import DEFAULT_EXECUTION_TIMEOUT, DEFAULT_RUN_TIMEOUT
from app.core.exceptions.token_exceptions import TokenBudgetExceeded, TokenQuotaExceeded

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class TestExecutionWorkflowWithTokens:
    """
    Enhanced workflow for test execution with token integration.

    This workflow orchestrates the test execution process with token management:
    1. Check token availability before execution
    2. Prepare test execution
    3. Execute browser automation
    4. Track token usage after execution
    5. Save results with token information

    Handles token-related errors gracefully and ensures proper tracking.
    """

    @workflow.run
    async def run(
        self,
        test_definition_id: str,
        run_id: str,
        environment: Dict[str, Any] = None,
        check_tokens: bool = True,
        track_tokens: bool = True,
        scope_type: str = "test",
    ) -> Dict[str, Any]:
        """
        Execute test workflow with integrated token management.

        Args:
            test_definition_id: Test definition internal ID
            run_id: Unique run identifier
            environment: Optional environment variables for the test
            check_tokens: Whether to check token availability before execution
            track_tokens: Whether to track token usage after execution
            scope_type: Token scope type (test, suite, organization)

        Returns:
            dict: Test execution results with token information
        """
        environment = environment or {}
        logger.info(
            f"TestExecutionWorkflowWithTokens starting for test {test_definition_id}, "
            f"run {run_id} (check_tokens={check_tokens}, track_tokens={track_tokens})"
        )

        token_check_result = None
        token_tracking_result = None

        try:
            # Step 1: Prepare test execution (includes token check if enabled)
            logger.info(f"Preparing test {test_definition_id}")
            prepare_output: PrepareTestOutput = await workflow.execute_activity(
                "prepare_test_with_tokens",
                PrepareTestInput(
                    test_definition_id=test_definition_id,
                    run_id=run_id,
                    environment=environment,
                    check_tokens=check_tokens,
                    scope_type=scope_type,
                ),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            token_check_result = prepare_output.token_check_result

            # Check if token check blocked execution
            if token_check_result and not token_check_result.get("allowed", True):
                enforcement_action = token_check_result.get("enforcement_action", "warning")

                if enforcement_action == "blocked":
                    logger.warning(
                        f"Test execution blocked for test {test_definition_id} "
                        f"due to token limits (hard enforcement)"
                    )

                    # Mark run as failed with token error
                    await workflow.execute_activity(
                        "mark_run_failed_with_tokens",
                        MarkRunFailedInput(
                            run_id=run_id,
                            error_message="Token budget exceeded",
                            token_error={
                                "error": "token_budget_exceeded",
                                "details": token_check_result
                            }
                        ),
                        start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                        retry_policy=get_default_retry_policy(),
                    )

                    return {
                        "run_id": run_id,
                        "test_definition_id": test_definition_id,
                        "status": "blocked",
                        "error": "Token budget exceeded",
                        "token_check_result": token_check_result,
                        "test_cases": [],
                    }

                elif enforcement_action == "warning":
                    logger.warning(
                        f"Test execution proceeding with warning for test {test_definition_id} "
                        f"(token budget exceeded but soft enforcement)"
                    )

            logger.info(
                f"Test prepared: mode={prepare_output.mode}, "
                f"steps={len(prepare_output.test_steps)}"
            )

            # Step 2: Execute browser automation
            logger.info(f"Starting browser automation for run {run_id}")
            automation_output: BrowserAutomationOutput = await workflow.execute_activity(
                "run_browser_automation_with_tokens",
                BrowserAutomationInput(
                    run_id=run_id,
                    test_definition_id=test_definition_id,
                    url=prepare_output.url,
                    test_goal=prepare_output.test_goal,
                    test_steps=prepare_output.test_steps,
                    environment=prepare_output.environment,
                    mode=prepare_output.mode,
                    execution_mode=prepare_output.execution_mode,
                    playwright_script=prepare_output.playwright_script,
                    script_status=prepare_output.script_status,
                    track_tokens=track_tokens,
                    scope_type=scope_type,
                ),
                start_to_close_timeout=DEFAULT_EXECUTION_TIMEOUT,
                retry_policy=get_long_running_retry_policy(),
            )

            token_tracking_result = automation_output.token_tracking_result

            logger.info(
                f"Browser automation completed: status={automation_output.status}, "
                f"tests={automation_output.total_tests}, "
                f"passed={automation_output.passed}, failed={automation_output.failed}"
            )

            # Step 3: Save results to database with token information
            results_dict = {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": automation_output.status,
                "start_time": automation_output.start_time,
                "end_time": automation_output.end_time,
                "total_duration": automation_output.total_duration,
                "total_tests": automation_output.total_tests,
                "passed": automation_output.passed,
                "failed": automation_output.failed,
                "skipped": automation_output.skipped,
                "test_cases": automation_output.test_cases,
                "error": automation_output.error,
                "tokens_used": automation_output.tokens_used,
                "token_tracking_result": token_tracking_result,
                "token_check_result": token_check_result,
            }

            logger.info(f"Saving results for run {run_id}")
            await workflow.execute_activity(
                "save_results_with_tokens",
                SaveResultsInput(
                    run_id=run_id,
                    results=results_dict,
                    track_tokens=track_tokens,
                ),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            logger.info(f"TestExecutionWorkflowWithTokens completed for run {run_id}")
            return results_dict

        except ActivityError as e:
            # Handle activity-specific errors
            logger.error(f"Activity error in TestExecutionWorkflowWithTokens: {e}")

            # Check if it's a token-related error
            error_message = str(e)
            token_error = None
            if "token" in error_message.lower():
                token_error = {
                    "error": "token_error",
                    "message": error_message,
                    "type": "TokenBudgetExceeded" if "budget" in error_message.lower() else "TokenQuotaExceeded"
                }

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    "mark_run_failed_with_tokens",
                    MarkRunFailedInput(
                        run_id=run_id,
                        error_message=error_message,
                        token_error=token_error,
                    ),
                    start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )
            except Exception as mark_error:
                logger.error(f"Failed to mark run as failed: {mark_error}")

            # Return error result
            return {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": error_message,
                "token_error": token_error,
                "token_check_result": token_check_result,
                "test_cases": [],
            }

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in TestExecutionWorkflowWithTokens: {e}")

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    "mark_run_failed_with_tokens",
                    MarkRunFailedInput(
                        run_id=run_id,
                        error_message=str(e),
                    ),
                    start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )
            except Exception as mark_error:
                logger.error(f"Failed to mark run as failed: {mark_error}")

            # Return error result
            return {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": str(e),
                "token_check_result": token_check_result,
                "test_cases": [],
            }


@workflow.defn(sandboxed=False)
class ScriptGenerationWorkflowWithTokens:
    """
    Workflow for script generation with token integration.

    This workflow:
    1. Checks token availability before script generation
    2. Generates Playwright script using LLM
    3. Tracks token usage after generation
    4. Saves script with token information
    """

    @workflow.run
    async def run(
        self,
        test_definition_id: int,
        url: str,
        test_goal: str,
        run_id: str,
        scope_type: str = "test",
        enforcement_mode: str = "soft",
    ) -> Dict[str, Any]:
        """
        Generate Playwright script with token management.

        Args:
            test_definition_id: Test definition ID
            url: Target URL for testing
            test_goal: Goal of the test
            run_id: Unique run identifier
            scope_type: Token scope type
            enforcement_mode: Token enforcement mode (hard, soft)

        Returns:
            dict: Script generation results with token information
        """
        logger.info(
            f"ScriptGenerationWorkflowWithTokens starting for test {test_definition_id}, "
            f"run {run_id}"
        )

        token_check_result = None
        token_tracking_result = None

        try:
            # Step 1: Check token availability
            async def check_tokens(db):
                return await check_test_execution_tokens(
                    test_definition_id=test_definition_id,
                    run_id=run_id,
                    db=db,
                    scope_type=scope_type
                )

            token_check_result = await workflow.execute_activity(
                "check_test_execution_tokens",
                check_tokens,
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            # Check if blocked
            if not token_check_result.get("allowed", True):
                enforcement_action = token_check_result.get("enforcement_action", "warning")
                if enforcement_action == "blocked":
                    logger.warning(
                        f"Script generation blocked for test {test_definition_id} "
                        f"due to token limits"
                    )
                    return {
                        "run_id": run_id,
                        "test_definition_id": test_definition_id,
                        "status": "blocked",
                        "error": "Token budget exceeded",
                        "token_check_result": token_check_result,
                    }

            # Step 2: Generate script using LLM
            # This would be implemented as a separate activity
            # For now, we'll use a placeholder
            logger.info(f"Generating script for test {test_definition_id}")

            # Placeholder for script generation
            # In real implementation, this would call the script generator
            script_generation_result = {
                "status": "success",
                "script": "# Placeholder script",
                "tokens_used": 1500,  # Example
            }

            # Step 3: Track token usage
            async def track_tokens(db):
                return await track_test_execution_tokens(
                    test_definition_id=test_definition_id,
                    run_id=run_id,
                    execution_result=script_generation_result,
                    db=db,
                    scope_type=scope_type
                )

            token_tracking_result = await workflow.execute_activity(
                "track_test_execution_tokens",
                track_tokens,
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            logger.info(f"Script generation completed for run {run_id}")

            return {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": "success",
                "script": script_generation_result["script"],
                "tokens_used": script_generation_result["tokens_used"],
                "token_check_result": token_check_result,
                "token_tracking_result": token_tracking_result,
            }

        except ActivityError as e:
            logger.error(f"Activity error in ScriptGenerationWorkflowWithTokens: {e}")
            return {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": str(e),
                "token_check_result": token_check_result,
                "token_tracking_result": token_tracking_result,
            }

        except Exception as e:
            logger.error(f"Unexpected error in ScriptGenerationWorkflowWithTokens: {e}")
            return {
                "run_id": run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": str(e),
                "token_check_result": token_check_result,
                "token_tracking_result": token_tracking_result,
            }


# Workflow helper functions


async def handle_workflow_token_error(
    workflow_instance,
    run_id: str,
    test_definition_id: str,
    token_error: Dict[str, Any],
    original_error: Optional[Exception] = None
) -> Dict[str, Any]:
    """
    Handle token errors in workflows.

    Helper function to standardize token error handling across workflows.

    Args:
        workflow_instance: Workflow instance
        run_id: Test run ID
        test_definition_id: Test definition ID
        token_error: Token error details
        original_error: Original exception if applicable

    Returns:
        Error result dictionary
    """
    logger.error(f"Token error in workflow for run {run_id}: {token_error}")

    # Mark run as failed
    try:
        await workflow.execute_activity(
            "mark_run_failed_with_tokens",
            MarkRunFailedInput(
                run_id=run_id,
                error_message=token_error.get("message", "Token error"),
                token_error=token_error,
            ),
            start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
            retry_policy=get_default_retry_policy(),
        )
    except Exception as mark_error:
        logger.error(f"Failed to mark run as failed: {mark_error}")

    return {
        "run_id": run_id,
        "test_definition_id": test_definition_id,
        "status": "error",
        "error": token_error.get("message", "Token error"),
        "token_error": token_error,
        "original_error": str(original_error) if original_error else None,
    }
