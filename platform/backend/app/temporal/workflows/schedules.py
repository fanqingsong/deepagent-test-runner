"""
Schedule Management Workflows

Temporal workflows for schedule execution.
Temporal native Schedules handle cron-based triggering;
ScheduleExecutionWorkflow handles the actual test execution.
"""

import logging
from typing import Any, Dict, List

from temporalio import workflow
from temporalio.exceptions import ActivityError

from app.temporal.activities import (
    get_default_retry_policy,
    execute_scheduled_test,
)
from app.temporal.activities.schedule_activities import (
    ExecuteScheduledTestInput,
    ExecuteScheduledTestOutput,
)

from app.temporal.workflows import DEFAULT_EXECUTION_TIMEOUT, DEFAULT_RUN_TIMEOUT

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class ScheduleExecutionWorkflow:
    """
    Workflow for executing a scheduled test run.

    This workflow is triggered by Temporal's cron system when a schedule is due.
    It handles:
    1. Loading the schedule configuration
    2. Preparing test execution (creating test run records)
    3. Executing tests via child workflow (TestExecutionWorkflow)
    4. Updating schedule state after execution

    Executes scheduled tests.
    """

    @workflow.run
    async def run(
        self,
        schedule_id: int,
        test_definition_id: str,
    ) -> Dict[str, Any]:
        """
        Execute a scheduled test run.

        Args:
            schedule_id: Schedule ID to execute
            test_definition_id: Test definition ID to execute

        Returns:
            dict: Execution results with run IDs and test counts
        """
        logger.info(f"ScheduleExecutionWorkflow starting for schedule {schedule_id}")

        try:
            # Step 1: Execute scheduled test preparation
            # This creates the test run record and resolves test definitions
            logger.info(f"Preparing execution for schedule {schedule_id}")
            execute_output: ExecuteScheduledTestOutput = await workflow.execute_activity(
                execute_scheduled_test,
                ExecuteScheduledTestInput(
                    schedule_id=schedule_id,
                    test_definition_id=test_definition_id,
                ),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            if not execute_output.success:
                logger.warning(
                    f"Schedule {schedule_id} execution preparation failed: "
                    f"{execute_output.message}"
                )
                return {
                    "schedule_id": schedule_id,
                    "status": "skipped",
                    "message": execute_output.message,
                    "tests_executed": 0,
                    "run_ids": [],
                }

            logger.info(
                f"Schedule {schedule_id} prepared: {execute_output.tests_queued} tests, "
                f"run_id={execute_output.run_id}"
            )

            # Step 2: Execute tests using child workflow
            test_definition_ids = execute_output.test_definition_ids or []
            environment = execute_output.environment or {}
            run_ids = []

            for test_def_id in test_definition_ids:
                try:
                    logger.info(
                        f"Starting child workflow for test {test_def_id} "
                        f"(schedule {schedule_id})"
                    )

                    # Execute child workflow for each test definition
                    # Note: We import here to avoid circular dependencies
                    from app.temporal.workflows.test_execution import TestExecutionWorkflow

                    test_result = await workflow.execute_child_workflow(
                        TestExecutionWorkflow.run,
                        args=[],
                        kwargs={
                            "test_definition_id": test_def_id,
                            "run_id": execute_output.run_id,
                            "environment": environment,
                        },
                        execution_timeout=DEFAULT_EXECUTION_TIMEOUT,
                    )

                    run_ids.append(test_result.get("run_id"))
                    logger.info(
                        f"Child workflow completed for test {test_def_id}: "
                        f"status={test_result.get('status')}"
                    )

                except Exception as e:
                    logger.error(
                        f"Child workflow failed for test {test_def_id}: {e}"
                    )
                    # Continue with other tests

            logger.info(
                f"ScheduleExecutionWorkflow completed for schedule {schedule_id}: "
                f"{len(run_ids)} tests executed"
            )

            return {
                "schedule_id": schedule_id,
                "status": "completed",
                "run_id": execute_output.run_id,
                "tests_executed": len(run_ids),
                "test_definition_ids": test_definition_ids,
                "run_ids": run_ids,
                "message": f"Executed {len(run_ids)} tests for schedule {schedule_id}",
            }

        except ActivityError as e:
            logger.error(f"Activity error in ScheduleExecutionWorkflow: {e}")
            return {
                "schedule_id": schedule_id,
                "status": "error",
                "error": str(e),
                "tests_executed": 0,
                "run_ids": [],
            }

        except Exception as e:
            logger.error(f"Unexpected error in ScheduleExecutionWorkflow: {e}")
            return {
                "schedule_id": schedule_id,
                "status": "error",
                "error": str(e),
                "tests_executed": 0,
                "run_ids": [],
            }
