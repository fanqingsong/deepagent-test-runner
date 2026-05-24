"""
Analytics Service - Data analysis and aggregation queries
Handles dashboard statistics and test analytics
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, cast, Float
from sqlalchemy.sql import text


class AnalyticsService:
    """Service for test analytics and dashboard data"""

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
                "start_time": row.start_time,  # Already milliseconds as bigint
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
                # Add fields expected by frontend
                "duration": row.total_duration,  # Frontend expects 'duration'
                "timestamp": row.start_time  # Frontend expects 'timestamp'
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

        # Select only columns that exist in the database (avoid model-only fields)
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

    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Get dashboard summary statistics

        Args:
            db: Database session
            days: Number of days to look back
            user_id: Filter by user ID (if not admin)
            is_admin: Whether user is admin (bypasses user filter)

        Returns:
            Dictionary with summary statistics
        """
        from app.models.test_run import TestRun
        from app.models.test_definition import TestDefinition

        start_time = datetime.utcnow() - timedelta(days=days)

        # Build query
        total_runs_col = func.count(TestRun.id).label('total_runs')
        total_passed_col = func.sum(TestRun.passed).label('total_passed')
        total_failed_col = func.sum(TestRun.failed).label('total_failed')
        total_tests_col = func.sum(TestRun.total_tests).label('total_tests')
        avg_duration_col = func.avg(TestRun.total_duration).label('avg_duration')
        successful_runs_col = func.sum(
            case((TestRun.status == 'passed', 1), else_=0)
        ).label('successful_runs')
        failed_runs_col = func.sum(
            case((TestRun.status == 'failed', 1), else_=0)
        ).label('failed_runs')
        runs_with_duration_col = func.sum(
            case((TestRun.total_duration.isnot(None), 1), else_=0)
        ).label('runs_with_duration')

        query = select(
            total_runs_col,
            total_passed_col,
            total_failed_col,
            total_tests_col,
            avg_duration_col,
            successful_runs_col,
            failed_runs_col,
            runs_with_duration_col
        ).select_from(
            TestRun
        ).outerjoin(
            TestDefinition,
            TestRun.test_definition_id == TestDefinition.id
        ).where(
            TestRun.created_at > start_time
        )

        # Filter by user if not admin
        if not is_admin and user_id:
            query = query.where(TestDefinition.created_by == user_id)

        result = await db.execute(query)
        row = result.first()

        return {
            "total_runs": row.total_runs or 0,
            "total_passed": row.total_passed or 0,
            "total_failed": row.total_failed or 0,
            "total_tests": row.total_tests or 0,
            "avg_duration": float(row.avg_duration) if row.avg_duration else 0,
            "successful_runs": row.successful_runs or 0,
            "failed_runs": row.failed_runs or 0,
            "runs_with_duration": row.runs_with_duration or 0
        }

    async def get_total_test_definitions(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> int:
        """
        Get total count of active test definitions

        Args:
            db: Database session
            user_id: Filter by user ID (if not admin)
            is_admin: Whether user is admin (bypasses user filter)

        Returns:
            Total count of active test definitions
        """
        from app.models.test_definition import TestDefinition

        query = select(func.count(TestDefinition.id)).where(
            TestDefinition.is_active == True
        )

        # Filter by user if not admin
        if not is_admin and user_id:
            query = query.where(TestDefinition.created_by == user_id)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_test_runs_by_day(
        self,
        db: AsyncSession,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get test runs grouped by day

        Args:
            db: Database session
            days: Number of days to look back
            user_id: Filter by user ID (if not admin)
            is_admin: Whether user is admin (bypasses user filter)

        Returns:
            List of daily statistics
        """
        from app.models.test_run import TestRun
        from app.models.test_definition import TestDefinition

        start_time = datetime.utcnow() - timedelta(days=days)

        # Truncate to day and group
        date_col = func.date_trunc('day', TestRun.created_at).label('date')

        query = select(
            date_col,
            func.count(TestRun.id).label('total_runs'),
            func.sum(TestRun.passed).label('total_passed'),
            func.sum(TestRun.failed).label('total_failed'),
            func.sum(TestRun.total_tests).label('total_tests')
        ).select_from(
            TestRun
        ).outerjoin(
            TestDefinition,
            TestRun.test_definition_id == TestDefinition.id
        ).where(
            TestRun.created_at > start_time
        )

        # Filter by user if not admin
        if not is_admin and user_id:
            query = query.where(TestDefinition.created_by == user_id)

        query = query.group_by(date_col).order_by(date_col.desc())

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "total_runs": row.total_runs,
                "total_passed": row.total_passed or 0,
                "total_failed": row.total_failed or 0,
                "total_tests": row.total_tests or 0
            }
            for row in rows
        ]

    async def get_slowest_tests(
        self,
        db: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get slowest tests (average duration)

        Args:
            db: Database session
            limit: Maximum number of tests to return

        Returns:
            List of slowest tests
        """
        from app.models.test_case import TestCase

        subquery = (
            select(
                TestCase.test_id,
                func.avg(TestCase.duration).label('avg_duration'),
                func.count().label('run_count'),
                func.max(TestCase.duration).label('max_duration')
            )
            .where(TestCase.status == 'passed')
            .group_by(TestCase.test_id)
            .order_by(func.avg(TestCase.duration).desc())
            .limit(limit)
        ).subquery()

        query = select(subquery)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "test_id": row.test_id,
                "avg_duration": float(row.avg_duration) if row.avg_duration else 0,
                "run_count": row.run_count,
                "max_duration": float(row.max_duration) if row.max_duration else 0
            }
            for row in rows
        ]

    async def get_flaky_tests(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get flaky tests (tests with both passes and failures)

        Args:
            db: Database session
            days: Number of days to look back

        Returns:
            List of flaky tests with failure rates
        """
        from app.models.test_case import TestCase
        from app.models.test_run import TestRun

        start_time = datetime.utcnow() - timedelta(days=days)

        subquery = (
            select(
                TestCase.test_id,
                func.count().label('total_runs'),
                func.sum(
                    case((TestCase.status == 'passed', 1), else_=0)
                ).label('passed_runs'),
                func.sum(
                    case((TestCase.status == 'failed', 1), else_=0)
                ).label('failed_runs')
            )
            .join(TestRun, TestCase.run_id == TestRun.id)
            .where(TestRun.start_time > start_time)
            .group_by(TestCase.test_id)
            .having(
                func.count() > 1,
                func.sum(case((TestCase.status == 'failed', 1), else_=0)) > 0
            )
        ).subquery()

        # Calculate failure rate
        failure_rate = (
            100.0 * subquery.c.failed_runs / cast(subquery.c.total_runs, Float)
        ).label('failure_rate')

        query = select(
            subquery.c.test_id,
            subquery.c.total_runs,
            subquery.c.passed_runs,
            subquery.c.failed_runs,
            failure_rate
        ).order_by(failure_rate.desc())

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "test_id": row.test_id,
                "total_runs": row.total_runs,
                "passed_runs": row.passed_runs,
                "failed_runs": row.failed_runs,
                "failure_rate": float(row.failure_rate) if row.failure_rate else 0
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

        Uses TestDefinition.source_app_id to find all definitions
        belonging to the app, then returns all runs for those definitions.
        """
        from app.models.test_run import TestRun
        from app.models.test_definition import TestDefinition

        td_ids = (
            select(TestDefinition.id)
            .where(TestDefinition.source_app_id == app_id)
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

    async def get_suite_dashboard_summary(
        self,
        db: AsyncSession,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        from app.models.test_suite import TestSuite
        from app.models.suite_run import SuiteRun

        start_time = datetime.utcnow() - timedelta(days=days)

        total_suites_query = select(func.count(TestSuite.id))
        if not is_admin and user_id:
            total_suites_query = total_suites_query.where(TestSuite.created_by == str(user_id))
        total_suites_result = await db.execute(total_suites_query)
        total_suites = total_suites_result.scalar() or 0

        runs_query = select(
            func.count(SuiteRun.id).label('total_runs'),
            func.sum(SuiteRun.passed).label('total_passed'),
            func.sum(SuiteRun.failed).label('total_failed'),
            func.avg(SuiteRun.total_duration).label('avg_duration'),
            func.sum(SuiteRun.total_tests).label('total_tests_executed'),
        ).where(SuiteRun.created_at > start_time)

        if not is_admin and user_id:
            suite_ids = select(TestSuite.id).where(TestSuite.created_by == str(user_id))
            runs_query = runs_query.where(SuiteRun.suite_id.in_(suite_ids))

        runs_result = await db.execute(runs_query)
        row = runs_result.first()

        total_passed = row.total_passed or 0
        total_failed = row.total_failed or 0
        total_run_count = (total_passed + total_failed) or 1

        return {
            "total_suites": total_suites,
            "total_runs": row.total_runs or 0,
            "pass_rate": round(total_passed / total_run_count * 100, 1),
            "avg_duration": float(row.avg_duration) if row.avg_duration else 0,
            "total_tests_executed": row.total_tests_executed or 0,
        }

    async def get_suites_with_latest_run(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        from app.models.test_suite import TestSuite
        from app.models.suite_run import SuiteRun

        query = select(TestSuite).order_by(TestSuite.created_at.desc())
        if not is_admin and user_id:
            query = query.where(TestSuite.created_by == str(user_id))

        result = await db.execute(query)
        suites = list(result.scalars().all())

        suite_list = []
        for suite in suites:
            test_count = len(suite.suite_entries) if suite.suite_entries else len(suite.test_definition_ids or [])

            latest_run_query = (
                select(SuiteRun)
                .where(SuiteRun.suite_id == suite.id)
                .order_by(SuiteRun.created_at.desc())
                .limit(1)
            )
            latest_result = await db.execute(latest_run_query)
            latest_run = latest_result.scalar_one_or_none()

            latest_run_data = None
            if latest_run:
                latest_run_data = {
                    "run_id": latest_run.run_id,
                    "status": latest_run.status,
                    "passed": latest_run.passed,
                    "failed": latest_run.failed,
                    "total_tests": latest_run.total_tests,
                    "total_duration": latest_run.total_duration,
                    "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None,
                }

            suite_list.append({
                "id": suite.id,
                "name": suite.name,
                "description": suite.description,
                "execution_mode": suite.execution_mode,
                "fail_strategy": suite.fail_strategy,
                "test_count": test_count,
                "is_dynamic": suite.is_dynamic,
                "tags": suite.tags or [],
                "latest_run": latest_run_data,
            })

        return suite_list

    async def get_suite_run_timeline(
        self,
        db: AsyncSession,
        suite_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        from app.models.suite_run import SuiteRun, SuiteRunEntry
        from app.models.test_definition import TestDefinition

        runs_query = (
            select(SuiteRun)
            .where(SuiteRun.suite_id == suite_id)
            .order_by(SuiteRun.created_at.desc())
            .limit(limit)
        )
        runs_result = await db.execute(runs_query)
        runs = list(runs_result.scalars().all())

        timeline = []
        for run in runs:
            entries_query = (
                select(
                    SuiteRunEntry.id,
                    SuiteRunEntry.entry_order,
                    SuiteRunEntry.test_definition_id,
                    SuiteRunEntry.status,
                    SuiteRunEntry.duration,
                    SuiteRunEntry.error_message,
                    SuiteRunEntry.condition,
                    TestDefinition.name.label('test_name'),
                )
                .outerjoin(TestDefinition, SuiteRunEntry.test_definition_id == TestDefinition.id)
                .where(SuiteRunEntry.suite_run_id == run.id)
                .order_by(SuiteRunEntry.entry_order)
            )
            entries_result = await db.execute(entries_query)
            entry_rows = entries_result.all()

            entries = [
                {
                    "entry_order": row.entry_order,
                    "test_definition_id": row.test_definition_id,
                    "test_name": row.test_name or f"Test #{row.entry_order}",
                    "status": row.status,
                    "duration": row.duration,
                    "error_message": row.error_message,
                    "condition": row.condition,
                }
                for row in entry_rows
            ]

            timeline.append({
                "id": run.id,
                "run_id": run.run_id,
                "status": run.status,
                "execution_mode": run.execution_mode,
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "total_tests": run.total_tests,
                "total_duration": run.total_duration,
                "triggered_by": run.triggered_by,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "entries": entries,
            })

        return timeline

    async def get_suite_run_with_test_cases(
        self,
        db: AsyncSession,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        from app.models.suite_run import SuiteRun, SuiteRunEntry
        from app.models.test_definition import TestDefinition
        from app.models.test_case import TestCase
        from app.models.test_run import TestRun

        run_query = select(SuiteRun).where(SuiteRun.run_id == run_id)
        run_result = await db.execute(run_query)
        suite_run = run_result.scalar_one_or_none()
        if not suite_run:
            return None

        entries_query = (
            select(
                SuiteRunEntry.id,
                SuiteRunEntry.entry_order,
                SuiteRunEntry.test_definition_id,
                SuiteRunEntry.test_run_id,
                SuiteRunEntry.status,
                SuiteRunEntry.duration,
                SuiteRunEntry.error_message,
                SuiteRunEntry.condition,
                TestDefinition.name.label('test_name'),
            )
            .outerjoin(TestDefinition, SuiteRunEntry.test_definition_id == TestDefinition.id)
            .where(SuiteRunEntry.suite_run_id == suite_run.id)
            .order_by(SuiteRunEntry.entry_order)
        )
        entries_result = await db.execute(entries_query)
        entry_rows = entries_result.all()

        entries = []
        for row in entry_rows:
            entry_data = {
                "entry_order": row.entry_order,
                "test_definition_id": row.test_definition_id,
                "test_name": row.test_name or f"Test #{row.entry_order}",
                "status": row.status,
                "duration": row.duration,
                "error_message": row.error_message,
                "condition": row.condition,
                "test_cases": [],
            }

            if row.test_run_id:
                test_run_pk = (
                    select(TestRun.id)
                    .where(TestRun.run_id == row.test_run_id)
                )
                tr_result = await db.execute(test_run_pk)
                tr_pk = tr_result.scalar_one_or_none()

                if tr_pk:
                    tc_query = (
                        select(
                            TestCase.test_id,
                            TestCase.description,
                            TestCase.status,
                            TestCase.duration,
                            TestCase.error_message,
                        )
                        .where(TestCase.run_id == tr_pk)
                        .order_by(TestCase.id)
                    )
                    tc_result = await db.execute(tc_query)
                    entry_data["test_cases"] = [
                        {
                            "test_id": tc.test_id,
                            "description": tc.description,
                            "status": tc.status,
                            "duration": tc.duration,
                            "error_message": tc.error_message,
                        }
                        for tc in tc_result.all()
                    ]

            entries.append(entry_data)

        return {
            "run_id": suite_run.run_id,
            "status": suite_run.status,
            "execution_mode": suite_run.execution_mode,
            "passed": suite_run.passed,
            "failed": suite_run.failed,
            "skipped": suite_run.skipped,
            "total_tests": suite_run.total_tests,
            "total_duration": suite_run.total_duration,
            "triggered_by": suite_run.triggered_by,
            "created_at": suite_run.created_at.isoformat() if suite_run.created_at else None,
            "entries": entries,
        }

    async def get_failure_patterns(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get common failure patterns (error messages)

        Args:
            db: Database session
            limit: Maximum number of patterns to return

        Returns:
            List of failure patterns
        """
        from app.models.test_case import TestCase

        query = select(
            TestCase.error_message,
            func.count().label('count'),
            func.max(TestCase.test_id).label('example_test')
        ).where(
            TestCase.status == 'failed',
            TestCase.error_message.isnot(None)
        ).group_by(
            TestCase.error_message
        ).order_by(
            func.count().desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "error_message": row.error_message,
                "count": row.count,
                "example_test": row.example_test
            }
            for row in rows
        ]
