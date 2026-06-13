"""
Run Status Manager

Manages test run status transitions and lifecycle following SOLID principles.
Single responsibility: handle all status-related operations for test runs.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_run import TestRun

logger = logging.getLogger(__name__)


class RunStatusManager:
    """
    Manages test run status transitions and lifecycle.

    Responsible for:
    - Validating status transitions
    - Updating run statuses with proper transitions
    - Managing run lifecycle states (pending, running, completed, failed)
    """

    # Valid status transitions for test runs
    VALID_TRANSITIONS = {
        'pending': ['running', 'skipped', 'failed', 'error'],
        'running': ['passed', 'failed', 'skipped', 'error'],
        'failed': ['pending'],
    }

    def __init__(self, db_session: AsyncSession):
        """
        Initialize Run Status Manager.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    def _validate_transition(self, current_status: str, new_status: str) -> bool:
        """
        Validate if a status transition is allowed.

        Args:
            current_status: Current run status
            new_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        valid_next_statuses = self.VALID_TRANSITIONS.get(current_status, [])
        return new_status in valid_next_statuses

    async def _get_test_run(self, run_id: str) -> Optional[TestRun]:
        """
        Retrieve test run by run_id.

        Args:
            run_id: Run identifier

        Returns:
            TestRun object or None if not found
        """
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
            start_time: Optional start time (milliseconds as bigint)
            end_time: Optional end time (milliseconds as bigint)
            error_message: Optional error message for failed runs

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If run not found or status transition is invalid
        """
        test_run = await self._get_test_run(run_id)

        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        # Validate status transitions
        current_status = test_run.status
        if not self._validate_transition(current_status, status):
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
        """
        Mark a run as running, including retry after failure.

        Handles transitions from:
        - pending -> running
        - failed -> pending -> running (retry flow)

        Args:
            run_id: Run identifier

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If run not found or cannot be started
        """
        test_run = await self._get_test_run(run_id)
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
        """
        Apply terminal status when save_test_results did not already set it.

        Handles smart transitions:
        - If already at target status, just update error message if needed
        - If running, transition to target status
        - If pending, transition through running to target status

        Args:
            run_id: Run identifier
            status: Target terminal status
            error_message: Optional error message

        Returns:
            Updated TestRun object or None if not found
        """
        target = "failed" if status == "error" else status

        test_run = await self._get_test_run(run_id)
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
        """
        Mark a run as failed without invalid failed->failed transitions.

        Handles:
        - If already failed, update error message if different
        - If running or pending, transition to failed
        - Other states are left unchanged

        Args:
            run_id: Run identifier
            error_message: Optional error message

        Returns:
            Updated TestRun object or None if not found
        """
        test_run = await self._get_test_run(run_id)
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
