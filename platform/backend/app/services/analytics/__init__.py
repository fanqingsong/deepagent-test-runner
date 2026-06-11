"""
Analytics Module

Data analysis and aggregation queries for dashboards and test analytics.
Split into focused modules:
- DashboardAnalytics: Summary statistics and overview data
- TestRunsAnalytics: Test run data retrieval
- PerformanceAnalytics: Slowest tests, flaky tests, failure patterns
- SuitesAnalytics: Test suite analysis
"""

from .analytics_dashboard import DashboardAnalytics
from .analytics_test_runs import TestRunsAnalytics
from .analytics_performance import PerformanceAnalytics
from .analytics_suites import SuitesAnalytics

__all__ = [
    "DashboardAnalytics",
    "TestRunsAnalytics",
    "PerformanceAnalytics",
    "SuitesAnalytics",
]
