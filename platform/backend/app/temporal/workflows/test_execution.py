"""
Test Execution Workflows

Temporal workflows for test execution orchestration.
These workflows coordinate test execution activities with proper error handling and retry logic.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError

from app.temporal.activities import (
    get_default_retry_policy,
    get_long_running_retry_policy,
    prepare_test,
    run_browser_automation,
    save_results,
    mark_run_failed,
)
from app.temporal.activities.test_activities import (
    PrepareTestInput,
    PrepareTestOutput,
    BrowserAutomationInput,
    BrowserAutomationOutput,
    SaveResultsInput,
    MarkRunFailedInput,
)

from app.temporal.workflows import DEFAULT_EXECUTION_TIMEOUT, DEFAULT_RUN_TIMEOUT

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class TestExecutionWorkflow:
    """
    Workflow for executing a single test definition.

    This workflow orchestrates the complete test execution process:
    1. Prepare: Load test definition and steps from database
    2. Execute: Run browser automation with Playwright and LangGraph agents
    3. Save: Persist test results to database

    Handles errors gracefully with proper retry policies and ensures
    database state is consistent even on failure.
    """

    @workflow.run
    async def run(
        self,
        test_definition_id: str,
        run_id: str,
        environment: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute test workflow with prepare → execute → save pipeline.

        Args:
            test_definition_id: Test definition internal ID
            run_id: Unique run identifier
            environment: Optional environment variables for the test

        Returns:
            dict: Test execution results with status, timing, and test case details
        """
        environment = environment or {}
        logger.info(f"TestExecutionWorkflow starting for test {test_definition_id}, run {run_id}")

        try:
            # Step 1: Prepare test execution
            logger.info(f"Preparing test {test_definition_id}")
            prepare_output: PrepareTestOutput = await workflow.execute_activity(
                prepare_test,
                PrepareTestInput(
                    test_definition_id=test_definition_id,
                    run_id=run_id,
                    environment=environment,
                ),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            logger.info(
                f"Test prepared: mode={prepare_output.mode}, "
                f"steps={len(prepare_output.test_steps)}"
            )

            # Step 2: Execute browser automation
            logger.info(f"Starting browser automation for run {run_id}")
            automation_output: BrowserAutomationOutput = await workflow.execute_activity(
                run_browser_automation,
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
                ),
                start_to_close_timeout=DEFAULT_EXECUTION_TIMEOUT,
                retry_policy=get_long_running_retry_policy(),
            )

            logger.info(
                f"Browser automation completed: status={automation_output.status}, "
                f"tests={automation_output.total_tests}, "
                f"passed={automation_output.passed}, failed={automation_output.failed}"
            )

            # Step 3: Save results to database
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
            }

            logger.info(f"Saving results for run {run_id}")
            await workflow.execute_activity(
                save_results,
                SaveResultsInput(run_id=run_id, results=results_dict),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            logger.info(f"TestExecutionWorkflow completed for run {run_id}")
            return results_dict

        except ActivityError as e:
            # Handle activity-specific errors
            logger.error(f"Activity error in TestExecutionWorkflow: {e}")

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    mark_run_failed,
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
                "test_cases": [],
            }

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in TestExecutionWorkflow: {e}")

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    mark_run_failed,
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
                "test_cases": [],
            }


@workflow.defn(sandboxed=False)
class RetryTestWorkflow:
    """
    Workflow for retrying a test execution with modified parameters.

    This workflow is used when a test fails and the user wants to retry
    with a modified plan (e.g., updated test steps or parameters).
    """

    @workflow.run
    async def run(
        self,
        original_run_id: str,
        modified_plan: Dict[str, Any],
        environment: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Retry test execution with a modified plan.

        Args:
            original_run_id: Original test run ID (for reference)
            modified_plan: Modified test plan with updated steps/parameters
            environment: Optional environment variables

        Returns:
            dict: Test execution results from the retry attempt
        """
        import uuid

        environment = environment or {}
        new_run_id = f"retry-{uuid.uuid4().hex[:12]}"

        # Extract test_definition_id from modified_plan
        test_definition_id = modified_plan.get("test_definition_id")
        if not test_definition_id:
            raise ValueError("modified_plan must contain test_definition_id")

        logger.info(
            f"RetryTestWorkflow starting for test {test_definition_id}, "
            f"original_run={original_run_id}, new_run={new_run_id}"
        )

        try:
            # Step 1: Prepare test execution with modified plan
            logger.info(f"Preparing retry test {test_definition_id} with modified plan")
            prepare_output: PrepareTestOutput = await workflow.execute_activity(
                prepare_test,
                PrepareTestInput(
                    test_definition_id=test_definition_id,
                    run_id=new_run_id,
                    environment=environment,
                ),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            # Override with modified plan if provided
            if modified_plan and "steps" in modified_plan:
                logger.info(f"Applying modified plan with {len(modified_plan['steps'])} steps")
                prepare_output.test_steps = [
                    {
                        "step_number": idx + 1,
                        "description": step.get("description", ""),
                    }
                    for idx, step in enumerate(modified_plan["steps"])
                ]
                # Force execute_only mode for retries with explicit steps
                prepare_output.mode = "execute_only"  # retained for retry override

            logger.info(
                f"Retry test prepared: mode={prepare_output.mode}, "
                f"steps={len(prepare_output.test_steps)}"
            )

            # Step 2: Execute browser automation
            logger.info(f"Starting retry browser automation for run {new_run_id}")
            automation_output: BrowserAutomationOutput = await workflow.execute_activity(
                run_browser_automation,
                BrowserAutomationInput(
                    run_id=new_run_id,
                    test_definition_id=test_definition_id,
                    url=prepare_output.url,
                    test_goal=prepare_output.test_goal,
                    test_steps=prepare_output.test_steps,
                    environment=prepare_output.environment,
                    mode=prepare_output.mode,
                    execution_mode=prepare_output.execution_mode,
                    playwright_script=prepare_output.playwright_script,
                    script_status=prepare_output.script_status,
                ),
                start_to_close_timeout=DEFAULT_EXECUTION_TIMEOUT,
                retry_policy=get_long_running_retry_policy(),
            )

            logger.info(
                f"Retry browser automation completed: status={automation_output.status}, "
                f"tests={automation_output.total_tests}, "
                f"passed={automation_output.passed}, failed={automation_output.failed}"
            )

            # Step 3: Save results to database
            results_dict = {
                "run_id": new_run_id,
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
                "original_run_id": original_run_id,
            }

            logger.info(f"Saving retry results for run {new_run_id}")
            await workflow.execute_activity(
                save_results,
                SaveResultsInput(run_id=new_run_id, results=results_dict),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            logger.info(f"RetryTestWorkflow completed for run {new_run_id}")
            return results_dict

        except ActivityError as e:
            # Handle activity-specific errors
            logger.error(f"Activity error in RetryTestWorkflow: {e}")

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    mark_run_failed,
                    MarkRunFailedInput(
                        run_id=new_run_id,
                        error_message=str(e),
                    ),
                    start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )
            except Exception as mark_error:
                logger.error(f"Failed to mark retry run as failed: {mark_error}")

            # Return error result
            return {
                "run_id": new_run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": str(e),
                "test_cases": [],
                "original_run_id": original_run_id,
            }

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in RetryTestWorkflow: {e}")

            # Mark run as failed in database
            try:
                await workflow.execute_activity(
                    mark_run_failed,
                    MarkRunFailedInput(
                        run_id=new_run_id,
                        error_message=str(e),
                    ),
                    start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )
            except Exception as mark_error:
                logger.error(f"Failed to mark retry run as failed: {mark_error}")

            # Return error result
            return {
                "run_id": new_run_id,
                "test_definition_id": test_definition_id,
                "status": "error",
                "error": str(e),
                "test_cases": [],
                "original_run_id": original_run_id,
            }
