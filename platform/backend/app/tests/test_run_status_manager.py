"""
Tests for RunStatusManager

Tests the status management logic extracted from ExecutionService.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.run_status_manager import RunStatusManager
from app.models.test_run import TestRun


class TestRunStatusManager:
    """Test suite for RunStatusManager."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def status_manager(self, mock_db):
        """Create RunStatusManager instance."""
        return RunStatusManager(mock_db)

    def test_valid_transitions_constant(self):
        """Test that VALID_TRANSITIONS is properly defined."""
        expected = {
            'pending': ['running', 'skipped', 'failed', 'error'],
            'running': ['passed', 'failed', 'skipped', 'error'],
            'failed': ['pending'],
        }
        assert RunStatusManager.VALID_TRANSITIONS == expected

    def test_validate_transition_valid(self, status_manager):
        """Test valid status transition validation."""
        assert status_manager._validate_transition('pending', 'running') is True
        assert status_manager._validate_transition('running', 'passed') is True
        assert status_manager._validate_transition('failed', 'pending') is True

    def test_validate_transition_invalid(self, status_manager):
        """Test invalid status transition validation."""
        assert status_manager._validate_transition('pending', 'passed') is False
        assert status_manager._validate_transition('running', 'pending') is False
        assert status_manager._validate_transition('passed', 'running') is False

    @pytest.mark.asyncio
    async def test_update_run_status_basic(self, status_manager, mock_db):
        """Test basic status update."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='pending',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Update status
        result = await status_manager.update_run_status("test-run-123", "running")

        # Verify the status was updated
        assert result.status == "running"
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_run_status_invalid_transition(self, status_manager, mock_db):
        """Test that invalid transitions raise ValueError."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='pending',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Try invalid transition
        with pytest.raises(ValueError, match="Invalid status transition"):
            await status_manager.update_run_status("test-run-123", "passed")

    @pytest.mark.asyncio
    async def test_update_run_status_not_found(self, status_manager, mock_db):
        """Test that non-existent run raises ValueError."""
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Try to update non-existent run
        with pytest.raises(ValueError, match="Test run .* not found"):
            await status_manager.update_run_status("nonexistent", "running")

    @pytest.mark.asyncio
    async def test_update_run_status_with_error_message(self, status_manager, mock_db):
        """Test status update with error message."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='running',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Update status with error message
        result = await status_manager.update_run_status(
            "test-run-123",
            "failed",
            error_message="Test failed"
        )

        # Verify the error message was set
        assert result.status == "failed"
        assert result.error_message == "Test failed"

    @pytest.mark.asyncio
    async def test_ensure_run_running_from_pending(self, status_manager, mock_db):
        """Test ensuring run is running from pending state."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='pending',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Ensure running
        result = await status_manager.ensure_run_running("test-run-123")

        # Verify transition
        assert result.status == "running"

    @pytest.mark.asyncio
    async def test_ensure_run_running_already_running(self, status_manager, mock_db):
        """Test that already-running run is not modified."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='running',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Ensure running
        result = await status_manager.ensure_run_running("test-run-123")

        # Verify no transition occurred
        assert result.status == "running"
        assert result == test_run

    @pytest.mark.asyncio
    async def test_ensure_run_running_from_failed(self, status_manager, mock_db):
        """Test retry logic from failed state."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='failed',
            start_time=1000,
            end_time=2000,
            error_message="Previous failure",
            total_duration=1000
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Ensure running (should go through pending -> running)
        result = await status_manager.ensure_run_running("test-run-123")

        # Verify transition
        assert result.status == "running"

    @pytest.mark.asyncio
    async def test_mark_run_failed_from_running(self, status_manager, mock_db):
        """Test marking a run as failed."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='running',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Mark as failed
        result = await status_manager.mark_run_failed("test-run-123", "Test error")

        # Verify transition
        assert result.status == "failed"
        assert result.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_mark_run_failed_already_failed(self, status_manager, mock_db):
        """Test that already-failed run only updates error message."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='failed',
            start_time=1000,
            end_time=2000,
            error_message="Old error",
            total_duration=1000
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Mark as failed with new error message
        result = await status_manager.mark_run_failed("test-run-123", "New error")

        # Verify error message was updated
        assert result.status == "failed"
        assert result.error_message == "New error"

    @pytest.mark.asyncio
    async def test_finalize_run_status_if_needed_from_running(self, status_manager, mock_db):
        """Test finalizing run status from running state."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='running',
            start_time=1000,
            end_time=None,
            error_message=None,
            total_duration=0
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Finalize to passed
        result = await status_manager.finalize_run_status_if_needed(
            "test-run-123",
            "passed"
        )

        # Verify transition
        assert result.status == "passed"

    @pytest.mark.asyncio
    async def test_finalize_run_status_already_at_target(self, status_manager, mock_db):
        """Test that already-finalized run is not modified."""
        # Create a mock test run
        test_run = TestRun(
            id=1,
            run_id="test-run-123",
            status='passed',
            start_time=1000,
            end_time=2000,
            error_message=None,
            total_duration=1000
        )

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_run
        mock_db.execute.return_value = mock_result

        # Finalize to same status
        result = await status_manager.finalize_run_status_if_needed(
            "test-run-123",
            "passed"
        )

        # Verify no transition occurred
        assert result.status == "passed"
        assert result == test_run

    @pytest.mark.asyncio
    async def test_finalize_run_status_not_found(self, status_manager, mock_db):
        """Test finalizing non-existent run returns None."""
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Try to finalize non-existent run
        result = await status_manager.finalize_run_status_if_needed(
            "nonexistent",
            "passed"
        )

        # Should return None without error
        assert result is None
