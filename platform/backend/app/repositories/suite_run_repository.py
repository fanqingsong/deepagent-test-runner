"""
Suite Run Repository Implementation

Implements data access operations for suite runs using SQLAlchemy.
Follows the Repository Pattern and Dependency Inversion Principle.
"""

import logging
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.suite_run import SuiteRun, SuiteRunEntry
from app.repositories.interfaces.suite_run_repository_interface import ISuiteRunRepository

logger = logging.getLogger(__name__)


class SQLAlchemySuiteRunRepository(ISuiteRunRepository):
    """
    SQLAlchemy implementation of suite run repository.

    Provides data access operations for SuiteRun and SuiteRunEntry models,
    isolating database logic from business logic (Single Responsibility Principle).
    """

    async def create(
        self,
        suite_id: int,
        run_id: str,
        status: str,
        execution_mode: str,
        total_tests: int,
        environment: dict,
        triggered_by: str,
        start_time: int,
        db_session: AsyncSession
    ) -> SuiteRun:
        """Create a new suite run."""
        suite_run = SuiteRun(
            suite_id=suite_id,
            run_id=run_id,
            status=status,
            execution_mode=execution_mode,
            total_tests=total_tests,
            environment=environment,
            triggered_by=triggered_by,
            start_time=start_time,
        )

        db_session.add(suite_run)
        await db_session.flush()

        logger.info(f"Created suite run {run_id} for suite {suite_id}")
        return suite_run

    async def get_by_run_id(
        self,
        run_id: str,
        db_session: AsyncSession,
        load_entries: bool = False
    ) -> Optional[SuiteRun]:
        """Get a suite run by run_id."""
        query = select(SuiteRun).where(SuiteRun.run_id == run_id)

        if load_entries:
            query = query.options(selectinload(SuiteRun.entries))

        result = await db_session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_id(
        self,
        suite_run_id: int,
        db_session: AsyncSession,
        load_entries: bool = False
    ) -> Optional[SuiteRun]:
        """Get a suite run by database ID."""
        query = select(SuiteRun).where(SuiteRun.id == suite_run_id)

        if load_entries:
            query = query.options(selectinload(SuiteRun.entries))

        result = await db_session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        suite_run_id: int,
        status: str,
        end_time: Optional[int] = None,
        error: Optional[str] = None,
        db_session: AsyncSession
    ) -> Optional[SuiteRun]:
        """Update suite run status."""
        suite_run = await self.get_by_id(suite_run_id, db_session)

        if not suite_run:
            return None

        suite_run.status = status

        if end_time is not None:
            suite_run.end_time = end_time

        if error is not None:
            suite_run.error = error

        await db_session.flush()

        logger.debug(f"Updated suite run {suite_run_id} status to {status}")
        return suite_run

    async def update_final_results(
        self,
        suite_run_id: int,
        passed: int,
        failed: int,
        skipped: int,
        total_duration: Optional[int] = None,
        db_session: AsyncSession
    ) -> Optional[SuiteRun]:
        """Update suite run with final execution results."""
        suite_run = await self.get_by_id(suite_run_id, db_session)

        if not suite_run:
            return None

        suite_run.passed = passed
        suite_run.failed = failed
        suite_run.skipped = skipped

        if total_duration is not None:
            suite_run.total_duration = total_duration

        # Determine overall status
        if failed > 0:
            suite_run.status = "failed"
        elif skipped > 0 and passed == suite_run.total_tests - skipped:
            suite_run.status = "passed"
        elif passed == suite_run.total_tests:
            suite_run.status = "passed"
        else:
            suite_run.status = "partial"

        await db_session.flush()

        logger.debug(
            f"Updated suite run {suite_run_id} final results: "
            f"passed={passed}, failed={failed}, skipped={skipped}"
        )
        return suite_run

    async def list_by_suite_id(
        self,
        suite_id: int,
        skip: int = 0,
        limit: int = 50,
        db_session: AsyncSession
    ) -> List[SuiteRun]:
        """List suite runs for a specific suite."""
        result = await db_session.execute(
            select(SuiteRun)
            .where(SuiteRun.suite_id == suite_id)
            .order_by(SuiteRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_entries(
        self,
        suite_run_id: int,
        db_session: AsyncSession
    ) -> List[SuiteRunEntry]:
        """Get all entries for a suite run."""
        result = await db_session.execute(
            select(SuiteRunEntry)
            .where(SuiteRunEntry.suite_run_id == suite_run_id)
            .order_by(SuiteRunEntry.entry_order)
        )
        return list(result.scalars().all())

    async def create_entries(
        self,
        suite_run_id: int,
        entries: List[dict],
        db_session: AsyncSession
    ) -> List[SuiteRunEntry]:
        """Create suite run entries."""
        entry_rows = [
            SuiteRunEntry(
                suite_run_id=suite_run_id,
                test_definition_id=e["test_definition_id"],
                entry_order=e.get("order", e.get("entry_order", idx + 1)),
                condition=e.get("condition", "always"),
            )
            for idx, e in enumerate(entries)
        ]

        db_session.add_all(entry_rows)
        await db_session.flush()

        logger.info(f"Created {len(entry_rows)} entries for suite run {suite_run_id}")
        return entry_rows

    async def update_entry_status(
        self,
        entry_id: int,
        status: str,
        started_at: Optional[int] = None,
        finished_at: Optional[int] = None,
        test_run_id: Optional[str] = None,
        error_message: Optional[str] = None,
        duration: Optional[int] = None,
        db_session: AsyncSession
    ) -> Optional[SuiteRunEntry]:
        """Update suite run entry status."""
        result = await db_session.execute(
            select(SuiteRunEntry).where(SuiteRunEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return None

        entry.status = status

        if started_at is not None:
            entry.started_at = started_at

        if finished_at is not None:
            entry.finished_at = finished_at

        if test_run_id is not None:
            entry.test_run_id = test_run_id

        if error_message is not None:
            entry.error_message = error_message

        if duration is not None:
            entry.duration = duration

        await db_session.flush()

        logger.debug(f"Updated entry {entry_id} status to {status}")
        return entry

    async def cancel_pending_entries(
        self,
        suite_run_id: int,
        from_order: int,
        db_session: AsyncSession
    ) -> int:
        """Cancel all pending entries from a specific order."""
        import time

        now_ms = int(time.time() * 1000)

        # Get entries to cancel
        result = await db_session.execute(
            select(SuiteRunEntry).where(
                SuiteRunEntry.suite_run_id == suite_run_id,
                SuiteRunEntry.entry_order >= from_order,
                SuiteRunEntry.status.in_(["pending", "dispatched"])
            )
        )
        entries = result.scalars().all()

        # Update each entry
        for entry in entries:
            entry.status = "skipped"
            entry.finished_at = now_ms

        await db_session.flush()

        logger.info(f"Canceled {len(entries)} entries for suite run {suite_run_id}")
        return len(entries)
