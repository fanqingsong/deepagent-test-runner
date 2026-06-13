"""
Tests for ExecutionService with Result wrapper types.

Tests the migrated Result-based methods to ensure proper error handling,
type safety, and backward compatibility.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.execution_service import ExecutionService
from app.core.simple_result_types import (
    ServiceSuccess, ServiceError, service_success, service_error,
    service_validation_error, service_not_found
)
from app.models.test_run import TestRun
from app.models.schedule import Schedule


class TestExecutionServiceResultTypes:
    """Test suite for ExecutionService Result-based methods."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_repository(self):
        """Mock test run repository."""
        repo = Mock()
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def execution_service(self, db_session, mock_repository):
        """Create ExecutionService instance."""
        with patch('app.services.execution_service.RepositoryFactory.get_test_run_repository', return_value=mock_repository):
            service = ExecutionService(db_session=db_session)
            service.test_run_repository = mock_repository
            return service

    @pytest.fixture
    def sample_schedule(self):
        """Create sample schedule."""
        schedule = Mock(spec=Schedule)
        schedule.id = 1
        schedule.allow_concurrent = False
        schedule.environment_overrides = {"TEST": "value"}
        return schedule

    @pytest.fixture
    def sample_test_run(self):
        """Create sample test run."""
        test_run = Mock(spec=TestRun)
        test_run.id = 1
        test_run.run_id = "test-run-123"
        test_run.status = "pending"
        test_run.test_definition_id = 10
        return test_run

    # ==================== resolve_target_tests_v2 tests ====================

    @pytest.mark.asyncio
    async def test_resolve_target_tests_v2_success(self, execution_service, sample_schedule):
        """Test successful target test resolution."""
        # Mock schedule resolver
        execution_service.schedule_resolver.resolve_schedule = AsyncMock(return_value=[1, 2, 3])

        result = await execution_service.resolve_target_tests_v2(sample_schedule, execution_service.db)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data() == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_resolve_target_tests_v2_value_error(self, execution_service, sample_schedule):
        """Test resolve_target_tests_v2 with ValueError."""
        # Mock schedule resolver to raise ValueError
        execution_service.schedule_resolver.resolve_schedule = AsyncMock(
            side_effect=ValueError("Invalid schedule configuration")
        )

        result = await execution_service.resolve_target_tests_v2(sample_schedule, execution_service.db)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "Invalid schedule configuration" in result.message

    @pytest.mark.asyncio
    async def test_resolve_target_tests_v2_unexpected_error(self, execution_service, sample_schedule):
        """Test resolve_target_tests_v2 with unexpected error."""
        # Mock schedule resolver to raise generic Exception
        execution_service.schedule_resolver.resolve_schedule = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        result = await execution_service.resolve_target_tests_v2(sample_schedule, execution_service.db)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "RESOLVE_ERROR"
        assert "Failed to resolve target tests" in result.message

    # ==================== create_test_run_v2 tests ====================

    @pytest.mark.asyncio
    async def test_create_test_run_v2_success(self, execution_service, sample_test_run):
        """Test successful test run creation."""
        # Mock repository
        execution_service.test_run_repository.create = AsyncMock(return_value=sample_test_run)

        result = await execution_service.create_test_run_v2(
            run_id="test-run-123",
            test_definition_ids=[10, 20, 30],
            environment={"TEST": "value"},
            db=execution_service.db
        )

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data() == sample_test_run
        assert result.metadata["test_count"] == 3

    @pytest.mark.asyncio
    async def test_create_test_run_v2_empty_test_ids(self, execution_service):
        """Test create_test_run_v2 with empty test definition IDs."""
        result = await execution_service.create_test_run_v2(
            run_id="test-run-123",
            test_definition_ids=[],
            environment={"TEST": "value"},
            db=execution_service.db
        )

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "cannot be empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_create_test_run_v2_repository_error(self, execution_service):
        """Test create_test_run_v2 with repository error."""
        # Mock repository to raise error
        execution_service.test_run_repository.create = AsyncMock(
            side_effect=ValueError("Invalid test definition")
        )

        result = await execution_service.create_test_run_v2(
            run_id="test-run-123",
            test_definition_ids=[10],
            environment={"TEST": "value"},
            db=execution_service.db
        )

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_test_run_v2_unexpected_error(self, execution_service):
        """Test create_test_run_v2 with unexpected error."""
        # Mock repository to raise generic Exception
        execution_service.test_run_repository.create = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        result = await execution_service.create_test_run_v2(
            run_id="test-run-123",
            test_definition_ids=[10],
            environment={"TEST": "value"},
            db=execution_service.db
        )

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "CREATE_ERROR"

    # ==================== update_run_status_v2 tests ====================

    @pytest.mark.asyncio
    async def test_update_run_status_v2_success(self, execution_service, sample_test_run):
        """Test successful run status update."""
        # Mock status manager
        execution_service.status_manager = Mock()
        execution_service.status_manager.update_run_status = AsyncMock(return_value=sample_test_run)

        result = await execution_service.update_run_status_v2(
            run_id="test-run-123",
            status="running"
        )

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data() == sample_test_run

    @pytest.mark.asyncio
    async def test_update_run_status_v2_not_found(self, execution_service):
        """Test update_run_status_v2 with non-existent run."""
        # Mock status manager to return None
        execution_service.status_manager = Mock()
        execution_service.status_manager.update_run_status = AsyncMock(return_value=None)

        result = await execution_service.update_run_status_v2(
            run_id="non-existent-run",
            status="running"
        )

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "NOT_FOUND"
        assert "TestRun" in result.details.get("resource", "")

    @pytest.mark.asyncio
    async def test_update_run_status_v2_invalid_transition(self, execution_service):
        """Test update_run_status_v2 with invalid status transition."""
        # Mock status manager to raise ValueError
        execution_service.status_manager = Mock()
        execution_service.status_manager.update_run_status = AsyncMock(
            side_effect=ValueError("Invalid status transition")
        )

        result = await execution_service.update_run_status_v2(
            run_id="test-run-123",
            status="invalid"
        )

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "Invalid status transition" in result.message

    # ==================== save_test_results_v2 tests ====================

    @pytest.mark.asyncio
    async def test_save_test_results_v2_success(self, execution_service, sample_test_run):
        """Test successful test results saving."""
        # Mock result persister
        execution_service.result_persister = Mock()
        execution_service.result_persister.save_test_results = AsyncMock(return_value=sample_test_run)

        results = {
            "total_tests": 10,
            "passed": 8,
            "failed": 1,
            "skipped": 1,
            "status": "passed",
            "test_definition_id": 10
        }

        result = await execution_service.save_test_results_v2("test-run-123", results)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data() == sample_test_run
        assert result.metadata["total_tests"] == 10
        assert result.metadata["passed"] == 8

    @pytest.mark.asyncio
    async def test_save_test_results_v2_empty_results(self, execution_service):
        """Test save_test_results_v2 with empty results."""
        result = await execution_service.save_test_results_v2("test-run-123", {})

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "cannot be empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_save_test_results_v2_validation_error(self, execution_service):
        """Test save_test_results_v2 with validation error."""
        # Mock result persister to raise ValueError
        execution_service.result_persister = Mock()
        execution_service.result_persister.save_test_results = AsyncMock(
            side_effect=ValueError("Invalid results data")
        )

        results = {"total_tests": 10}

        result = await execution_service.save_test_results_v2("test-run-123", results)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_save_test_results_v2_unexpected_error(self, execution_service):
        """Test save_test_results_v2 with unexpected error."""
        # Mock result persister to raise generic Exception
        execution_service.result_persister = Mock()
        execution_service.result_persister.save_test_results = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        results = {"total_tests": 10}

        result = await execution_service.save_test_results_v2("test-run-123", results)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "SAVE_ERROR"

    # ==================== Backward compatibility tests ====================

    @pytest.mark.asyncio
    async def test_legacy_create_test_run_still_works(self, execution_service, sample_test_run):
        """Test that legacy create_test_run method still works."""
        execution_service.test_run_repository.create = AsyncMock(return_value=sample_test_run)

        result = await execution_service.create_test_run(
            run_id="test-run-123",
            test_definition_ids=[10, 20],
            environment={"TEST": "value"},
            db=execution_service.db
        )

        assert isinstance(result, TestRun)
        assert result.run_id == "test-run-123"
        # Not a ServiceSuccess - it's the direct object
        assert not isinstance(result, (ServiceSuccess, ServiceError))

    @pytest.mark.asyncio
    async def test_legacy_resolve_target_tests_still_works(self, execution_service):
        """Test that legacy resolve_target_tests method still works."""
        execution_service.schedule_resolver.resolve_schedule = AsyncMock(return_value=[1, 2, 3])

        result = await execution_service.resolve_target_tests(Mock(), execution_service.db)

        assert isinstance(result, list)
        assert result == [1, 2, 3]
        # Not a ServiceSuccess - it's the direct list
        assert not isinstance(result, (ServiceSuccess, ServiceError))

    @pytest.mark.asyncio
    async def test_legacy_update_run_status_still_works(self, execution_service, sample_test_run):
        """Test that legacy update_run_status method still works."""
        execution_service.status_manager = Mock()
        execution_service.status_manager.update_run_status = AsyncMock(return_value=sample_test_run)

        result = await execution_service.update_run_status("test-run-123", "running")

        assert isinstance(result, TestRun)
        assert result.run_id == "test-run-123"
        # Not a ServiceSuccess - it's the direct object
        assert not isinstance(result, (ServiceSuccess, ServiceError))


class TestExecutionServiceIntegration:
    """Integration tests for ExecutionService Result methods."""

    @pytest.mark.asyncio
    async def test_chained_result_operations(self):
        """Test chaining multiple Result-based operations."""
        db_session = Mock(spec=AsyncSession)
        mock_repo = Mock()
        mock_repo.create = AsyncMock(return_value=Mock(spec=TestRun, run_id="test-123", id=1))

        with patch('app.services.execution_service.RepositoryFactory.get_test_run_repository', return_value=mock_repo):
            service = ExecutionService(db_session=db_session)

        # Chain: create -> update -> save results
        create_result = await service.create_test_run_v2(
            run_id="test-123",
            test_definition_ids=[10],
            environment={},
            db=db_session
        )

        assert create_result.is_success()

        # Simulate status update
        service.status_manager = Mock()
        service.status_manager.update_run_status = AsyncMock(
            return_value=create_result.get_data()
        )

        update_result = await service.update_run_status_v2("test-123", "running")
        assert update_result.is_success()

        # Simulate results save
        service.result_persister = Mock()
        service.result_persister.save_test_results = AsyncMock(
            return_value=create_result.get_data()
        )

        save_result = await service.save_test_results_v2("test-123", {"total_tests": 1, "status": "passed"})
        assert save_result.is_success()

    @pytest.mark.asyncio
    async def test_error_propagation_chain(self):
        """Test error handling across chained operations."""
        db_session = Mock(spec=AsyncSession)
        mock_repo = Mock()
        mock_repo.create = AsyncMock(side_effect=ValueError("Invalid configuration"))

        with patch('app.services.execution_service.RepositoryFactory.get_test_run_repository', return_value=mock_repo):
            service = ExecutionService(db_session=db_session)

        result = await service.create_test_run_v2(
            run_id="test-123",
            test_definition_ids=[],
            environment={},
            db=db_session
        )

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert result.get_http_status() == 400
