"""
Suite Resolver Strategy

Handles resolution of test suite schedules.
"""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.test_suite import TestSuite
from .schedule_resolver_strategy import ScheduleResolverStrategy


logger = logging.getLogger(__name__)


class SuiteResolver(ScheduleResolverStrategy):
    """
    Strategy for resolving test suite schedules.

    For 'suite' schedule type, fetches the test suite from
    database and returns all associated test definition IDs.
    """

    async def resolve(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve test suite schedule.

        Args:
            schedule: Schedule object with schedule_type='suite'
            db: Database session for querying test suite

        Returns:
            List of test definition IDs from the suite

        Raises:
            ValueError: If test suite not found or test_suite_id is not set
        """
        self.validate_schedule(schedule)

        stmt = select(TestSuite).where(TestSuite.id == schedule.test_suite_id)
        result = await db.execute(stmt)
        suite = result.scalar_one_or_none()

        if not suite:
            raise ValueError(
                f"Test suite {schedule.test_suite_id} not found for schedule {schedule.id}"
            )

        logger.info(
            "Resolved suite %d to %d test definitions for schedule %d",
            suite.id,
            len(suite.test_definition_ids),
            schedule.id
        )

        return suite.test_definition_ids

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "SuiteResolver"

    def get_supported_schedule_types(self) -> List[str]:
        """Get supported schedule types."""
        return ['suite']

    def validate_schedule(self, schedule: Schedule) -> None:
        """
        Validate test suite schedule.

        Args:
            schedule: Schedule to validate

        Raises:
            ValueError: If test_suite_id is None
        """
        if schedule.test_suite_id is None:
            raise ValueError(
                f"Suite schedule {schedule.id} must have test_suite_id set"
            )
