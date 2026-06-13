"""
Unit tests for refactored ScheduleResolver using Strategy Pattern.
Tests backward compatibility and new functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schedule_resolver import ScheduleResolver
from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy
from app.models.schedule import Schedule


class MockTestResolver(ScheduleResolverStrategy):
    """Mock resolver for testing."""

    async def resolve(self, schedule, db):
        return [999]

    def get_strategy_name(self):
        return "MockTestResolver"

    def get_supported_schedule_types(self):
        return ['mock_type']


class TestScheduleResolverRefactored:
    """Test suite for refactored ScheduleResolver."""

    def setup_method(self):
        """Reset factory before each test."""
        ScheduleResolverFactory.reset()

    @pytest.mark.asyncio
    async def test_resolve_single_schedule(self):
        """Test resolving single test schedule (backward compatibility)."""
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
        """Test resolving suite schedule (backward compatibility)."""
        from app.models.test_suite import TestSuite

        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Suite Schedule",
            schedule_type="suite",
            test_suite_id=10
        )

        mock_suite = TestSuite(
            id=10,
            name="Test Suite",
            test_definition_ids=[1, 2, 3]
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = mock_suite
        db.execute.return_value = result_mock

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_schedule(self):
        """Test resolving tag filter schedule (backward compatibility)."""
        resolver = ScheduleResolver()
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

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_unknown_schedule_type(self):
        """Test resolving unknown schedule type raises error (backward compatibility)."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Unknown Schedule",
            schedule_type="unknown_type"
        )

        db = Mock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Unknown schedule_type"):
            await resolver.resolve_schedule(schedule, db)

    @pytest.mark.asyncio
    async def test_resolver_with_custom_strategy(self):
        """Test resolver works with custom registered strategy."""
        # Register custom strategy
        ScheduleResolverFactory.register_strategy('mock_type', MockTestResolver())

        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Mock Schedule",
            schedule_type="mock_type"
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        assert result == [999]

    def test_resolver_initialization(self):
        """Test resolver initialization."""
        resolver = ScheduleResolver()

        assert resolver._factory == ScheduleResolverFactory

    def test_resolver_with_custom_factory(self):
        """Test resolver with injected factory (dependency injection)."""
        mock_factory = Mock()
        resolver = ScheduleResolver(factory=mock_factory)

        assert resolver._factory is mock_factory

    @pytest.mark.asyncio
    async def test_resolver_uses_factory_to_get_strategy(self):
        """Test resolver uses factory to get appropriate strategy."""
        mock_factory = Mock()
        mock_strategy = MockTestResolver()
        mock_factory.get_strategy_for_schedule.return_value = mock_strategy

        resolver = ScheduleResolver(factory=mock_factory)
        schedule = Schedule(
            name="Test",
            schedule_type="mock_type"
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        mock_factory.get_strategy_for_schedule.assert_called_once_with(schedule)
        assert result == [999]

    @pytest.mark.asyncio
    async def test_resolve_tag_filter_schedule_no_tags(self):
        """Test resolving tag filter schedule with no tag_filter set (backward compatibility)."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Empty Tag Filter",
            schedule_type="tag_filter",
            tag_filter=None
        )

        db = Mock(spec=AsyncSession)

        result = await resolver.resolve_schedule(schedule, db)

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_suite_schedule_not_found(self):
        """Test resolving suite schedule when suite doesn't exist (backward compatibility)."""
        resolver = ScheduleResolver()
        schedule = Schedule(
            name="Suite Schedule",
            schedule_type="suite",
            test_suite_id=999
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test suite 999 not found"):
            await resolver.resolve_schedule(schedule, db)

    @pytest.mark.asyncio
    async def test_resolve_single_returns_single_item_list(self):
        """Test that single schedule returns a list with one item (backward compatibility)."""
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

    @pytest.mark.asyncio
    async def test_all_strategies_work_through_resolver(self):
        """Test that all default strategies work through the refactored resolver."""
        from app.models.test_suite import TestSuite

        # Test single
        resolver = ScheduleResolver()
        single_schedule = Schedule(
            name="Single",
            schedule_type="single",
            test_definition_id=1
        )
        db = Mock(spec=AsyncSession)
        result = await resolver.resolve_schedule(single_schedule, db)
        assert result == [1]

        # Test suite
        suite_schedule = Schedule(
            name="Suite",
            schedule_type="suite",
            test_suite_id=10
        )
        mock_suite = TestSuite(id=10, name="Suite", test_definition_ids=[1, 2])

        db2 = Mock(spec=AsyncSession)
        db2.execute = AsyncMock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = mock_suite
        db2.execute.return_value = result_mock

        result = await resolver.resolve_schedule(suite_schedule, db2)
        assert result == [1, 2]

        # Test tag filter
        tag_schedule = Schedule(
            name="Tags",
            schedule_type="tag_filter",
            tag_filter="test"
        )
        db3 = Mock(spec=AsyncSession)
        db3.execute = AsyncMock()
        result_mock3 = Mock()
        result_mock3.fetchall.return_value = [(1,), (2,)]
        db3.execute.return_value = result_mock3

        result = await resolver.resolve_schedule(tag_schedule, db3)
        assert result == [1, 2]
