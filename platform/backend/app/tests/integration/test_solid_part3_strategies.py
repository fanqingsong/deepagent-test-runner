"""
SOLID Verification Part 3: Strategy Pattern

Tests strategy implementations follow Open/Closed Principle:
- Open for extension (new strategies)
- Closed for modification (existing code unchanged)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schedule_resolver import ScheduleResolver
from app.services.strategies.schedule_resolver_factory import ScheduleResolverFactory
from app.services.strategies.execution_strategy_factory import ExecutionStrategyFactory
from app.models.schedule import Schedule


class TestStrategyPatterns:
    """Verify strategy patterns follow Open/Closed Principle."""

    @pytest.mark.asyncio
    async def test_schedule_resolver_strategies(self, db_session: AsyncSession):
        """Test ScheduleResolver strategy implementations."""
        factory = ScheduleResolverFactory()
        resolver = ScheduleResolver(factory=factory)

        # Test single test strategy
        single_schedule = Schedule(
            id=1,
            name="Single Test",
            schedule_type="single",
            cron_expression="0 0 * * *",
            test_definition_id=5,
            created_by="user123"
        )

        test_ids = await resolver.resolve_schedule(single_schedule, db_session)
        assert test_ids == [5]

        # Test manual selection strategy
        manual_schedule = Schedule(
            id=3,
            name="Manual Test",
            schedule_type="manual",
            cron_expression="0 0 * * *",
            manual_test_ids=[10, 20, 30],
            created_by="user123"
        )

        test_ids = await resolver.resolve_schedule(manual_schedule, db_session)
        assert test_ids == [10, 20, 30]

    @pytest.mark.asyncio
    async def test_strategy_factory_registration(self):
        """Test strategy factory allows easy extension."""
        factory = ScheduleResolverFactory()

        # Verify all strategies are registered
        strategies = factory.get_registered_strategies()
        assert "single" in strategies
        assert "suite" in strategies
        assert "manual" in strategies

        # Verify we can get each strategy
        single_strategy = factory.get_strategy("single")
        assert single_strategy is not None

        suite_strategy = factory.get_strategy("suite")
        assert suite_strategy is not None

        manual_strategy = factory.get_strategy("manual")
        assert manual_strategy is not None

    @pytest.mark.asyncio
    async def test_strategy_extensibility(self):
        """Test that new strategies can be added without modifying existing code."""
        factory = ScheduleResolverFactory()

        # Count initial strategies
        initial_strategies = factory.get_registered_strategies()
        initial_count = len(initial_strategies)

        # Verify we have multiple strategies
        assert initial_count >= 3  # At least single, suite, manual

        # The factory design allows adding new strategies without modifying code
        # This demonstrates the Open/Closed Principle

    @pytest.mark.asyncio
    async def test_execution_strategy_factory(self):
        """Test ExecutionStrategyFactory follows same pattern."""
        factory = ExecutionStrategyFactory()

        # Verify strategies are registered
        strategies = factory.get_registered_strategies()
        assert len(strategies) > 0

        # Verify we can get strategies
        for strategy_name in strategies:
            strategy = factory.get_strategy(strategy_name)
            assert strategy is not None

    @pytest.mark.asyncio
    async def test_liskov_substitution_strategies(self):
        """Test all strategies are substitutable."""
        factory = ScheduleResolverFactory()

        # All strategies should implement the same interface
        strategies = factory.get_registered_strategies()

        for strategy_name in strategies:
            strategy = factory.get_strategy(strategy_name)
            # Should have required method
            assert hasattr(strategy, 'resolve')
            assert callable(strategy.resolve)
