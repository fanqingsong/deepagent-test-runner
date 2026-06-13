"""
Unit tests for ScheduleResolverFactory.
"""

import pytest
from unittest.mock import Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory
from app.services.strategies.single_test_resolver import SingleTestResolver
from app.services.strategies.suite_resolver import SuiteResolver
from app.services.strategies.tag_filter_resolver import TagFilterResolver
from app.services.strategies.schedule_resolver_strategy import ScheduleResolverStrategy
from app.models.schedule import Schedule


class CustomTestResolver(ScheduleResolverStrategy):
    """Custom resolver for testing factory registration."""

    async def resolve(self, schedule: Schedule, db: AsyncSession):
        return [99]

    def get_strategy_name(self):
        return "CustomTestResolver"

    def get_supported_schedule_types(self):
        return ['custom']


class TestScheduleResolverFactory:
    """Test suite for ScheduleResolverFactory."""

    def setup_method(self):
        """Reset factory before each test."""
        ScheduleResolverFactory.reset()

    def test_factory_initializes_default_strategies(self):
        """Test factory initializes with default strategies."""
        strategies = ScheduleResolverFactory.list_strategies()

        assert 'single' in strategies
        assert 'suite' in strategies
        assert 'tag_filter' in strategies
        assert len(strategies) == 3

    def test_get_strategy_for_single(self):
        """Test getting strategy for 'single' schedule type."""
        strategy = ScheduleResolverFactory.get_strategy('single')

        assert isinstance(strategy, SingleTestResolver)
        assert strategy.get_strategy_name() == "SingleTestResolver"

    def test_get_strategy_for_suite(self):
        """Test getting strategy for 'suite' schedule type."""
        strategy = ScheduleResolverFactory.get_strategy('suite')

        assert isinstance(strategy, SuiteResolver)
        assert strategy.get_strategy_name() == "SuiteResolver"

    def test_get_strategy_for_tag_filter(self):
        """Test getting strategy for 'tag_filter' schedule type."""
        strategy = ScheduleResolverFactory.get_strategy('tag_filter')

        assert isinstance(strategy, TagFilterResolver)
        assert strategy.get_strategy_name() == "TagFilterResolver"

    def test_get_strategy_for_unknown_type_raises_error(self):
        """Test getting strategy for unknown schedule type raises error."""
        with pytest.raises(ValueError, match="Unknown schedule_type: 'unknown'"):
            ScheduleResolverFactory.get_strategy('unknown')

    def test_register_custom_strategy(self):
        """Test registering a custom strategy."""
        custom_resolver = CustomTestResolver()
        ScheduleResolverFactory.register_strategy('custom', custom_resolver)

        strategy = ScheduleResolverFactory.get_strategy('custom')

        assert strategy is custom_resolver
        assert strategy.get_strategy_name() == "CustomTestResolver"

    def test_register_strategy_with_invalid_type_raises_error(self):
        """Test registering non-strategy raises TypeError."""
        with pytest.raises(TypeError, match="must be instance of ScheduleResolverStrategy"):
            ScheduleResolverFactory.register_strategy('invalid', "not a strategy")

    def test_register_strategy_overwrites_existing(self):
        """Test registering strategy overwrites existing one."""
        # Initialize factory first
        _ = ScheduleResolverFactory.list_strategies()

        custom_resolver = CustomTestResolver()
        ScheduleResolverFactory.register_strategy('single', custom_resolver)

        strategy = ScheduleResolverFactory.get_strategy('single')

        assert isinstance(strategy, CustomTestResolver)
        assert strategy.get_strategy_name() == "CustomTestResolver"

    def test_is_strategy_registered(self):
        """Test checking if strategy is registered."""
        assert ScheduleResolverFactory.is_strategy_registered('single') is True
        assert ScheduleResolverFactory.is_strategy_registered('suite') is True
        assert ScheduleResolverFactory.is_strategy_registered('unknown') is False

    def test_list_strategies(self):
        """Test listing all registered strategies."""
        strategies = ScheduleResolverFactory.list_strategies()

        assert isinstance(strategies, dict)
        assert len(strategies) >= 3
        assert 'single' in strategies
        assert 'suite' in strategies
        assert 'tag_filter' in strategies

    def test_unregister_strategy(self):
        """Test unregistering a strategy."""
        ScheduleResolverFactory.register_strategy('temp', CustomTestResolver())

        assert ScheduleResolverFactory.is_strategy_registered('temp') is True

        result = ScheduleResolverFactory.unregister_strategy('temp')

        assert result is True
        assert ScheduleResolverFactory.is_strategy_registered('temp') is False

    def test_unregister_nonexistent_strategy(self):
        """Test unregistering non-existent strategy returns False."""
        result = ScheduleResolverFactory.unregister_strategy('nonexistent')
        assert result is False

    def test_reset_clears_all_strategies(self):
        """Test resetting factory clears all strategies."""
        # Initialize factory
        _ = ScheduleResolverFactory.list_strategies()
        ScheduleResolverFactory.register_strategy('custom', CustomTestResolver())

        assert len(ScheduleResolverFactory._strategies) > 3

        ScheduleResolverFactory.reset()

        # After reset, should be empty (check internal state to avoid reinitialization)
        assert len(ScheduleResolverFactory._strategies) == 0
        assert ScheduleResolverFactory._initialized is False

    def test_get_strategy_for_schedule(self):
        """Test getting strategy from schedule object."""
        schedule = Schedule(
            name="Test",
            schedule_type="single",
            test_definition_id=5
        )

        strategy = ScheduleResolverFactory.get_strategy_for_schedule(schedule)

        assert isinstance(strategy, SingleTestResolver)

    def test_factory_reinitializes_after_reset(self):
        """Test factory reinitializes default strategies after reset."""
        # Initialize factory first
        _ = ScheduleResolverFactory.list_strategies()
        ScheduleResolverFactory.reset()

        # After reset, factory should be empty (check internal state)
        assert len(ScheduleResolverFactory._strategies) == 0
        assert ScheduleResolverFactory._initialized is False

        # Getting a strategy should trigger reinitialization
        strategy = ScheduleResolverFactory.get_strategy('single')

        assert isinstance(strategy, SingleTestResolver)
        assert ScheduleResolverFactory._initialized is True
        assert len(ScheduleResolverFactory._strategies) == 3

    def test_multiple_custom_strategies(self):
        """Test registering multiple custom strategies."""
        ScheduleResolverFactory.register_strategy('custom1', CustomTestResolver())
        ScheduleResolverFactory.register_strategy('custom2', CustomTestResolver())

        assert ScheduleResolverFactory.is_strategy_registered('custom1') is True
        assert ScheduleResolverFactory.is_strategy_registered('custom2') is True
        assert len(ScheduleResolverFactory.list_strategies()) >= 5
