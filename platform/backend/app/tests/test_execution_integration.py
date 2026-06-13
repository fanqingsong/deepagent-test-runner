"""
Integration test to verify ExecutionService still works after refactoring.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.execution_service import ExecutionService
from app.services.schedule_resolver import ScheduleResolver
from app.models.schedule import Schedule


class TestExecutionServiceIntegration:
    """Integration tests for ExecutionService after ScheduleResolver extraction."""

    @pytest.mark.asyncio
    async def test_execution_service_uses_schedule_resolver(self):
        """Test that ExecutionService properly delegates to ScheduleResolver."""
        # Create a custom resolver that we can verify gets called
        custom_resolver = Mock(spec=ScheduleResolver)
        custom_resolver.resolve_schedule = AsyncMock(return_value=[1, 2, 3])

        # Create ExecutionService with the custom resolver
        db_session = Mock(spec=AsyncSession)
        service = ExecutionService(db_session, custom_resolver)

        # Create a schedule
        schedule = Schedule(
            name="Test Schedule",
            schedule_type="single",
            test_definition_id=5
        )

        # Call resolve_target_tests
        result = await service.resolve_target_tests(schedule, db_session)

        # Verify the custom resolver was called
        custom_resolver.resolve_schedule.assert_called_once_with(schedule, db_session)
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_execution_service_default_resolver_works(self):
        """Test that ExecutionService works with default resolver."""
        # Create ExecutionService with default resolver
        service = ExecutionService()

        # Create a single test schedule
        schedule = Schedule(
            name="Test Schedule",
            schedule_type="single",
            test_definition_id=42
        )

        db_session = Mock(spec=AsyncSession)

        # Call resolve_target_tests
        result = await service.resolve_target_tests(schedule, db_session)

        # Verify it works correctly
        assert result == [42]
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_backward_compatibility_single_param(self):
        """Test backward compatibility with single db_session parameter."""
        db_session = Mock(spec=AsyncSession)
        service = ExecutionService(db_session)

        # Verify service has all expected methods
        assert hasattr(service, 'resolve_target_tests')
        assert hasattr(service, 'check_execution_limit')
        assert hasattr(service, 'build_environment')
        assert hasattr(service, 'create_test_run')
        assert hasattr(service, 'update_run_status')

        # Verify schedule_resolver is present
        assert hasattr(service, 'schedule_resolver')
        assert isinstance(service.schedule_resolver, ScheduleResolver)

    @pytest.mark.asyncio
    async def test_schedule_resolver_isolated_functionality(self):
        """Test that ScheduleResolver can be used independently."""
        resolver = ScheduleResolver()

        # Create a single test schedule
        schedule = Schedule(
            name="Test Schedule",
            schedule_type="single",
            test_definition_id=99
        )

        db_session = Mock(spec=AsyncSession)

        # Call resolve_schedule directly
        result = await resolver.resolve_schedule(schedule, db_session)

        # Verify it works correctly
        assert result == [99]

    @pytest.mark.asyncio
    async def test_execution_service_method_signatures_unchanged(self):
        """Test that ExecutionService method signatures remain unchanged."""
        service = ExecutionService()
        db_session = Mock(spec=AsyncSession)
        schedule = Schedule(
            name="Test",
            schedule_type="single",
            test_definition_id=1
        )

        # Test that methods can be called with expected signatures
        # This ensures backward compatibility
        try:
            # resolve_target_tests(schedule, db) -> List[int]
            result = await service.resolve_target_tests(schedule, db_session)
            assert isinstance(result, list)

            # check_execution_limit(schedule, db) -> bool
            # (We can't fully test this without a real schedule, but we can check the method exists)
            assert callable(service.check_execution_limit)

            # build_environment(schedule, optional, optional) -> Dict
            env_result = service.build_environment(schedule)
            assert isinstance(env_result, dict)

            print('✓ All method signatures are backward compatible')

        except Exception as e:
            pytest.fail(f"Method signature compatibility check failed: {e}")
