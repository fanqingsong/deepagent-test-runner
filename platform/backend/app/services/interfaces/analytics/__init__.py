"""
Analytics Interfaces Package

Focused interfaces for analytics operations following Interface Segregation Principle.

This package contains specialized interfaces for different analytics domains:
- IDashboardAnalytics: Dashboard summary operations
- ITestRunAnalytics: Test run data retrieval
- IPerformanceAnalytics: Performance analysis
- ISuiteAnalytics: Suite analytics and reporting

Clients should depend on the specific interface they need rather than
the general IAnalyticsService interface, following Interface Segregation Principle.
"""

from app.services.interfaces.analytics.dashboard_analytics_interface import IDashboardAnalytics
from app.services.interfaces.analytics.test_run_analytics_interface import ITestRunAnalytics
from app.services.interfaces.analytics.performance_analytics_interface import IPerformanceAnalytics
from app.services.interfaces.analytics.suite_analytics_interface import ISuiteAnalytics

__all__ = [
    "IDashboardAnalytics",
    "ITestRunAnalytics",
    "IPerformanceAnalytics",
    "ISuiteAnalytics",
]
