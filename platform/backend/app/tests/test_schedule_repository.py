"""
Schedule Repository Tests

Comprehensive tests for Schedule repository implementation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

from app.repositories.schedule_repository import SQLAlchemyScheduleRepository
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository
from app.models.schedule import Schedule


class TestScheduleRepositoryInterface:
    """Test the repository interface contract."""

    def test_interface_exists(self):
        """Test that IScheduleRepository interface exists."""
        assert IScheduleRepository is not None

    def test_interface_has_required_methods(self):
        """Test that interface has all required methods."""
        required_methods = [
            'create', 'get_by_id', 'get_all', 'get_active_schedules',
            'get_by_test_definition_id', 'get_by_suite_id', 'update',
            'update_next_run_time', 'activate', 'deactivate', 'delete',
            'get_by_type', 'get_due_schedules', 'count', 'count_by_status',
            'update_last_run_time', 'exists'
        ]
        for method in required_methods:
            assert hasattr(IScheduleRepository, method)


class TestSQLAlchemyScheduleRepository:
    """Test SQLAlchemy implementation of Schedule repository."""

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return SQLAlchemyScheduleRepository()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.delete = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def sample_schedule_data(self):
        """Create sample schedule data."""
        return {
            'name': 'Test Schedule',
            'schedule_type': 'single',
            'test_definition_ids': [1, 2, 3],
            'test_definition_id': 1,
            'cron_expression': '0 0 * * *',
            'timezone': 'UTC',
            'environment_overrides': {'KEY': 'value'},
            'is_active': True,
            'allow_concurrent': False,
            'max_retries': 3,
            'retry_interval_seconds': 60,
            'created_by': 1
        }

    @pytest.mark.asyncio
    async def test_create_schedule_success(self, repository, mock_db_session, sample_schedule_data):
        """Test successful schedule creation."""
        # Execute
        result = await repository.create(sample_schedule_data, mock_db_session)

        # Verify
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_schedule_missing_cron(self, repository, mock_db_session, sample_schedule_data):
        """Test schedule creation fails without cron expression."""
        # Setup
        sample_schedule_data.pop('cron_expression')

        # Execute & Verify
        with pytest.raises(ValueError, match="cron_expression is required"):
            await repository.create(sample_schedule_data, mock_db_session)

    @pytest.mark.asyncio
    async def test_create_schedule_missing_type(self, repository, mock_db_session, sample_schedule_data):
        """Test schedule creation fails without schedule type."""
        # Setup
        sample_schedule_data.pop('schedule_type')

        # Execute & Verify
        with pytest.raises(ValueError, match="schedule_type is required"):
            await repository.create(sample_schedule_data, mock_db_session)

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_db_session):
        """Test successful schedule retrieval by ID."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *')

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = schedule
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(1, mock_db_session)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.name == 'Test'

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db_session):
        """Test schedule retrieval when not found."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(999, mock_db_session)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_schedules(self, repository, mock_db_session):
        """Test retrieving all schedules."""
        # Setup
        schedules = [
            Schedule(id=1, name='Schedule 1', schedule_type='single',
                     test_definition_ids=[1], cron_expression='0 0 * * *'),
            Schedule(id=2, name='Schedule 2', schedule_type='suite',
                     test_definition_ids=[2], cron_expression='0 1 * * *')
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(mock_db_session, limit=10, offset=0)

        # Verify
        assert len(result) == 2
        assert result[0].name == 'Schedule 1'
        assert result[1].name == 'Schedule 2'

    @pytest.mark.asyncio
    async def test_get_active_schedules(self, repository, mock_db_session):
        """Test retrieving active schedules."""
        # Setup
        schedules = [
            Schedule(id=1, name='Active 1', schedule_type='single',
                     test_definition_ids=[1], cron_expression='0 0 * * *',
                     is_active=True, next_run_time=datetime.utcnow())
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_active_schedules(mock_db_session)

        # Verify
        assert len(result) == 1
        assert result[0].is_active is True

    @pytest.mark.asyncio
    async def test_get_by_test_definition_id(self, repository, mock_db_session):
        """Test retrieving schedules by test definition ID."""
        # Setup
        schedules = [
            Schedule(id=1, name='Schedule 1', schedule_type='single',
                     test_definition_ids=[1], cron_expression='0 0 * * *',
                     test_definition_id=1)
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_test_definition_id(1, mock_db_session)

        # Verify
        assert len(result) == 1
        assert result[0].test_definition_id == 1

    @pytest.mark.asyncio
    async def test_get_by_suite_id(self, repository, mock_db_session):
        """Test retrieving schedules by test suite ID."""
        # Setup
        schedules = [
            Schedule(id=1, name='Suite Schedule', schedule_type='suite',
                     test_definition_ids=[1], test_suite_id=10,
                     cron_expression='0 0 * * *')
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_suite_id(10, mock_db_session)

        # Verify
        assert len(result) == 1
        assert result[0].test_suite_id == 10

    @pytest.mark.asyncio
    async def test_update_schedule(self, repository, mock_db_session, sample_schedule_data):
        """Test updating a schedule."""
        # Setup - First create a schedule
        schedule = Schedule(**sample_schedule_data)
        schedule.id = 1

        # Mock get_by_id to return our schedule
        repository.get_by_id = AsyncMock(return_value=schedule)

        # Execute
        updates = {'name': 'Updated Name', 'is_active': False}
        result = await repository.update(1, updates, mock_db_session)

        # Verify
        assert result.name == 'Updated Name'
        assert result.is_active is False
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, repository, mock_db_session):
        """Test updating a schedule that doesn't exist."""
        # Setup
        repository.get_by_id = AsyncMock(return_value=None)

        # Execute & Verify
        with pytest.raises(ValueError, match="Schedule 1 not found"):
            await repository.update(1, {'name': 'New Name'}, mock_db_session)

    @pytest.mark.asyncio
    async def test_update_next_run_time(self, repository, mock_db_session):
        """Test updating next run time."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *')
        repository.get_by_id = AsyncMock(return_value=schedule)

        next_time = datetime.utcnow() + timedelta(hours=1)

        # Execute
        result = await repository.update_next_run_time(1, next_time, mock_db_session)

        # Verify
        assert result.next_run_time == next_time
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_schedule(self, repository, mock_db_session):
        """Test activating a schedule."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *',
                           is_active=False)
        repository.get_by_id = AsyncMock(return_value=schedule)

        # Execute
        result = await repository.activate(1, mock_db_session)

        # Verify
        assert result.is_active is True
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_schedule(self, repository, mock_db_session):
        """Test deactivating a schedule."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *',
                           is_active=True)
        repository.get_by_id = AsyncMock(return_value=schedule)

        # Execute
        result = await repository.deactivate(1, mock_db_session)

        # Verify
        assert result.is_active is False
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schedule(self, repository, mock_db_session):
        """Test deleting a schedule."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *')
        repository.get_by_id = AsyncMock(return_value=schedule)

        # Execute
        result = await repository.delete(1, mock_db_session)

        # Verify
        assert result is True
        mock_db_session.delete.assert_called_once_with(schedule)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self, repository, mock_db_session):
        """Test deleting a schedule that doesn't exist."""
        # Setup
        repository.get_by_id = AsyncMock(return_value=None)

        # Execute
        result = await repository.delete(999, mock_db_session)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_type(self, repository, mock_db_session):
        """Test retrieving schedules by type."""
        # Setup
        schedules = [
            Schedule(id=1, name='Single 1', schedule_type='single',
                     test_definition_ids=[1], cron_expression='0 0 * * *'),
            Schedule(id=2, name='Single 2', schedule_type='single',
                     test_definition_ids=[2], cron_expression='0 1 * * *')
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_type('single', mock_db_session)

        # Verify
        assert len(result) == 2
        assert all(s.schedule_type == 'single' for s in result)

    @pytest.mark.asyncio
    async def test_get_due_schedules(self, repository, mock_db_session):
        """Test retrieving due schedules."""
        # Setup
        now = datetime.utcnow()
        schedules = [
            Schedule(id=1, name='Due 1', schedule_type='single',
                     test_definition_ids=[1], cron_expression='0 0 * * *',
                     is_active=True, next_run_time=now - timedelta(minutes=5)),
            Schedule(id=2, name='Due 2', schedule_type='suite',
                     test_definition_ids=[2], cron_expression='0 1 * * *',
                     is_active=True, next_run_time=now - timedelta(minutes=10))
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_due_schedules(now, mock_db_session)

        # Verify
        assert len(result) == 2
        assert all(s.is_active and s.next_run_time <= now for s in result)

    @pytest.mark.asyncio
    async def test_count_schedules(self, repository, mock_db_session):
        """Test counting all schedules."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.count(mock_db_session)

        # Verify
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_status(self, repository, mock_db_session):
        """Test counting schedules by status."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 3
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.count_by_status(True, mock_db_session)

        # Verify
        assert result == 3

    @pytest.mark.asyncio
    async def test_update_last_run_time(self, repository, mock_db_session):
        """Test updating last run time."""
        # Setup
        schedule = Schedule(id=1, name='Test', schedule_type='single',
                           test_definition_ids=[1], cron_expression='0 0 * * *')
        repository.get_by_id = AsyncMock(return_value=schedule)

        last_run = datetime.utcnow() - timedelta(minutes=30)

        # Execute
        result = await repository.update_last_run_time(1, last_run, mock_db_session)

        # Verify
        assert result.last_run_time == last_run
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_schedule(self, repository, mock_db_session):
        """Test checking if schedule exists."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.exists(1, mock_db_session)

        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_schedule_not_found(self, repository, mock_db_session):
        """Test checking if schedule exists when it doesn't."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await repository.exists(999, mock_db_session)

        # Verify
        assert result is False


class TestScheduleRepositoryIntegration:
    """Integration tests with real database (requires test database)."""

    @pytest.mark.integration
    @pytest.fixture
    async def db_session(self):
        """Create real database session for integration tests."""
        from app.core.database import get_async_session
        async for session in get_async_session():
            yield session
            # No need to close - get_async_session handles it

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return SQLAlchemyScheduleRepository()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_retrieve_schedule(self, repository, db_session):
        """Test creating and retrieving a schedule."""
        # Create schedule
        schedule_data = {
            'name': 'Integration Test Schedule',
            'schedule_type': 'single',
            'test_definition_ids': [1],
            'test_definition_id': 1,
            'cron_expression': '0 0 * * *',
            'timezone': 'UTC',
            'is_active': True
        }

        created = await repository.create(schedule_data, db_session)
        assert created.id is not None

        # Retrieve schedule
        retrieved = await repository.get_by_id(created.id, db_session)
        assert retrieved is not None
        assert retrieved.name == 'Integration Test Schedule'
        assert retrieved.schedule_type == 'single'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_activate_deactivate_schedule(self, repository, db_session):
        """Test activating and deactivating a schedule."""
        # Create schedule
        schedule_data = {
            'name': 'Toggle Test Schedule',
            'schedule_type': 'single',
            'test_definition_ids': [1],
            'cron_expression': '0 0 * * *',
            'is_active': False
        }

        created = await repository.create(schedule_data, db_session)
        assert created.is_active is False

        # Activate
        activated = await repository.activate(created.id, db_session)
        assert activated.is_active is True

        # Deactivate
        deactivated = await repository.deactivate(created.id, db_session)
        assert deactivated.is_active is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_count_schedules(self, repository, db_session):
        """Test counting schedules."""
        # Create multiple schedules
        for i in range(3):
            schedule_data = {
                'name': f'Count Test Schedule {i}',
                'schedule_type': 'single',
                'test_definition_ids': [i+1],
                'cron_expression': f'0 {i} * * *',
                'is_active': True
            }
            await repository.create(schedule_data, db_session)

        # Count all
        total = await repository.count(db_session)
        assert total >= 3

        # Count active
        active_count = await repository.count_by_status(True, db_session)
        assert active_count >= 3
