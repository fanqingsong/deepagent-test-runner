"""
Tests for SuiteService with Result wrapper types.

Tests the migrated Result-based methods to ensure proper error handling,
type safety, and backward compatibility.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.services.suite_service import SuiteService
from app.core.simple_result_types import (
    ServiceSuccess, ServiceError, service_success, service_error,
    service_validation_error, service_not_found
)
from app.models.suite_run import SuiteRun, SuiteRunEntry
from app.models.test_suite import TestSuite


class TestSuiteServiceResultTypes:
    """Test suite for SuiteService Result-based methods."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def suite_service(self, db_session):
        """Create SuiteService instance."""
        return SuiteService(db_session)

    @pytest.fixture
    def sample_suite(self):
        """Create sample test suite."""
        suite = Mock(spec=TestSuite)
        suite.id = 1
        suite.name = "Test Suite 1"
        suite.is_dynamic = False
        suite.execution_mode = "sequential"
        suite.fail_strategy = "continue"
        suite.environment_vars = {"BASE": "value"}
        suite.suite_entries = None
        suite.test_definition_ids = [10, 20, 30]
        suite.setup_test_id = None
        suite.teardown_test_id = None
        return suite

    @pytest.fixture
    def sample_suite_run(self):
        """Create sample suite run."""
        suite_run = Mock(spec=SuiteRun)
        suite_run.id = 1
        suite_run.suite_id = 1
        suite_run.run_id = "suite-abc123"
        suite_run.status = "pending"
        suite_run.execution_mode = "sequential"
        suite_run.total_tests = 3
        suite_run.passed = 0
        suite_run.failed = 0
        suite_run.skipped = 0
        suite_run.environment = {}
        suite_run.triggered_by = "manual"
        suite_run.start_time = 1234567890
        suite_run.end_time = None
        return suite_run

    # ==================== resolve_suite_entries_v2 tests ====================

    def test_resolve_suite_entries_v2_with_static_entries(self, suite_service, sample_suite):
        """Test resolving entries with static suite_entries."""
        sample_suite.suite_entries = [
            {"test_definition_id": 10, "order": 1, "enabled": True},
            {"test_definition_id": 20, "order": 2, "enabled": True},
        ]

        result = suite_service.resolve_suite_entries_v2(sample_suite)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        entries = result.get_data()
        assert len(entries) == 2
        assert entries[0]["test_definition_id"] == 10

    def test_resolve_suite_entries_v2_with_disabled_entries(self, suite_service, sample_suite):
        """Test resolving entries filters out disabled entries."""
        sample_suite.suite_entries = [
            {"test_definition_id": 10, "order": 1, "enabled": True},
            {"test_definition_id": 20, "order": 2, "enabled": False},
        ]

        result = suite_service.resolve_suite_entries_v2(sample_suite)

        assert result.is_success()
        entries = result.get_data()
        assert len(entries) == 1
        assert entries[0]["test_definition_id"] == 10

    def test_resolve_suite_entries_v2_fallback_to_test_definition_ids(self, suite_service, sample_suite):
        """Test resolving entries falls back to test_definition_ids."""
        sample_suite.suite_entries = None
        sample_suite.test_definition_ids = [10, 20, 30]

        result = suite_service.resolve_suite_entries_v2(sample_suite)

        assert result.is_success()
        entries = result.get_data()
        assert len(entries) == 3
        assert entries[0]["test_definition_id"] == 10
        assert entries[0]["condition"] == "always"

    def test_resolve_suite_entries_v2_with_none_suite(self, suite_service):
        """Test resolve_suite_entries_v2 with None suite."""
        result = suite_service.resolve_suite_entries_v2(None)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "cannot be None" in result.message.lower()

    # ==================== resolve_dynamic_suite_v2 tests ====================

    @pytest.mark.asyncio
    async def test_resolve_dynamic_suite_v2_success(self, suite_service, sample_suite):
        """Test resolving dynamic suite successfully."""
        from app.models.test_definition import TestDefinition

        sample_suite.is_dynamic = True
        sample_suite.dynamic_tag_rule = {"tags": ["smoke"], "match": "any"}

        # Mock database query
        mock_td = Mock(spec=TestDefinition)
        mock_td.id = 10
        mock_result = Mock()
        mock_result.scalars().all.return_value = [mock_td]

        suite_service.db.execute = AsyncMock(return_value=mock_result)

        result = await suite_service.resolve_dynamic_suite_v2(sample_suite)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        entries = result.get_data()
        assert len(entries) == 1
        assert entries[0]["test_definition_id"] == 10

    @pytest.mark.asyncio
    async def test_resolve_dynamic_suite_v2_no_tags(self, suite_service, sample_suite):
        """Test resolving dynamic suite with no tags."""
        sample_suite.is_dynamic = True
        sample_suite.dynamic_tag_rule = {}

        result = await suite_service.resolve_dynamic_suite_v2(sample_suite)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        entries = result.get_data()
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_resolve_dynamic_suite_v2_with_none_suite(self, suite_service):
        """Test resolve_dynamic_suite_v2 with None suite."""
        result = await suite_service.resolve_dynamic_suite_v2(None)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    # ==================== create_suite_run_v2 tests ====================

    @pytest.mark.asyncio
    async def test_create_suite_run_v2_success(self, suite_service, sample_suite):
        """Test successful suite run creation."""
        # Mock database queries
        suite_service.db.execute = AsyncMock()
        suite_service.db.flush = AsyncMock()
        suite_service.db.refresh = AsyncMock()

        # Mock suite retrieval
        suite_service._get_suite = AsyncMock(return_value=sample_suite)

        result = await suite_service.create_suite_run_v2(
            suite_id=1,
            triggered_by="manual"
        )

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        suite_run = result.get_data()
        assert result.metadata["entry_count"] == 3
        assert suite_service.db.add.called
        assert suite_service.db.commit.called

    @pytest.mark.asyncio
    async def test_create_suite_run_v2_suite_not_found(self, suite_service):
        """Test create_suite_run_v2 with non-existent suite."""
        suite_service._get_suite = AsyncMock(return_value=None)

        result = await suite_service.create_suite_run_v2(suite_id=999)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "NOT_FOUND"
        assert "TestSuite" in result.details.get("resource", "")

    @pytest.mark.asyncio
    async def test_create_suite_run_v2_no_entries(self, suite_service, sample_suite):
        """Test create_suite_run_v2 with suite that has no entries."""
        sample_suite.test_definition_ids = []
        sample_suite.suite_entries = None
        sample_suite.is_dynamic = False

        suite_service._get_suite = AsyncMock(return_value=sample_suite)

        result = await suite_service.create_suite_run_v2(suite_id=1)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "no test entries" in result.message.lower()

    @pytest.mark.asyncio
    async def test_create_suite_run_v2_database_error(self, suite_service, sample_suite):
        """Test create_suite_run_v2 with database error."""
        suite_service._get_suite = AsyncMock(return_value=sample_suite)
        suite_service.db.flush = AsyncMock(side_effect=Exception("Database connection failed"))

        result = await suite_service.create_suite_run_v2(suite_id=1)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "CREATE_ERROR"
        assert suite_service.db.rollback.called

    # ==================== get_suite_run_with_entries_v2 tests ====================

    @pytest.mark.asyncio
    async def test_get_suite_run_with_entries_v2_success(self, suite_service, sample_suite_run):
        """Test successful suite run retrieval with entries."""
        mock_result = Mock()
        mock_result.unique().scalar_one_or_none.return_value = sample_suite_run
        suite_service.db.execute = AsyncMock(return_value=mock_result)

        result = await suite_service.get_suite_run_with_entries_v2("suite-abc123")

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data() == sample_suite_run

    @pytest.mark.asyncio
    async def test_get_suite_run_with_entries_v2_not_found(self, suite_service):
        """Test get_suite_run_with_entries_v2 with non-existent run."""
        mock_result = Mock()
        mock_result.unique().scalar_one_or_none.return_value = None
        suite_service.db.execute = AsyncMock(return_value=mock_result)

        result = await suite_service.get_suite_run_with_entries_v2("non-existent")

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "NOT_FOUND"
        assert "SuiteRun" in result.details.get("resource", "")

    # ==================== cancel_suite_run_v2 tests ====================

    @pytest.mark.asyncio
    async def test_cancel_suite_run_v2_success(self, suite_service, sample_suite_run):
        """Test successful suite run cancellation."""
        sample_suite_run.status = "running"

        suite_service._get_suite_run = AsyncMock(return_value=sample_suite_run)
        suite_service._get_entries = AsyncMock(return_value=[])
        suite_service.db.commit = AsyncMock()
        suite_service.db.refresh = AsyncMock()

        result = await suite_service.cancel_suite_run_v2(suite_run_id=1)

        assert isinstance(result, ServiceSuccess)
        assert result.is_success()
        assert result.get_data().status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_suite_run_v2_not_found(self, suite_service):
        """Test cancel_suite_run_v2 with non-existent run."""
        suite_service._get_suite_run = AsyncMock(return_value=None)

        result = await suite_service.cancel_suite_run_v2(suite_run_id=999)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cancel_suite_run_v2_invalid_status(self, suite_service, sample_suite_run):
        """Test cancel_suite_run_v2 with invalid status."""
        sample_suite_run.status = "completed"

        suite_service._get_suite_run = AsyncMock(return_value=sample_suite_run)

        result = await suite_service.cancel_suite_run_v2(suite_run_id=1)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "Cannot cancel" in result.message
        assert result.details.get("current_status") == "completed"

    @pytest.mark.asyncio
    async def test_cancel_suite_run_v2_database_error(self, suite_service, sample_suite_run):
        """Test cancel_suite_run_v2 with database error."""
        sample_suite_run.status = "running"

        suite_service._get_suite_run = AsyncMock(return_value=sample_suite_run)
        suite_service._get_entries = AsyncMock(return_value=[])
        suite_service.db.commit = AsyncMock(side_effect=Exception("Database error"))

        result = await suite_service.cancel_suite_run_v2(suite_run_id=1)

        assert isinstance(result, ServiceError)
        assert result.is_error()
        assert result.error_code == "CANCEL_ERROR"

    # ==================== Backward compatibility tests ====================

    def test_legacy_resolve_suite_entries_still_works(self, suite_service, sample_suite):
        """Test that legacy resolve_suite_entries method still works."""
        sample_suite.suite_entries = [
            {"test_definition_id": 10, "order": 1, "enabled": True},
        ]

        result = suite_service.resolve_suite_entries(sample_suite)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["test_definition_id"] == 10
        # Not a ServiceSuccess - it's the direct list
        assert not isinstance(result, (ServiceSuccess, ServiceError))

    @pytest.mark.asyncio
    async def test_legacy_resolve_dynamic_suite_still_works(self, suite_service, sample_suite):
        """Test that legacy resolve_dynamic_suite method still works."""
        from app.models.test_definition import TestDefinition

        sample_suite.is_dynamic = True
        sample_suite.dynamic_tag_rule = {"tags": ["smoke"], "match": "any"}

        mock_td = Mock(spec=TestDefinition)
        mock_td.id = 10
        mock_result = Mock()
        mock_result.scalars().all.return_value = [mock_td]

        suite_service.db.execute = AsyncMock(return_value=mock_result)

        result = await suite_service.resolve_dynamic_suite(sample_suite)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["test_definition_id"] == 10
        # Not a ServiceSuccess - it's the direct list
        assert not isinstance(result, (ServiceSuccess, ServiceError))


class TestSuiteServiceIntegration:
    """Integration tests for SuiteService Result methods."""

    @pytest.mark.asyncio
    async def test_full_suite_run_workflow(self):
        """Test complete suite run workflow with Result types."""
        db_session = Mock(spec=AsyncSession)
        db_session.commit = AsyncMock()
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        service = SuiteService(db_session)

        # Mock suite
        mock_suite = Mock(spec=TestSuite)
        mock_suite.id = 1
        mock_suite.test_definition_ids = [10, 20]
        mock_suite.suite_entries = None
        mock_suite.is_dynamic = False
        mock_suite.execution_mode = "sequential"
        mock_suite.environment_vars = {}

        service._get_suite = AsyncMock(return_value=mock_suite)

        # Create suite run
        create_result = await service.create_suite_run_v2(
            suite_id=1,
            triggered_by="manual"
        )

        assert create_result.is_success()
        suite_run = create_result.get_data()
        assert suite_run.status == "pending"

    @pytest.mark.asyncio
    async def test_error_recovery_chain(self):
        """Test error recovery across operations."""
        db_session = Mock(spec=AsyncSession)
        db_session.commit = AsyncMock()
        db_session.rollback = AsyncMock()

        service = SuiteService(db_session)

        # Test not found error
        service._get_suite = AsyncMock(return_value=None)

        result = await service.create_suite_run_v2(suite_id=999)

        assert result.is_error()
        assert result.error_code == "NOT_FOUND"
        assert result.get_http_status() == 404
