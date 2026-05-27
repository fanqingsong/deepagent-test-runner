"""
Execution Service

Handles test execution logic for scheduled tasks.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Service for managing test execution for scheduled tasks.

    Responsible for:
    - Resolving target test definitions
    - Checking execution limits
    - Building environment configurations
    - Managing run state
    """

    def __init__(self, db_session=None):
        """
        Initialize Execution Service.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def resolve_target_tests(self, schedule, db) -> List[int]:
        """
        Resolve target test definition IDs based on schedule type.

        Args:
            schedule: Schedule object

        Returns:
            List of test definition IDs to execute

        Raises:
            ValueError: If schedule_type is unknown
        """
        if schedule.schedule_type == 'single':
            return [schedule.test_definition_id]

        elif schedule.schedule_type == 'suite':
            # Load test suite
            stmt = select(TestSuite).where(TestSuite.id == schedule.test_suite_id)
            result = await db.execute(stmt)
            suite = result.scalar_one_or_none()

            if not suite:
                raise ValueError(f"Test suite {schedule.test_suite_id} not found")

            return suite.test_definition_ids

        elif schedule.schedule_type == 'tag_filter':
            # Query test definitions matching the tag filter
            if not schedule.tag_filter:
                logger.warning(f"Schedule {schedule.id} has no tag_filter set")
                return []

            stmt = select(TestDefinition.id).where(
                TestDefinition.tags.any(schedule.tag_filter)
            ).where(TestDefinition.is_draft == False)
            result = await db.execute(stmt)
            ids = [row[0] for row in result.fetchall()]
            logger.info(
                "Tag filter '%s' resolved to %d test definitions for schedule %d",
                schedule.tag_filter, len(ids), schedule.id
            )
            return ids

        else:
            raise ValueError(f"Unknown schedule_type: {schedule.schedule_type}")

    async def check_execution_limit(self, schedule, db) -> bool:
        """
        Check if execution is allowed based on concurrency settings.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            True if execution is allowed, False otherwise
        """
        # If concurrent execution is allowed, always return True
        if schedule.allow_concurrent:
            return True

        # TODO: Implement proper concurrency check without schedule_id in TestRun
        return True

    def build_environment(
        self,
        schedule: Schedule,
        test_definition_environment: Optional[Dict[str, Any]] = None,
        config_env: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build final execution environment by merging configurations.

        Merge order (later wins): test_definition < run_config < schedule overrides

        Args:
            schedule: Schedule object with environment_overrides
            test_definition_environment: Base environment from test definition (optional)
            config_env: Environment from RunConfig template (optional)

        Returns:
            Merged environment dictionary
        """
        base_env = test_definition_environment or {}
        config = config_env or {}
        overrides = schedule.environment_overrides or {}

        return {**base_env, **config, **overrides}

    async def create_test_run(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> TestRun:
        """
        Create a new test run record.

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs
            environment: Environment variables
            db: Database session
            schedule_id: Optional schedule ID if triggered by schedule

        Returns:
            Created TestRun object
        """
        # Use the first test_definition_id as the primary association
        # This allows the dashboard to display the test name
        primary_test_definition_id = test_definition_ids[0] if test_definition_ids else None

        test_run = TestRun(
            test_definition_id=primary_test_definition_id,
            run_id=run_id,
            status='pending',
            start_time=int(datetime.utcnow().timestamp() * 1000)  # Set initial start_time as bigint
        )

        db.add(test_run)
        await db.commit()
        await db.refresh(test_run)

        logger.info(f"Created test run {run_id} with {len(test_definition_ids)} test definitions")
        return test_run

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> TestRun:
        """
        Update test run status and timestamps.

        Args:
            run_id: Run identifier
            status: New status
            start_time: Optional start time
            end_time: Optional end time
            error_message: Optional error message for failed runs

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If status transition is invalid
        """
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        test_run = result.scalar_one_or_none()

        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        # Validate status transitions
        valid_transitions = {
            'pending': ['running', 'skipped', 'failed', 'error'],
            'running': ['passed', 'failed', 'skipped', 'error'],
            'failed': ['pending'],
        }

        current_status = test_run.status
        if status not in valid_transitions.get(current_status, []):
            raise ValueError(
                f"Invalid status transition: {current_status} -> {status}"
            )

        # Update status and timestamps
        test_run.status = status

        if start_time:
            test_run.start_time = start_time

        if end_time:
            test_run.end_time = end_time

        # Set error message if provided
        if error_message:
            test_run.error_message = error_message

        # Calculate duration if both times are present (both are millisecond ints)
        if test_run.start_time and test_run.end_time:
            delta = test_run.end_time - test_run.start_time
            test_run.total_duration = int(delta)  # Already in milliseconds

        await self.db.commit()
        await self.db.refresh(test_run)

        logger.info(f"Updated test run {run_id} status to {status}")
        return test_run

    async def ensure_run_running(self, run_id: str) -> TestRun:
        """Mark a run as running, including Celery retry after failure."""
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        test_run = result.scalar_one_or_none()
        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        current = test_run.status
        if current == "running":
            return test_run
        if current == "pending":
            return await self.update_run_status(run_id, "running")
        if current == "failed":
            await self.update_run_status(run_id, "pending")
            return await self.update_run_status(run_id, "running")

        raise ValueError(
            f"Cannot start run {run_id}: status is {current!r}"
        )

    async def finalize_run_status_if_needed(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[TestRun]:
        """Apply terminal status when save_test_results did not already set it."""
        target = "failed" if status == "error" else status

        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        test_run = result.scalar_one_or_none()
        if not test_run:
            return None

        current = test_run.status
        if current == target:
            if error_message and test_run.error_message != error_message:
                test_run.error_message = error_message
                await self.db.commit()
            return test_run

        if current == "running":
            return await self.update_run_status(
                run_id, target, error_message=error_message
            )
        if current == "pending":
            await self.update_run_status(run_id, "running")
            return await self.update_run_status(
                run_id, target, error_message=error_message
            )

        logger.info(
            "Skipping status update for run %s: current=%s target=%s",
            run_id,
            current,
            target,
        )
        return test_run

    async def mark_run_failed(
        self,
        run_id: str,
        error_message: Optional[str] = None,
    ) -> Optional[TestRun]:
        """Mark a run failed without invalid failed->failed transitions."""
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        test_run = result.scalar_one_or_none()
        if not test_run:
            return None

        if test_run.status == "failed":
            if error_message and test_run.error_message != error_message:
                test_run.error_message = error_message
                await self.db.commit()
            return test_run

        if test_run.status in ("running", "pending"):
            return await self.update_run_status(
                run_id, "failed", error_message=error_message
            )

        return test_run

    async def save_test_results(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> TestRun:
        """
        Save test execution results to database.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary

        Returns:
            Updated TestRun object
        """
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        test_run = result.scalar_one_or_none()

        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        # Update result fields
        test_definition_id = results.get('test_definition_id')
        # Convert string test_definition_id to int if needed
        if test_definition_id and isinstance(test_definition_id, str):
            try:
                test_definition_id = int(test_definition_id)
            except (ValueError, TypeError):
                pass  # Keep as is if conversion fails

        test_run.test_definition_id = test_definition_id
        test_run.status = results.get('status', 'unknown')
        test_run.total_tests = results.get('total_tests', 0)
        test_run.passed = results.get('passed', 0)
        test_run.failed = results.get('failed', 0)
        test_run.skipped = results.get('skipped', 0)
        test_run.test_cases = results.get('test_cases')
        test_run.error_message = results.get('error')

        # Update timestamps and duration
        start_time_ms = results.get('start_time')
        end_time_ms = results.get('end_time')
        total_duration_ms = results.get('total_duration')

        if start_time_ms:
            test_run.start_time = int(start_time_ms)  # Store as bigint (milliseconds)

        if end_time_ms:
            test_run.end_time = int(end_time_ms)  # Store as bigint (milliseconds)

        if total_duration_ms:
            test_run.total_duration = int(total_duration_ms / 1000)  # Convert to seconds
        elif test_run.start_time and test_run.end_time:
            # Calculate duration if not provided
            duration_ms = test_run.end_time - test_run.start_time
            test_run.total_duration = int(duration_ms / 1000)  # Convert to seconds

        test_cases_data = results.get('test_cases', [])
        if test_cases_data:
            # Convert test_definition_id to int for database operations
            test_def_id = results.get('test_definition_id')
            if test_def_id and isinstance(test_def_id, str):
                try:
                    test_def_id = int(test_def_id)
                except (ValueError, TypeError):
                    pass  # Keep as is if conversion fails

            start_time = int(results.get('start_time', 0))
            end_time = int(results.get('end_time', 0))
            test_case_rows = [
                TestCase(
                    run_id=test_run.id,
                    test_definition_id=test_def_id,
                    test_id=f"{test_def_id}_step_{idx + 1}",
                    description=case_data.get('description', f"Step {idx + 1}"),
                    status=case_data.get('status', 'unknown'),
                    duration=int(case_data.get('duration', 0)),
                    start_time=start_time,
                    end_time=end_time,
                    error_message=case_data.get('error'),
                    screenshot_path=case_data.get('screenshot_path', ''),
                )
                for idx, case_data in enumerate(test_cases_data)
            ]
            self.db.add_all(test_case_rows)
            logger.info("Saved %d test case rows for run %s", len(test_case_rows), run_id)

        await self.db.commit()
        await self.db.refresh(test_run)

        logger.info(f"Saved results for test run {run_id}: {test_run.status}")
        return test_run
