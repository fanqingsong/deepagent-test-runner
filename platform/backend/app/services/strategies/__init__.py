"""
Schedule Resolver Strategies

This module contains the strategy pattern implementation for schedule resolution.
Each strategy handles a specific schedule type, following the Open/Closed Principle:
- Open for extension: New strategies can be added without modifying existing code
- Closed for modification: Existing strategies remain stable

Usage:
    from app.services.strategies import ScheduleResolverFactory

    # Get appropriate strategy for schedule type
    strategy = ScheduleResolverFactory.get_strategy('single')
    test_ids = await strategy.resolve(schedule, db)

    # Register custom strategy
    ScheduleResolverFactory.register_strategy('custom', CustomResolver())
"""

from .schedule_resolver_strategy import ScheduleResolverStrategy
from .schedule_resolver_factory import ScheduleResolverFactory

__all__ = [
    'ScheduleResolverStrategy',
    'ScheduleResolverFactory',
]
