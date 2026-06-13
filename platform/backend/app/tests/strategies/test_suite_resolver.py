"""
Unit tests for SuiteResolver strategy.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.strategies.suite_resolver import SuiteResolver
from app.models.schedule import Schedule
from app.models.test_suite import TestSuite


class TestSuiteResolver:
    """Test suite for SuiteResolver strategy."""

    @pytest.fixture
    def resolver(self):
        """Create resolver instance."""
        return SuiteResolver()

    @pytest.mark.asyncio
    async def test_resolve_suite(self, resolver):
        """Test resolving suite schedule."""
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

        result = await resolver.resolve(schedule, db)

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_resolve_suite_with_many_tests(self, resolver):
        """Test resolving suite with many test definitions."""
        schedule = Schedule(
            name="Large Suite",
            schedule_type="suite",
            test_suite_id=20
        )

        mock_suite = TestSuite(
            id=20,
            name="Large Suite",
            test_definition_ids=list(range(1, 101))  # 100 tests
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = mock_suite
        db.execute.return_value = result_mock

        result = await resolver.resolve(schedule, db)

        assert len(result) == 100
        assert result == list(range(1, 101))

    @pytest.mark.asyncio
    async def test_resolve_suite_with_empty_suite(self, resolver):
        """Test resolving suite with no test definitions."""
        schedule = Schedule(
            name="Empty Suite",
            schedule_type="suite",
            test_suite_id=30
        )

        mock_suite = TestSuite(
            id=30,
            name="Empty Suite",
            test_definition_ids=[]
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = mock_suite
        db.execute.return_value = result_mock

        result = await resolver.resolve(schedule, db)

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_suite_not_found(self, resolver):
        """Test resolving suite schedule when suite doesn't exist."""
        schedule = Schedule(
            name="Missing Suite",
            schedule_type="suite",
            test_suite_id=999
        )

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test suite 999 not found"):
            await resolver.resolve(schedule, db)

    def test_get_strategy_name(self, resolver):
        """Test get_strategy_name returns correct name."""
        name = resolver.get_strategy_name()
        assert name == "SuiteResolver"

    def test_get_supported_schedule_types(self, resolver):
        """Test get_supported_schedule_types returns correct types."""
        types = resolver.get_supported_schedule_types()
        assert types == ['suite']

    def test_validate_schedule_with_valid_suite_id(self, resolver):
        """Test validation passes with valid suite ID."""
        schedule = Schedule(
            name="Valid Suite",
            schedule_type="suite",
            test_suite_id=5
        )

        # Should not raise
        resolver.validate_schedule(schedule)

    def test_validate_schedule_with_missing_suite_id(self, resolver):
        """Test validation fails with missing suite ID."""
        schedule = Schedule(
            name="Invalid Suite",
            schedule_type="suite",
            test_suite_id=None
        )

        with pytest.raises(ValueError, match="must have test_suite_id set"):
            resolver.validate_schedule(schedule)
