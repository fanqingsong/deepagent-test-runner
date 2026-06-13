"""
Test Run Repository Tests

Unit tests for SQLAlchemyTestRunRepository using mocks and async patterns.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
from app.models.test_run import TestRun


@pytest.fixture
def repository():
    """Create repository instance."""
    return SQLAlchemyTestRunRepository()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.delete = Mock()
    return session


@pytest.fixture
def sample_test_run():
    """Create sample TestRun object."""
    test_run = TestRun(
        id=1,
        run_id="test-run-123",
        test_definition_id=100,
        status="pending",
        start_time=int(datetime.utcnow().timestamp() * 1000),
        total_tests=0,
        passed=0,
        failed=0,
        skipped=0
    )
    return test_run


class TestSQLAlchemyTestRunRepository:
    """Test suite for SQLAlchemyTestRunRepository."""

    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_db_session):
        """Test successful test run creation."""
        # Arrange
        run_id = "test-run-123"
        test_definition_id = 100
        start_time_ms = int(datetime.utcnow().timestamp() * 1000)

        # Act
        result = await repository.create(
            run_id=run_id,
            test_definition_id=test_definition_id,
            start_time_ms=start_time_ms,
            db_session=mock_db_session
        )

        # Assert
        assert result is not None
        assert result.run_id == run_id
        assert result.test_definition_id == test_definition_id
        assert result.status == "pending"
        assert result.start_time == start_time_ms
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_run_id(self, repository, mock_db_session):
        """Test creating with duplicate run_id raises ValueError."""
        # Arrange - simulate existing run
        with patch.object(repository, 'get_by_id', return_value=Mock(id=1)):
            run_id = "existing-run"

            # Act & Assert
            with pytest.raises(ValueError, match="already exists"):
                await repository.create(
                    run_id=run_id,
                    test_definition_id=100,
                    start_time_ms=1000000,
                    db_session=mock_db_session
                )

    @pytest.mark.asyncio
    async def test_create_database_error(self, repository, mock_db_session):
        """Test database error during create."""
        # Arrange
        mock_db_session.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await repository.create(
                run_id="test-run-123",
                test_definition_id=100,
                start_time_ms=1000000,
                db_session=mock_db_session
            )

        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db_session, sample_test_run):
        """Test getting test run by run_id when found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_test_run
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id("test-run-123", mock_db_session)

        # Assert
        assert result is sample_test_run
        assert result.run_id == "test-run-123"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db_session):
        """Test getting test run by run_id when not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id("non-existent", mock_db_session)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_success(self, repository, mock_db_session, sample_test_run):
        """Test successful status update."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=sample_test_run):
            run_id = "test-run-123"
            new_status = "running"

            # Act
            result = await repository.update_status(
                run_id=run_id,
                status=new_status,
                db_session=mock_db_session
            )

            # Assert
            assert result.status == new_status
            mock_db_session.flush.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_with_timestamps(self, repository, mock_db_session, sample_test_run):
        """Test status update with timestamps."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=sample_test_run):
            start_time_ms = 1000000
            end_time_ms = 2000000

            # Act
            result = await repository.update_status(
                run_id="test-run-123",
                status="passed",
                db_session=mock_db_session,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                error_message=None
            )

            # Assert
            assert result.start_time == start_time_ms
            assert result.end_time == end_time_ms

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repository, mock_db_session):
        """Test updating status when test run not found."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=None):
            # Act & Assert
            with pytest.raises(ValueError, match="not found"):
                await repository.update_status(
                    run_id="non-existent",
                    status="running",
                    db_session=mock_db_session
                )

    @pytest.mark.asyncio
    async def test_update_results_success(self, repository, mock_db_session, sample_test_run):
        """Test successful results update."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=sample_test_run):
            results = {
                'total_tests': 10,
                'passed': 8,
                'failed': 1,
                'skipped': 1,
                'status': 'passed',
                'total_duration_ms': 5000,
                'start_time_ms': 1000000,
                'end_time_ms': 1006000
            }

            # Act
            result = await repository.update_results("test-run-123", results, mock_db_session)

            # Assert
            assert result.total_tests == 10
            assert result.passed == 8
            assert result.failed == 1
            assert result.skipped == 1
            assert result.status == 'passed'
            assert result.total_duration == 5  # Converted to seconds

    @pytest.mark.asyncio
    async def test_update_results_calculates_duration(self, repository, mock_db_session, sample_test_run):
        """Test that duration is calculated when not provided."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=sample_test_run):
            results = {
                'total_tests': 10,
                'passed': 10,
                'failed': 0,
                'skipped': 0,
                'status': 'passed',
                'start_time_ms': 1000000,
                'end_time_ms': 1005000
            }

            # Act
            result = await repository.update_results("test-run-123", results, mock_db_session)

            # Assert
            assert result.total_duration == 5  # (1005000 - 1000000) / 1000

    @pytest.mark.asyncio
    async def test_get_by_test_definition_id(self, repository, mock_db_session):
        """Test getting runs by test definition ID."""
        # Arrange
        test_definition_id = 100
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock(), Mock()]
        mock_db_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_test_definition_id(
            test_definition_id=test_definition_id,
            db_session=mock_db_session,
            limit=10,
            offset=0
        )

        # Assert
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_pending_runs(self, repository, mock_db_session):
        """Test getting pending runs."""
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock(), Mock(), Mock()]
        mock_db_session.execute.return_value = mock_result

        # Act
        results = await repository.get_pending_runs(mock_db_session, limit=100)

        # Assert
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_recent_runs(self, repository, mock_db_session):
        """Test getting recent runs."""
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock()]
        mock_db_session.execute.return_value = mock_result

        # Act
        results = await repository.get_recent_runs(mock_db_session, days=7, limit=100)

        # Assert
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_count_by_status(self, repository, mock_db_session):
        """Test counting runs by status."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_db_session.execute.return_value = mock_result

        # Act
        count = await repository.count_by_status("passed", mock_db_session)

        # Assert
        assert count == 42

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_db_session, sample_test_run):
        """Test successful deletion."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=sample_test_run):
            # Act
            result = await repository.delete("test-run-123", mock_db_session)

            # Assert
            assert result is True
            mock_db_session.delete.assert_called_once_with(sample_test_run)
            mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_db_session):
        """Test deletion when run not found."""
        # Arrange
        with patch.object(repository, 'get_by_id', return_value=None):
            # Act
            result = await repository.delete("non-existent", mock_db_session)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_db_session):
        """Test exists when run exists."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await repository.exists("test-run-123", mock_db_session)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_db_session):
        """Test exists when run does not exist."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await repository.exists("non-existent", mock_db_session)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_stats_by_date_range(self, repository, mock_db_session):
        """Test getting statistics by date range."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Mock multiple execute calls
        execute_results = [
            Mock(scalar=Mock(return_value=100)),  # total_runs
            Mock(scalar=Mock(return_value=80)),   # passed
            Mock(scalar=Mock(return_value=15)),   # failed
            Mock(scalar=Mock(return_value=5.5))   # avg_duration
        ]
        mock_db_session.execute.side_effect = execute_results

        # Act
        stats = await repository.get_stats_by_date_range(start_date, end_date, mock_db_session)

        # Assert
        assert stats['total_runs'] == 100
        assert stats['passed'] == 80
        assert stats['failed'] == 15
        assert stats['avg_duration'] == 5.5

    @pytest.mark.asyncio
    async def test_get_all_without_filter(self, repository, mock_db_session):
        """Test getting all runs without status filter."""
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock(), Mock()]
        mock_db_session.execute.return_value = mock_result

        # Act
        results = await repository.get_all(mock_db_session, limit=50, offset=0)

        # Assert
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_all_with_filter(self, repository, mock_db_session):
        """Test getting all runs with status filter."""
        # Arrange
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock()]
        mock_db_session.execute.return_value = mock_result

        # Act
        results = await repository.get_all(mock_db_session, limit=50, offset=0, status_filter="passed")

        # Assert
        assert len(results) == 1
