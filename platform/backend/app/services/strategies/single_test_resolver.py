"""
Single Test Resolver Strategy

Handles resolution of single test schedules.
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from .schedule_resolver_strategy import ScheduleResolverStrategy


logger = logging.getLogger(__name__)


class SingleTestResolver(ScheduleResolverStrategy):
    """
    Strategy for resolving single test schedules.

    For 'single' schedule type, returns the test_definition_id
    directly from the schedule configuration.
    """

    async def resolve(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve single test schedule.

        Args:
            schedule: Schedule object with schedule_type='single'
            db: Database session (not used for single test resolution)

        Returns:
            List containing single test definition ID

        Raises:
            ValueError: If test_definition_id is not set
        """
        self.validate_schedule(schedule)

        test_id = schedule.test_definition_id

        logger.info(
            "Resolved single test schedule %d to test definition ID %d",
            schedule.id,
            test_id
        )

        return [test_id]

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "SingleTestResolver"

    def get_supported_schedule_types(self) -> List[str]:
        """Get supported schedule types."""
        return ['single']

    def validate_schedule(self, schedule: Schedule) -> None:
        """
        Validate single test schedule.

        Args:
            schedule: Schedule to validate

        Raises:
            ValueError: If test_definition_id is None
        """
        if schedule.test_definition_id is None:
            raise ValueError(
                f"Single test schedule {schedule.id} must have test_definition_id set"
            )
