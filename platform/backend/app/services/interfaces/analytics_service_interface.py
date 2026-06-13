"""
Analytics Service Interface

Composed interface for analytics operations.
Following Interface Segregation Principle - composed of focused interfaces.
"""

from abc import ABC
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

# Import focused analytics interfaces
from app.services.interfaces.analytics.dashboard_analytics_interface import IDashboardAnalytics
from app.services.interfaces.analytics.test_run_analytics_interface import ITestRunAnalytics
from app.services.interfaces.analytics.performance_analytics_interface import IPerformanceAnalytics
from app.services.interfaces.analytics.suite_analytics_interface import ISuiteAnalytics


class IAnalyticsService(IDashboardAnalytics, ITestRunAnalytics, IPerformanceAnalytics, ISuiteAnalytics):
    """
    Composed analytics service interface.

    This interface combines multiple focused interfaces following the
    Interface Segregation Principle. Clients can depend on specific
    sub-interfaces (IDashboardAnalytics, ITestRunAnalytics, etc.) if they
    only need specific functionality, or on this composed interface if they
    need full analytics capabilities.

    This approach ensures:
    - No client is forced to depend on methods it doesn't use (ISP)
    - Easy to extend with new analytics capabilities (OCP)
    - Clear separation of concerns (SRP)
    - Interchangeable implementations (LSP)
    - Depends on abstractions (DIP)
    """

    pass  # All methods are inherited from composed interfaces
