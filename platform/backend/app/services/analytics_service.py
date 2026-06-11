"""
Analytics Service - Data analysis and aggregation queries

Refactored into focused modules:
- DashboardAnalytics: Summary statistics and overview data
- TestRunsAnalytics: Test run data retrieval
- PerformanceAnalytics: Slowest tests, flaky tests, failure patterns
- SuitesAnalytics: Test suite analysis
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

# Import the split service modules
from app.services.analytics.analytics_dashboard import DashboardAnalytics
from app.services.analytics.analytics_test_runs import TestRunsAnalytics
from app.services.analytics.analytics_performance import PerformanceAnalytics
from app.services.analytics.analytics_suites import SuitesAnalytics


class AnalyticsService:
    """Service for test analytics and dashboard data"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._dashboard = DashboardAnalytics()
        self._test_runs = TestRunsAnalytics()
        self._performance = PerformanceAnalytics()
        self._suites = SuitesAnalytics()

    # ------------------------------------------------------------------
    # Dashboard summary queries (delegated to DashboardAnalytics)
    # ------------------------------------------------------------------

    async def get_dashboard_summary(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        return await self._dashboard.get_dashboard_summary(self.db, days, user_id, is_admin)

    async def get_total_test_definitions(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> int:
        return await self._dashboard.get_total_test_definitions(self.db, user_id, is_admin)

    async def get_test_runs_by_day(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        return await self._dashboard.get_test_runs_by_day(self.db, days, user_id, is_admin)

    # ------------------------------------------------------------------
    # Test run queries (delegated to TestRunsAnalytics)
    # ------------------------------------------------------------------

    async def get_recent_test_runs(
        self,
        limit: int = 100,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        return await self._test_runs.get_recent_test_runs(self.db, limit, user_id, is_admin)

    async def get_test_cases_for_run(
        self,
        run_id: str
    ) -> List[Dict[str, Any]]:
        return await self._test_runs.get_test_cases_for_run(self.db, run_id)

    async def get_test_runs_for_app(
        self,
        app_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        return await self._test_runs.get_test_runs_for_app(self.db, app_id, limit, offset)

    # ------------------------------------------------------------------
    # Performance analysis (delegated to PerformanceAnalytics)
    # ------------------------------------------------------------------

    async def get_slowest_tests(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        return await self._performance.get_slowest_tests(self.db, limit)

    async def get_flaky_tests(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        return await self._performance.get_flaky_tests(self.db, days)

    async def get_failure_patterns(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        return await self._performance.get_failure_patterns(self.db, limit)

    # ------------------------------------------------------------------
    # Suite analytics (delegated to SuitesAnalytics)
    # ------------------------------------------------------------------

    async def get_suite_dashboard_summary(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        return await self._suites.get_suite_dashboard_summary(self.db, days, user_id, is_admin)

    async def get_suites_with_latest_run(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        return await self._suites.get_suites_with_latest_run(self.db, user_id, is_admin)

    async def get_suite_run_timeline(
        self,
        suite_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        return await self._suites.get_suite_run_timeline(self.db, suite_id, limit)

    async def get_suite_run_with_test_cases(
        self,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self._suites.get_suite_run_with_test_cases(self.db, run_id)
