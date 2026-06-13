"""
Unit tests for SingleTestResolver strategy.
"""

import pytest
from unittest.mock import Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.strategies.single_test_resolver import SingleTestResolver
from app.models.schedule import Schedule


class TestSingleTestResolver:
    """Test suite for SingleTestResolver strategy."""

    @pytest.fixture
    def resolver(self):
        """Create resolver instance."""
        return SingleTestResolver()

    @pytest.mark.asyncio
    async def test_resolve_single_test(self, resolver):
        """Test resolving single test schedule."""
        schedule = Schedule(
            name="Single Test",
            schedule_type="single",
            test_definition_id=5
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve(schedule, db)

        assert result == [5]
        assert len(result) == 1
        assert result[0] == 5

    @pytest.mark.asyncio
    async def test_resolve_single_test_different_id(self, resolver):
        """Test resolving single test with different ID."""
        schedule = Schedule(
            name="Another Test",
            schedule_type="single",
            test_definition_id=42
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve(schedule, db)

        assert result == [42]

    @pytest.mark.asyncio
    async def test_resolve_single_test_with_zero_id(self, resolver):
        """Test resolving single test with ID 0 (edge case)."""
        schedule = Schedule(
            name="Zero ID Test",
            schedule_type="single",
            test_definition_id=0
        )
        db = Mock(spec=AsyncSession)

        result = await resolver.resolve(schedule, db)

        assert result == [0]

    def test_get_strategy_name(self, resolver):
        """Test get_strategy_name returns correct name."""
        name = resolver.get_strategy_name()
        assert name == "SingleTestResolver"

    def test_get_supported_schedule_types(self, resolver):
        """Test get_supported_schedule_types returns correct types."""
        types = resolver.get_supported_schedule_types()
        assert types == ['single']

    def test_validate_schedule_with_valid_id(self, resolver):
        """Test validation passes with valid ID."""
        schedule = Schedule(
            name="Valid Test",
            schedule_type="single",
            test_definition_id=10
        )

        # Should not raise
        resolver.validate_schedule(schedule)

    def test_validate_schedule_with_missing_id(self, resolver):
        """Test validation fails with missing ID."""
        schedule = Schedule(
            name="Invalid Test",
            schedule_type="single",
            test_definition_id=None
        )

        with pytest.raises(ValueError, match="must have test_definition_id set"):
            resolver.validate_schedule(schedule)

    def test_get_strategy_description(self, resolver):
        """Test get_strategy_description returns informative description."""
        description = resolver.get_strategy_description()
        assert "SingleTestResolver" in description
        assert "single" in description
