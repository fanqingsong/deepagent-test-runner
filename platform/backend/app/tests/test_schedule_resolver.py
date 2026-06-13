"""
Unit tests for ScheduleResolver component.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schedule_resolver import ScheduleResolver
from app.models.schedule import Schedule
from app.models.test_suite import TestSuite
from app.models.test_definition import TestDefinition


class TestScheduleResolver:
    """Test suite for ScheduleResolver."""

    @pytest.mark.asyncio
    async def test_resolve_single_schedule(self):
        """Test resolving single test schedule."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Single Test",
            schedule_type="single",
            test_definition_id=5
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [5]

    @pytest.mark.asyncio
    async def test_resolve_suite_schedule(self):
        """Test resolving suite schedule."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Suite Schedule",
            schedule_type="suite",
            test_suite_id=10
        )

        # Mock database response
        mock_suite = TestSuite(
            id=10,
            name="Test Suite",
            test_definition_ids=[1, 2, 3]
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        # Setup mock to return suite
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = mock_suite
        db.execute.return_value = result_mock

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_suite_schedule_not_found(self):
        """Test resolving suite schedule when suite doesn't exist."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Suite Schedule",
            schedule_type="suite",
            test_suite_id=999
        )

        # Mock database response - suite not found
        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test suite 999 not found"):
            await resolver.resolve_schedule(schedule, db)

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_schedule(self):
        """Test resolving tag filter schedule."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Tag Filter Schedule",
            schedule_type="tag_filter",
            tag_filter="smoke"
        )

        # Mock database response
        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        # Setup mock to return test IDs
        result_mock = Mock()
        result_mock.fetchall.return_value = [(1,), (2,), (3,)]
        db.execute.return_value = result_mock

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_schedule_no_tags(self):
        """Test resolving tag filter schedule with no tag_filter set."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Tag Filter Schedule",
            schedule_type="tag_filter",
            tag_filter=None
        )

        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_unknown_schedule_type(self):
        """Test resolving unknown schedule type raises error."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Unknown Schedule",
            schedule_type="unknown_type"
        )

        db = Mock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Unknown schedule_type"):
            await resolver.resolve_schedule(schedule, db)

    @pytest.mark.asyncio
    async def test_resolve_single_returns_single_item_list(self):
        """Test that single schedule returns a list with one item."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Single Test",
            schedule_type="single",
            test_definition_id=42
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == 42
