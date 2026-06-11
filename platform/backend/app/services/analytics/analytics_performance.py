"""
Performance Analytics

Provides slowest tests, flaky tests, and failure pattern analysis.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import select, func, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession


class PerformanceAnalytics:
    """Performance and reliability analysis queries."""

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
