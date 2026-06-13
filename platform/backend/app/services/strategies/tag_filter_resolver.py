"""
Tag Filter Resolver Strategy

Handles resolution of tag filter schedules.
"""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.test_definition import TestDefinition
from .schedule_resolver_strategy import ScheduleResolverStrategy


logger = logging.getLogger(__name__)


class TagFilterResolver(ScheduleResolverStrategy):
    """
    Strategy for resolving tag filter schedules.

    For 'tag_filter' schedule type, queries the database for
    all test definitions matching the specified tag filter.
    """

    async def resolve(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve tag filter schedule.

        Args:
            schedule: Schedule object with schedule_type='tag_filter'
            db: Database session for querying test definitions

        Returns:
            List of test definition IDs matching the tag filter
        """
        if not schedule.tag_filter:
            logger.warning(
                "Schedule %s has schedule_type='tag_filter' but no tag_filter set",
                schedule.id
            )
            return []

        stmt = select(TestDefinition.id).where(
            TestDefinition.tags.any(schedule.tag_filter)
        ).where(TestDefinition.is_draft == False)

        result = await db.execute(stmt)
        ids = [row[0] for row in result.fetchall()]

        logger.info(
            "Tag filter '%s' resolved to %d test definitions for schedule %d",
            schedule.tag_filter,
            len(ids),
            schedule.id
        )

        return ids

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "TagFilterResolver"

    def get_supported_schedule_types(self) -> List[str]:
        """Get supported schedule types."""
        return ['tag_filter']

    def validate_schedule(self, schedule: Schedule) -> None:
        """
        Validate tag filter schedule.

        Note: Empty tag_filter is allowed (returns empty list).
        This method can be called for pre-validation but empty tags
        are handled gracefully in resolve().

        Args:
            schedule: Schedule to validate
        """
        # Tag filter allows None/empty values - handled in resolve()
        pass
