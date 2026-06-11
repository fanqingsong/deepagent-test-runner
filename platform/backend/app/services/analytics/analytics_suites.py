"""
Suites Analytics

Provides test suite analysis and suite run data retrieval.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


class SuitesAnalytics:
    """Test suite analytics and suite run queries."""

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
