"""
Test Runs Analytics

Provides test run data retrieval and test case details.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestRunsAnalytics:
    """Test run and test case queries."""

    async def get_recent_test_runs(
        self,
        db: AsyncSession,
        limit: int = 100,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent test runs with test definition names

        Args:
            db: Database session
            limit: Maximum number of runs to return
            user_id: Filter by user ID (if not admin)
            is_admin: Whether user is admin (bypasses user filter)

        Returns:
            List of test runs with metadata
        """
        from app.models.test_run import TestRun
        from app.models.test_definition import TestDefinition

        query = (
            select(
                TestRun.id,
                TestRun.run_id,
                TestRun.start_time,
                TestRun.end_time,
                TestRun.total_tests,
                TestRun.passed,
                TestRun.failed,
                TestRun.skipped,
                TestRun.total_duration,
                TestRun.status,
                TestRun.created_at,
                TestRun.test_definition_id,
                TestRun.error_message,
                TestDefinition.name.label('test_name'),
                TestDefinition.created_by.label('test_owner')
            )
            .outerjoin(TestDefinition, TestRun.test_definition_id == TestDefinition.id)
            .order_by(TestRun.created_at.desc())
            .limit(limit)
        )

        # Filter by user if not admin
        if not is_admin and user_id:
            query = query.where(TestDefinition.created_by == user_id)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "total_tests": row.total_tests,
                "passed": row.passed,
                "failed": row.failed,
                "skipped": row.skipped,
                "total_duration": row.total_duration,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "test_definition_id": row.test_definition_id,
                "error_message": row.error_message,
                "test_name": row.test_name,
                "test_owner": row.test_owner,
                "duration": row.total_duration,
                "timestamp": row.start_time
            }
            for row in rows
        ]

    async def get_test_cases_for_run(
        self,
        db: AsyncSession,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all test cases for a specific test run

        Args:
            db: Database session
            run_id: Test run UUID (string)

        Returns:
            List of test cases
        """
        from app.models.test_case import TestCase
        from app.models.test_run import TestRun

        # First, find the test run by UUID to get the primary key ID
        test_run_query = select(TestRun.id).where(TestRun.run_id == run_id)
        test_run_result = await db.execute(test_run_query)
        test_run_pk_id = test_run_result.scalar_one_or_none()

        if test_run_pk_id is None:
            return []

        query = select(
            TestCase.id,
            TestCase.test_id,
            TestCase.description,
            TestCase.status,
            TestCase.duration,
            TestCase.start_time,
            TestCase.end_time,
            TestCase.error_message,
            TestCase.screenshot_path,
            TestCase.created_at,
        ).where(
            TestCase.run_id == test_run_pk_id
        ).order_by(TestCase.id)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": row.id,
                "test_id": row.test_id,
                "description": row.description,
                "status": row.status,
                "duration": row.duration,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "error_message": row.error_message,
                "screenshot_path": row.screenshot_path,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in rows
        ]

    async def get_test_runs_for_app(
        self,
        db: AsyncSession,
        app_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all test runs for a specific app/studio.

        Uses TestDefinition.source_workspace_id to find all definitions
        belonging to the app, then returns all runs for those definitions.
        """
        from app.models.test_run import TestRun
        from app.models.test_definition import TestDefinition

        td_ids = (
            select(TestDefinition.id)
            .where(TestDefinition.source_workspace_id == app_id)
        )

        query = (
            select(
                TestRun.id,
                TestRun.run_id,
                TestRun.start_time,
                TestRun.end_time,
                TestRun.total_tests,
                TestRun.passed,
                TestRun.failed,
                TestRun.skipped,
                TestRun.total_duration,
                TestRun.status,
                TestRun.created_at,
                TestRun.test_definition_id,
                TestRun.error_message,
                TestDefinition.name.label('test_name'),
            )
            .outerjoin(TestDefinition, TestRun.test_definition_id == TestDefinition.id)
            .where(TestRun.test_definition_id.in_(td_ids))
            .order_by(TestRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "status": row.status,
                "passed": row.passed,
                "failed": row.failed,
                "total_tests": row.total_tests,
                "skipped": row.skipped,
                "total_duration": row.total_duration,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "error_message": row.error_message,
                "test_name": row.test_name,
                "duration": row.total_duration,
                "timestamp": row.start_time,
            }
            for row in rows
        ]
