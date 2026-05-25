"""
Schedule Management Workflows

Temporal workflows for schedule management and execution.
These workflows replace Celery Beat for cron-based scheduling.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError

from app.activities import (
    get_default_retry_policy,
    get_active_schedules,
    update_schedule_next_run,
    execute_scheduled_test,
)
from app.activities.schedule_activities import (
    GetActiveSchedulesInput,
    GetActiveSchedulesOutput,
    UpdateScheduleNextRunInput,
    UpdateScheduleNextRunOutput,
    ExecuteScheduledTestInput,
    ExecuteScheduledTestOutput,
)

from app.workflows import DEFAULT_EXECUTION_TIMEOUT, DEFAULT_RUN_TIMEOUT

logger = logging.getLogger(__name__)


@workflow.defn
class ScheduleSyncWorkflow:
    """
    Workflow for synchronizing database schedules to Temporal cron schedules.

    This workflow periodically checks the database for active schedules and
    ensures they are properly registered with Temporal's cron scheduling system.
    It handles:
    1. Fetching active schedules from database
    2. Calculating next run times for each schedule
    3. Triggering child workflows for due schedules

    This replaces the Celery Beat scheduler with Temporal's native cron support.
    """

    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """
        Synchronize schedules and trigger due executions.

        Returns:
            dict: Sync results with counts of processed schedules
        """
        logger.info("ScheduleSyncWorkflow starting schedule synchronization")

        try:
            # Step 1: Fetch all active schedules from database
            logger.info("Fetching active schedules from database")
            active_output: GetActiveSchedulesOutput = await workflow.execute_activity(
                get_active_schedules,
                GetActiveSchedulesInput(),
                start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                retry_policy=get_default_retry_policy(),
            )

            active_schedules = active_output.schedules
            logger.info(f"Found {len(active_schedules)} active schedules")

            if not active_schedules:
                logger.info("No active schedules to process")
                return {
                    "status": "completed",
                    "total_schedules": 0,
                    "updated_schedules": 0,
                    "triggered_executions": 0,
                }

            # Step 2: Update next run times for all active schedules
            updated_count = 0
            for schedule in active_schedules:
                schedule_id = schedule["id"]
                try:
                    logger.info(f"Updating next run time for schedule {schedule_id}")
                    update_output: UpdateScheduleNextRunOutput = await workflow.execute_activity(
                        update_schedule_next_run,
                        UpdateScheduleNextRunInput(schedule_id=schedule_id),
                        start_to_close_timeout=DEFAULT_RUN_TIMEOUT,
                        retry_policy=get_default_retry_policy(),
                    )

                    if update_output.success:
                        updated_count += 1
                        logger.info(
                            f"Schedule {schedule_id} next run: {update_output.next_run_time}"
                        )
                    else:
                        logger.warning(f"Failed to update schedule {schedule_id}")

                except Exception as e:
                    logger.error(f"Error updating schedule {schedule_id}: {e}")
                    # Continue with other schedules

            logger.info(f"Updated {updated_count}/{len(active_schedules)} schedules")

            # Step 3: Trigger executions for schedules that are due
            # Note: In a real cron setup, Temporal would handle this automatically.
            # This workflow is primarily for initial sync and manual triggering.
            # For continuous cron execution, use Temporal's schedule feature directly.

            logger.info("ScheduleSyncWorkflow completed")
            return {
                "status": "completed",
                "total_schedules": len(active_schedules),
                "updated_schedules": updated_count,
                "triggered_executions": 0,
                "message": "Schedule synchronization completed. Use Temporal Schedules for continuous execution.",
            }

        except ActivityError as e:
            logger.error(f"Activity error in ScheduleSyncWorkflow: {e}")
            return {
                "status": "error",
                "error": str(e),
                "total_schedules": 0,
                "updated_schedules": 0,
                "triggered_executions": 0,
            }

        except Exception as e:
            logger.error(f"Unexpected error in ScheduleSyncWorkflow: {e}")
            return {
                "status": "error",
                "error": str(e),
                "total_schedules": 0,
                "updated_schedules": 0,
                "triggered_executions": 0,
            }


@workflow.defn
class ScheduleExecutionWorkflow:
    """
    Workflow for executing a scheduled test run.

    This workflow is triggered by Temporal's cron system when a schedule is due.
    It handles:
    1. Loading the schedule configuration
    2. Preparing test execution (creating test run records)
    3. Executing tests via child workflow (TestExecutionWorkflow)
    4. Updating schedule state after execution

    This workflow replaces the Celery task `schedule_sync.execute_scheduled_tests()`.
    """

    @workflow.run
    async def run(
        self,
        schedule_id: int,
    ) -> Dict[str, Any]:
        """
        Execute a scheduled test run.

        Args:
            schedule_id: Schedule ID to execute

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
                ExecuteScheduledTestInput(schedule_id=schedule_id),
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
                    from app.workflows.test_execution import TestExecutionWorkflow

                    test_result = await workflow.execute_child_workflow(
                        TestExecutionWorkflow,
                        args=[
                            test_def_id,
                            execute_output.run_id,
                            environment,
                        ],
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
