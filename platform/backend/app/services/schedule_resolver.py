"""
Schedule Resolver

Resolves schedules to test definition IDs based on schedule type.
Refactored to use Strategy Pattern following Open/Closed Principle.
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory


logger = logging.getLogger(__name__)


class ScheduleResolver:
    """
    Handles resolution of schedules to test definition IDs.

    Single responsibility: Convert schedule configurations into
    lists of executable test definition IDs based on schedule type.

    This class now uses the Strategy Pattern to delegate resolution
    to appropriate strategy implementations, following SOLID principles:
    - Single Responsibility: Delegates to specialized strategies
    - Open/Closed: Open for extension (new strategies), closed for modification
    - Dependency Inversion: Depends on abstraction (strategy interface)

    Usage:
        resolver = ScheduleResolver()
        test_ids = await resolver.resolve_schedule(schedule, db)

    Adding new schedule types:
        1. Create new strategy class extending ScheduleResolverStrategy
        2. Register with factory: ScheduleResolverFactory.register_strategy()
        3. No changes needed to this class!
    """

    def __init__(self, factory: ScheduleResolverFactory = None):
        """
        Initialize schedule resolver.

        Args:
            factory: Optional factory instance for dependency injection.
                    Defaults to ScheduleResolverFactory class.
                    Primarily used for testing with mock factories.
        """
        self._factory = factory or ScheduleResolverFactory
        logger.info("Initialized ScheduleResolver with Strategy Pattern")

    async def resolve_schedule(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve target test definition IDs based on schedule type.

        Uses Strategy Pattern to delegate resolution to appropriate
        strategy implementation based on schedule_type.

        Args:
            schedule: Schedule object containing schedule configuration
            db: Async database session for queries

        Returns:
            List of test definition IDs to execute

        Raises:
            ValueError: If schedule_type is unknown or required data is missing

        Example:
            ```python
            resolver = ScheduleResolver()
            schedule = Schedule(
                name="My Test",
                schedule_type="single",
                test_definition_id=5
            )
            test_ids = await resolver.resolve_schedule(schedule, db)
            # Returns: [5]
            ```
        """
        logger.debug(
            "Resolving schedule %d (type=%s) using Strategy Pattern",
            schedule.id,
            schedule.schedule_type
        )

        # Get appropriate strategy from factory
        strategy = self._factory.get_strategy_for_schedule(schedule)

        # Delegate resolution to strategy
        test_ids = await strategy.resolve(schedule, db)

        logger.info(
            "Resolved schedule %d (%s) to %d test definitions: %s",
            schedule.id,
            schedule.schedule_type,
            len(test_ids),
            test_ids[:10] if len(test_ids) > 10 else test_ids  # Log first 10
        )

        return test_ids
