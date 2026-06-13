"""
Unit tests for TagFilterResolver strategy.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.strategies.tag_filter_resolver import TagFilterResolver
from app.models.schedule import Schedule


class TestTagFilterResolver:
    """Test suite for TagFilterResolver strategy."""

    @pytest.fixture
    def resolver(self):
        """Create resolver instance."""
        return TagFilterResolver()

    @pytest.mark.asyncio
    async def test_resolve_tag_filter(self, resolver):
        """Test resolving tag filter schedule."""
        schedule = Schedule(
            name="Tag Filter Schedule",
            schedule_type="tag_filter",
            tag_filter="smoke"
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.fetchall.return_value = [(1,), (2,), (3,)]
        db.execute.return_value = result_mock

        result = await resolver.resolve(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_with_many_matches(self, resolver):
        """Test resolving tag filter with many matches."""
        schedule = Schedule(
            name="Large Tag Filter",
            schedule_type="tag_filter",
            tag_filter="integration"
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        # Return 50 matching tests
        result_mock = Mock()
        result_mock.fetchall.return_value = [(i,) for i in range(1, 51)]
        db.execute.return_value = result_mock

        result = await resolver.resolve(schedule, db)

        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_no_matches(self, resolver):
        """Test resolving tag filter with no matches."""
        schedule = Schedule(
            name="No Match Filter",
            schedule_type="tag_filter",
            tag_filter="nonexistent"
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.fetchall.return_value = []
        db.execute.return_value = result_mock

        result = await resolver.resolve(schedule, db)

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_no_tag_set(self, resolver):
        """Test resolving tag filter schedule with no tag_filter set."""
        schedule = Schedule(
            name="Empty Tag Filter",
            schedule_type="tag_filter",
            tag_filter=None
        )

        db = Mock(spec=AsyncSession)

        result = await resolver.resolve(schedule, db)

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_empty_string(self, resolver):
        """Test resolving tag filter with empty string."""
        schedule = Schedule(
            name="Empty String Filter",
            schedule_type="tag_filter",
            tag_filter=""
        )

        db = Mock(spec=AsyncSession)

        # Empty string is falsy, should return empty list
        result = await resolver.resolve(schedule, db)

        assert result == []

    def test_get_strategy_name(self, resolver):
        """Test get_strategy_name returns correct name."""
        name = resolver.get_strategy_name()
        assert name == "TagFilterResolver"

    def test_get_supported_schedule_types(self, resolver):
        """Test get_supported_schedule_types returns correct types."""
        types = resolver.get_supported_schedule_types()
        assert types == ['tag_filter']

    def test_validate_schedule_with_valid_tag(self, resolver):
        """Test validation passes with valid tag."""
        schedule = Schedule(
            name="Valid Tag Filter",
            schedule_type="tag_filter",
            tag_filter="smoke"
        )

        # Should not raise
        resolver.validate_schedule(schedule)

    def test_validate_schedule_with_missing_tag(self, resolver):
        """Test validation allows None (handled in resolve)."""
        schedule = Schedule(
            name="Tag Filter",
            schedule_type="tag_filter",
            tag_filter=None
        )

        # Should not raise - None is allowed, handled in resolve()
        resolver.validate_schedule(schedule)

    def test_get_strategy_description(self, resolver):
        """Test get_strategy_description returns informative description."""
        description = resolver.get_strategy_description()
        assert "TagFilterResolver" in description
        assert "tag_filter" in description
