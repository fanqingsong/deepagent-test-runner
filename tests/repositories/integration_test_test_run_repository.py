"""
Integration Tests for TestRun Repository

Tests repository with real in-memory database to verify SQLAlchemy integration.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
from app.models.test_run import TestRun


@pytest.mark.integration
class TestTestRunRepositoryIntegration:
    """Integration tests for TestRun repository."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, test_db_session):
        """Test creating and retrieving a test run."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run_id = "integration-test-1"
        test_definition_id = 100
        start_time_ms = int(datetime.utcnow().timestamp() * 1000)

        # Act - Create
        created_run = await repository.create(
            run_id=run_id,
            test_definition_id=test_definition_id,
            start_time_ms=start_time_ms,
            db_session=test_db_session
        )

        # Assert - Created
        assert created_run is not None
        assert created_run.run_id == run_id
        assert created_run.test_definition_id == test_definition_id
        assert created_run.status == "pending"

        # Act - Retrieve
        retrieved_run = await repository.get_by_id(run_id, test_db_session)

        # Assert - Retrieved
        assert retrieved_run is not None
        assert retrieved_run.id == created_run.id
        assert retrieved_run.run_id == run_id

    @pytest.mark.asyncio
    async def test_update_status(self, test_db_session):
        """Test updating test run status."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run = await repository.create(
            run_id="status-test-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )

        # Act
        updated_run = await repository.update_status(
            run_id=run.run_id,
            status="running",
            db_session=test_db_session,
            start_time_ms=1000000,
            end_time_ms=2000000
        )

        # Assert
        assert updated_run.status == "running"
        assert updated_run.start_time == 1000000
        assert updated_run.end_time == 2000000

    @pytest.mark.asyncio
    async def test_update_results(self, test_db_session):
        """Test updating test run with results."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run = await repository.create(
            run_id="results-test-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )

        results = {
            'total_tests': 10,
            'passed': 8,
            'failed': 1,
            'skipped': 1,
            'status': 'passed',
            'total_duration_ms': 5000,
            'start_time_ms': 1000000,
            'end_time_ms': 1005000
        }

        # Act
        updated_run = await repository.update_results(run.run_id, results, test_db_session)

        # Assert
        assert updated_run.total_tests == 10
        assert updated_run.passed == 8
        assert updated_run.failed == 1
        assert updated_run.skipped == 1
        assert updated_run.status == 'passed'
        assert updated_run.total_duration == 5  # Converted to seconds

    @pytest.mark.asyncio
    async def test_get_by_test_definition_id(self, test_db_session):
        """Test retrieving runs by test definition ID."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        test_definition_id = 100

        # Create multiple runs for same definition
        for i in range(3):
            await repository.create(
                run_id=f"test-{i}",
                test_definition_id=test_definition_id,
                start_time_ms=1000000 + (i * 1000),
                db_session=test_db_session
            )

        # Act
        runs = await repository.get_by_test_definition_id(
            test_definition_id=test_definition_id,
            db_session=test_db_session,
            limit=10
        )

        # Assert
        assert len(runs) == 3
        assert all(run.test_definition_id == test_definition_id for run in runs)

    @pytest.mark.asyncio
    async def test_get_pending_runs(self, test_db_session):
        """Test retrieving pending runs."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()

        # Create pending runs
        for i in range(3):
            run = await repository.create(
                run_id=f"pending-{i}",
                test_definition_id=100,
                start_time_ms=1000000,
                db_session=test_db_session
            )
            # Keep status as pending

        # Create non-pending run
        completed_run = await repository.create(
            run_id="completed-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )
        await repository.update_status(completed_run.run_id, "passed", test_db_session)

        # Act
        pending_runs = await repository.get_pending_runs(test_db_session)

        # Assert
        assert len(pending_runs) == 3
        assert all(run.status == "pending" for run in pending_runs)

    @pytest.mark.asyncio
    async def test_count_by_status(self, test_db_session):
        """Test counting runs by status."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()

        # Create runs with different statuses
        for status in ["pending", "pending", "running", "passed", "failed"]:
            run = await repository.create(
                run_id=f"run-{status}",
                test_definition_id=100,
                start_time_ms=1000000,
                db_session=test_db_session
            )
            await repository.update_status(run.run_id, status, test_db_session)

        # Act & Assert
        pending_count = await repository.count_by_status("pending", test_db_session)
        assert pending_count == 2

        passed_count = await repository.count_by_status("passed", test_db_session)
        assert passed_count == 1

        failed_count = await repository.count_by_status("failed", test_db_session)
        assert failed_count == 1

    @pytest.mark.asyncio
    async def test_delete(self, test_db_session):
        """Test deleting a test run."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run = await repository.create(
            run_id="delete-test-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )

        # Act
        deleted = await repository.delete(run.run_id, test_db_session)

        # Assert
        assert deleted is True

        # Verify it's gone
        retrieved = await repository.get_by_id(run.run_id, test_db_session)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_exists(self, test_db_session):
        """Test checking if run exists."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run = await repository.create(
            run_id="exists-test-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )

        # Act & Assert
        assert await repository.exists(run.run_id, test_db_session) is True
        assert await repository.exists("non-existent", test_db_session) is False

    @pytest.mark.asyncio
    async def test_get_recent_runs(self, test_db_session):
        """Test retrieving recent runs."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()

        # Create runs at different times
        for i in range(5):
            await repository.create(
                run_id=f"recent-{i}",
                test_definition_id=100,
                start_time_ms=1000000 + (i * 1000),
                db_session=test_db_session
            )

        # Act
        recent_runs = await repository.get_recent_runs(
            test_db_session,
            days=7,
            limit=10
        )

        # Assert
        assert len(recent_runs) >= 5

    @pytest.mark.asyncio
    async def test_get_all_with_filtering(self, test_db_session):
        """Test retrieving all runs with filtering."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()

        # Create runs with different statuses
        statuses = ["pending", "running", "passed", "failed", "passed"]
        for i, status in enumerate(statuses):
            run = await repository.create(
                run_id=f"filtered-{i}",
                test_definition_id=100,
                start_time_ms=1000000 + (i * 1000),
                db_session=test_db_session
            )
            await repository.update_status(run.run_id, status, test_db_session)

        # Act - Get all
        all_runs = await repository.get_all(test_db_session, limit=10)

        # Assert
        assert len(all_runs) >= 5

        # Act - Filter by status
        passed_runs = await repository.get_all(
            test_db_session,
            limit=10,
            status_filter="passed"
        )

        # Assert
        assert len(passed_runs) >= 2
        assert all(run.status == "passed" for run in passed_runs)

    @pytest.mark.asyncio
    async def test_get_stats_by_date_range(self, test_db_session):
        """Test getting statistics for date range."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()

        # Create runs with different outcomes
        for status in ["passed", "passed", "failed"]:
            run = await repository.create(
                run_id=f"stats-{status}",
                test_definition_id=100,
                start_time_ms=1000000,
                db_session=test_db_session
            )
            results = {
                'total_tests': 10,
                'passed': 10 if status == "passed" else 5,
                'failed': 0 if status == "passed" else 5,
                'skipped': 0,
                'status': status,
                'total_duration_ms': 5000,
                'start_time_ms': 1000000,
                'end_time_ms': 1005000
            }
            await repository.update_results(run.run_id, results, test_db_session)

        # Act
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)
        stats = await repository.get_stats_by_date_range(start_date, end_date, test_db_session)

        # Assert
        assert stats['total_runs'] >= 3
        assert stats['passed'] >= 2
        assert stats['failed'] >= 1
        assert stats['avg_duration'] > 0

    @pytest.mark.asyncio
    async def test_get_by_pk(self, test_db_session):
        """Test retrieving by primary key."""
        # Arrange
        repository = SQLAlchemyTestRunRepository()
        run = await repository.create(
            run_id="pk-test-1",
            test_definition_id=100,
            start_time_ms=1000000,
            db_session=test_db_session
        )

        # Act
        retrieved_run = await repository.get_by_pk(run.id, test_db_session)

        # Assert
        assert retrieved_run is not None
        assert retrieved_run.id == run.id
        assert retrieved_run.run_id == run.run_id
