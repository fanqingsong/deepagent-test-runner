"""
Schedule Manager Service

Manages schedule validation, cron parsing, and next run time calculation.
"""

import logging
from datetime import datetime, timezone
from typing import List

from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


class ScheduleManager:
    """
    Manages schedule operations.

    Responsible for:
    - Reading active schedules from database
    - Validating cron expressions
    - Calculating next run times
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_active_schedules(self) -> List[Schedule]:
        """Retrieve all active schedules from database."""
        stmt = select(Schedule).where(Schedule.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def validate_cron(self, cron_expression: str) -> bool:
        """Validate cron expression format."""
        try:
            base_time = datetime.now(timezone.utc)
            croniter(cron_expression, base_time)
            return True
        except (ValueError, KeyError):
            return False

    async def update_next_run_time(self, schedule: Schedule) -> None:
        """Calculate and update next run time for a schedule."""
        try:
            cron = croniter(schedule.cron_expression, datetime.now(timezone.utc))
            next_time = cron.get_next(datetime)
            schedule.next_run_time = next_time
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to calculate next run time for schedule {schedule.id}: {e}")
            raise

    def parse_cron_expression(self, cron_expr: str, tz_str: str = "UTC") -> datetime:
        """
        Parse cron expression and calculate next run time.

        Returns:
            Next run time as naive datetime object (without timezone info)
        """
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"Cron expression must have 5 parts, got {len(parts)}")

            import pytz
            try:
                tz = pytz.timezone(tz_str)
            except pytz.exceptions.UnknownTimeZoneError:
                tz = timezone.utc

            base_time = datetime.now(tz)
            cron = croniter(cron_expr, base_time)
            next_time = cron.get_next(datetime)
            next_time_utc = next_time.astimezone(timezone.utc)
            return next_time_utc.replace(tzinfo=None)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expr}': {str(e)}")
