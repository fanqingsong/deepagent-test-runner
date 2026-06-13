"""
Test Run Repository Implementation

SQLAlchemy implementation of TestRun repository following async patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.test_run import TestRun
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.core.metrics.metrics_decorators import track_timing, track_errors

logger = logging.getLogger(__name__)


class SQLAlchemyTestRunRepository(ITestRunRepository):
    """
    SQLAlchemy implementation of TestRun repository.

    Handles all database operations for TestRun model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = TestRun

    @track_timing("database.test_run.create")
    async def create(
        self,
        run_id: str,
        test_definition_id: Optional[int],
        start_time_ms: int,
        db_session: AsyncSession
    ) -> TestRun:
        """
        Create a new test run record.

        Args:
            run_id: Unique run identifier
            test_definition_id: Test definition ID
            start_time_ms: Start time in milliseconds
            db_session: Database session

        Returns:
            Created TestRun object

        Raises:
            ValueError: If run_id already exists or validation fails
        """
        @track_errors("database.test_run.create")
        async def _create():
            # Check if run_id already exists
            existing = await self.get_by_id(run_id, db_session)
            if existing:
                raise ValueError(f"Test run with run_id '{run_id}' already exists")

            # Create new test run
            test_run = TestRun(
                run_id=run_id,
                test_definition_id=test_definition_id,
                status='pending',
                start_time=start_time_ms,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0
            )

            try:
                db_session.add(test_run)
                await db_session.flush()
                await db_session.refresh(test_run)

                logger.info(f"Created test run {run_id} with ID {test_run.id}")
                return test_run

            except Exception as e:
                logger.error(f"Error creating test run {run_id}: {e}")
                await db_session.rollback()
                raise

        return await _create()
        # Check if run_id already exists
        existing = await self.get_by_id(run_id, db_session)
        if existing:
            raise ValueError(f"Test run with run_id '{run_id}' already exists")

        # Create new test run
        test_run = TestRun(
            run_id=run_id,
            test_definition_id=test_definition_id,
            status='pending',
            start_time=start_time_ms,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0
        )

        try:
            db_session.add(test_run)
            await db_session.flush()
            await db_session.refresh(test_run)

            logger.info(f"Created test run {run_id} with ID {test_run.id}")
            return test_run

        except Exception as e:
            logger.error(f"Error creating test run {run_id}: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(self, run_id: str, db_session: AsyncSession) -> Optional[TestRun]:
        """
        Retrieve a test run by its run_id.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            TestRun object or None if not found
        """
        try:
            stmt = select(TestRun).where(TestRun.run_id == run_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving test run {run_id}: {e}")
            raise

    async def get_by_pk(self, pk: int, db_session: AsyncSession) -> Optional[TestRun]:
        """
        Retrieve a test run by its primary key.

        Args:
            pk: Primary key ID
            db_session: Database session

        Returns:
            TestRun object or None if not found
        """
        try:
            stmt = select(TestRun).where(TestRun.id == pk)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving test run by pk {pk}: {e}")
            raise

    async def update_status(
        self,
        run_id: str,
        status: str,
        db_session: AsyncSession,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> TestRun:
        """
        Update test run status and optionally timestamps.

        Args:
            run_id: Unique run identifier
            status: New status value
            db_session: Database session
            start_time_ms: Optional start time in milliseconds
            end_time_ms: Optional end time in milliseconds
            error_message: Optional error message for failed runs

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If test run not found
        """
        test_run = await self.get_by_id(run_id, db_session)
        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        # Update status
        test_run.status = status

        # Update timestamps if provided
        if start_time_ms is not None:
            test_run.start_time = start_time_ms

        if end_time_ms is not None:
            test_run.end_time = end_time_ms

        # Update error message if provided
        if error_message is not None:
            test_run.error_message = error_message

        try:
            await db_session.flush()
            await db_session.refresh(test_run)

            logger.info(f"Updated test run {run_id} status to {status}")
            return test_run

        except Exception as e:
            logger.error(f"Error updating test run {run_id} status: {e}")
            await db_session.rollback()
            raise

    async def update_results(
        self,
        run_id: str,
        results: Dict[str, Any],
        db_session: AsyncSession
    ) -> TestRun:
        """
        Update test run with execution results.

        Args:
            run_id: Unique run identifier
            results: Dictionary containing test results
            db_session: Database session

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If test run not found
        """
        test_run = await self.get_by_id(run_id, db_session)
        if not test_run:
            raise ValueError(f"Test run {run_id} not found")

        # Update summary fields
        test_run.total_tests = results.get('total_tests', 0)
        test_run.passed = results.get('passed', 0)
        test_run.failed = results.get('failed', 0)
        test_run.skipped = results.get('skipped', 0)
        test_run.status = results.get('status', test_run.status)

        # Update error message if provided
        if 'error_message' in results:
            test_run.error_message = results['error_message']

        # Update test_definition_id if provided
        if 'test_definition_id' in results:
            test_run.test_definition_id = results['test_definition_id']

        # Update timestamps
        if 'start_time_ms' in results and results['start_time_ms'] is not None:
            test_run.start_time = int(results['start_time_ms'])

        if 'end_time_ms' in results and results['end_time_ms'] is not None:
            test_run.end_time = int(results['end_time_ms'])

        # Update duration
        if 'total_duration_ms' in results and results['total_duration_ms']:
            test_run.total_duration = int(results['total_duration_ms'] / 1000)
        elif test_run.start_time and test_run.end_time:
            # Calculate duration if not provided
            duration_ms = test_run.end_time - test_run.start_time
            test_run.total_duration = int(duration_ms / 1000)

        try:
            await db_session.flush()
            await db_session.refresh(test_run)

            logger.info(f"Updated test run {run_id} with results: status={test_run.status}")
            return test_run

        except Exception as e:
            logger.error(f"Error updating test run {run_id} results: {e}")
            await db_session.rollback()
            raise

    async def get_by_test_definition_id(
        self,
        test_definition_id: int,
        db_session: AsyncSession,
        limit: int = 10,
        offset: int = 0
    ) -> List[TestRun]:
        """
        Retrieve test runs for a specific test definition.

        Args:
            test_definition_id: Test definition ID
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        try:
            stmt = (
                select(TestRun)
                .where(TestRun.test_definition_id == test_definition_id)
                .order_by(desc(TestRun.created_at))
                .limit(limit)
                .offset(offset)
            )
            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving runs for test definition {test_definition_id}: {e}")
            raise

    async def get_pending_runs(self, db_session: AsyncSession, limit: int = 100) -> List[TestRun]:
        """
        Retrieve all pending test runs.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of pending TestRun objects, ordered by created_at ASC
        """
        try:
            stmt = (
                select(TestRun)
                .where(TestRun.status == 'pending')
                .order_by(asc(TestRun.created_at))
                .limit(limit)
            )
            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error("Error retrieving pending runs: {e}")
            raise

    async def get_recent_runs(
        self,
        db_session: AsyncSession,
        days: int = 7,
        limit: int = 100
    ) -> List[TestRun]:
        """
        Retrieve recent test runs within the specified time window.

        Args:
            db_session: Database session
            days: Number of days to look back (default: 7)
            limit: Maximum number of records to return

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            stmt = (
                select(TestRun)
                .where(TestRun.created_at >= cutoff_date)
                .order_by(desc(TestRun.created_at))
                .limit(limit)
            )
            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving recent runs: {e}")
            raise

    async def count_by_status(self, status: str, db_session: AsyncSession) -> int:
        """
        Count test runs by status.

        Args:
            status: Status to count (e.g., 'pending', 'running', 'passed', 'failed')
            db_session: Database session

        Returns:
            Count of test runs with the specified status
        """
        try:
            stmt = select(func.count()).select_from(TestRun).where(TestRun.status == status)
            result = await db_session.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting runs by status {status}: {e}")
            raise

    async def delete(self, run_id: str, db_session: AsyncSession) -> bool:
        """
        Delete a test run by its run_id.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        try:
            test_run = await self.get_by_id(run_id, db_session)
            if not test_run:
                return False

            await db_session.delete(test_run)
            await db_session.flush()

            logger.info(f"Deleted test run {run_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting test run {run_id}: {e}")
            await db_session.rollback()
            raise

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[TestRun]:
        """
        Retrieve all test runs with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            status_filter: Optional status filter

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        try:
            stmt = select(TestRun)

            if status_filter:
                stmt = stmt.where(TestRun.status == status_filter)

            stmt = stmt.order_by(desc(TestRun.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error("Error retrieving all test runs: {e}")
            raise

    async def exists(self, run_id: str, db_session: AsyncSession) -> bool:
        """
        Check if a test run exists.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count()).select_from(TestRun).where(TestRun.run_id == run_id)
            result = await db_session.execute(stmt)
            count = result.scalar() or 0
            return count > 0

        except Exception as e:
            logger.error(f"Error checking if test run {run_id} exists: {e}")
            raise

    async def get_stats_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get test run statistics for a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            db_session: Database session

        Returns:
            Dictionary containing statistics
        """
        try:
            # Total runs
            total_stmt = select(func.count()).select_from(TestRun).where(
                and_(
                    TestRun.created_at >= start_date,
                    TestRun.created_at <= end_date
                )
            )
            total_result = await db_session.execute(total_stmt)
            total_runs = total_result.scalar() or 0

            # Passed runs
            passed_stmt = select(func.count()).select_from(TestRun).where(
                and_(
                    TestRun.created_at >= start_date,
                    TestRun.created_at <= end_date,
                    TestRun.status == 'passed'
                )
            )
            passed_result = await db_session.execute(passed_stmt)
            passed = passed_result.scalar() or 0

            # Failed runs
            failed_stmt = select(func.count()).select_from(TestRun).where(
                and_(
                    TestRun.created_at >= start_date,
                    TestRun.created_at <= end_date,
                    TestRun.status == 'failed'
                )
            )
            failed_result = await db_session.execute(failed_stmt)
            failed = failed_result.scalar() or 0

            # Average duration
            avg_stmt = select(func.avg(TestRun.total_duration)).where(
                and_(
                    TestRun.created_at >= start_date,
                    TestRun.created_at <= end_date,
                    TestRun.total_duration.isnot(None)
                )
            )
            avg_result = await db_session.execute(avg_stmt)
            avg_duration = avg_result.scalar() or 0

            return {
                'total_runs': total_runs,
                'passed': passed,
                'failed': failed,
                'avg_duration': float(avg_duration)
            }

        except Exception as e:
            logger.error(f"Error getting stats for date range: {e}")
            raise
