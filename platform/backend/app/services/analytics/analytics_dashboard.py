"""
Dashboard Analytics

Provides summary statistics and overview data for dashboards.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardAnalytics:
    """Dashboard summary and overview queries."""

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
    ) -> list:
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
