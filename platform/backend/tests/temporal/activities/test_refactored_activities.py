"""
Integration tests for refactored test activities.

Tests the refactored activities with database integration.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.temporal.activities.test_activities_refactored import (
    PrepareTestActivity,
    BrowserAutomationActivity,
    SaveResultsActivity,
    MarkRunFailedActivity,
    PrepareTestInput,
    BrowserAutomationInput,
    SaveResultsInput,
    MarkRunFailedInput,
)


class TestPrepareTestActivity:
    """Test PrepareTestActivity implementation."""

    @pytest.mark.asyncio
    async def test_validate_input_success(self):
        """Test successful input validation."""
        activity = PrepareTestActivity()

        input_data = PrepareTestInput(
            test_definition_id="123",
            run_id="run-123",
            environment={"key": "value"},
        )

        result = await activity.validate_input(input_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_test_definition_id(self):
        """Test validation fails without test_definition_id."""
        activity = PrepareTestActivity()

        input_data = PrepareTestInput(
            test_definition_id="",  # Empty
            run_id="run-123",
        )

        with pytest.raises(ValueError, match="test_definition_id is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_validate_input_missing_run_id(self):
        """Test validation fails without run_id."""
        activity = PrepareTestActivity()

        input_data = PrepareTestInput(
            test_definition_id="123",
            run_id="",  # Empty
        )

        with pytest.raises(ValueError, match="run_id is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_validate_input_invalid_test_definition_id(self):
        """Test validation fails with invalid test_definition_id format."""
        activity = PrepareTestActivity()

        input_data = PrepareTestInput(
            test_definition_id="not-a-number",
            run_id="run-123",
        )

        with pytest.raises(ValueError, match="Invalid test_definition_id"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_execute_impl_with_mock_db(self):
        """Test execution with mocked database."""
        activity = PrepareTestActivity()

        input_data = PrepareTestInput(
            test_definition_id="123",
            run_id="run-123",
            environment={"env": "test"},
        )

        # Mock the database operations
        mock_test_def = Mock()
        mock_test_def.id = 123
        mock_test_def.url = "https://example.com"
        mock_test_def.test_goal = "Test goal"
        mock_test_def.execution_mode = "script"
        mock_test_def.playwright_script = "script content"
        mock_test_def.script_status = "approved"

        with patch('app.temporal.activities.test_activities_refactored.run_with_session') as mock_session:
            async def mock_db_func(db):
                return PrepareTestOutput(
                    test_definition_id="123",
                    run_id="run-123",
                    url="https://example.com",
                    test_goal="Test goal",
                    test_steps=[],
                    environment={"env": "test"},
                    mode="execute_only",
                    execution_mode="script",
                    playwright_script="script content",
                    script_status="approved",
                )

            mock_session.return_value = await mock_db_func(None)

            output = await activity.execute_impl(input_data)

            assert output.test_definition_id == "123"
            assert output.url == "https://example.com"
            assert output.execution_mode == "script"


class TestBrowserAutomationActivity:
    """Test BrowserAutomationActivity implementation."""

    @pytest.mark.asyncio
    async def test_validate_input_success(self):
        """Test successful input validation."""
        activity = BrowserAutomationActivity()

        input_data = BrowserAutomationInput(
            run_id="run-123",
            test_definition_id="123",
            url="https://example.com",
            test_goal="Test",
            test_steps=[],
            environment={},
            mode="execute_only",
        )

        result = await activity.validate_input(input_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_run_id(self):
        """Test validation fails without run_id."""
        activity = BrowserAutomationActivity()

        input_data = BrowserAutomationInput(
            run_id="",  # Empty
            test_definition_id="123",
            url="https://example.com",
            test_goal="Test",
            test_steps=[],
            environment={},
            mode="execute_only",
        )

        with pytest.raises(ValueError, match="run_id is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_execute_impl_with_mock_playwright(self):
        """Test execution with mocked Playwright."""
        activity = BrowserAutomationActivity()

        input_data = BrowserAutomationInput(
            run_id="run-123",
            test_definition_id="123",
            url="https://example.com",
            test_goal="Test goal",
            test_steps=[],
            environment={},
            mode="execute_only",
            execution_mode="script",
            playwright_script="script content",
            script_status="approved",
        )

        # Mock Playwright and strategy factory
        with patch('app.temporal.activities.test_activities_refactored.async_playwright') as mock_playwright, \
             patch('app.temporal.activities.test_activities_refactored.get_execution_strategy_factory') as mock_factory:

            # Setup mocks
            mock_p = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_p

            mock_browser = AsyncMock()
            mock_p.chromium.launch.return_value = mock_browser

            mock_context = AsyncMock()
            mock_browser.new_context.return_value = mock_context

            mock_page = AsyncMock()
            mock_context.new_page.return_value = mock_page

            # Mock strategy execution result
            mock_result = Mock()
            mock_result.run_id = "run-123"
            mock_result.test_definition_id = "123"
            mock_result.status = "passed"
            mock_result.test_cases = []
            mock_result.error = None
            mock_result.start_time = 1000000
            mock_result.end_time = 2000000
            mock_result.total_duration = 1000000
            mock_result.total_tests = 1
            mock_result.passed = 1
            mock_result.failed = 0
            mock_result.skipped = 0

            mock_strategy_factory = Mock()
            mock_strategy_factory.execute_with_strategy = AsyncMock(return_value=mock_result)
            mock_factory.return_value = mock_strategy_factory

            output = await activity.execute_impl(input_data)

            assert output.run_id == "run-123"
            assert output.status == "passed"
            assert output.total_tests == 1
            assert output.passed == 1
            assert output.failed == 0


class TestSaveResultsActivity:
    """Test SaveResultsActivity implementation."""

    @pytest.mark.asyncio
    async def test_validate_input_success(self):
        """Test successful input validation."""
        activity = SaveResultsActivity()

        input_data = SaveResultsInput(
            run_id="run-123",
            results={"status": "passed"},
        )

        result = await activity.validate_input(input_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_run_id(self):
        """Test validation fails without run_id."""
        activity = SaveResultsActivity()

        input_data = SaveResultsInput(
            run_id="",  # Empty
            results={"status": "passed"},
        )

        with pytest.raises(ValueError, match="run_id is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_validate_input_missing_results(self):
        """Test validation fails without results."""
        activity = SaveResultsActivity()

        input_data = SaveResultsInput(
            run_id="run-123",
            results=None,  # Empty
        )

        with pytest.raises(ValueError, match="results is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_execute_impl_with_mock_service(self):
        """Test execution with mocked ExecutionService."""
        activity = SaveResultsActivity()

        input_data = SaveResultsInput(
            run_id="run-123",
            results={"status": "passed", "total_tests": 1},
        )

        with patch('app.temporal.activities.test_activities_refactored.run_with_session') as mock_session:
            mock_session.return_value = None

            output = await activity.execute_impl(input_data)

            # SaveResultsActivity returns None
            assert output is None


class TestMarkRunFailedActivity:
    """Test MarkRunFailedActivity implementation."""

    @pytest.mark.asyncio
    async def test_validate_input_success(self):
        """Test successful input validation."""
        activity = MarkRunFailedActivity()

        input_data = MarkRunFailedInput(
            run_id="run-123",
            error_message="Test error",
        )

        result = await activity.validate_input(input_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_run_id(self):
        """Test validation fails without run_id."""
        activity = MarkRunFailedActivity()

        input_data = MarkRunFailedInput(
            run_id="",  # Empty
            error_message="Test error",
        )

        with pytest.raises(ValueError, match="run_id is required"):
            await activity.validate_input(input_data)

    @pytest.mark.asyncio
    async def test_execute_impl_with_mock_service(self):
        """Test execution with mocked ExecutionService."""
        activity = MarkRunFailedActivity()

        input_data = MarkRunFailedInput(
            run_id="run-123",
            error_message="Test error",
        )

        with patch('app.temporal.activities.test_activities_refactored.run_with_session') as mock_session:
            mock_session.return_value = None

            output = await activity.execute_impl(input_data)

            # MarkRunFailedActivity returns None
            assert output is None


class TestBackwardCompatibility:
    """Test backward compatibility with existing workflows."""

    @pytest.mark.asyncio
    async def test_prepare_test_wrapper(self):
        """Test that wrapper function maintains backward compatibility."""
        from app.temporal.activities.test_activities_refactored import prepare_test

        input_data = PrepareTestInput(
            test_definition_id="123",
            run_id="run-123",
            environment={},
        )

        with patch('app.temporal.activities.test_activities_refactored.run_with_session'):
            # Should not raise exception
            output = await prepare_test(input_data)
            assert output is not None

    @pytest.mark.asyncio
    async def test_save_results_wrapper(self):
        """Test that save_results wrapper maintains backward compatibility."""
        from app.temporal.activities.test_activities_refactored import save_results

        input_data = SaveResultsInput(
            run_id="run-123",
            results={"status": "passed"},
        )

        with patch('app.temporal.activities.test_activities_refactored.run_with_session'):
            # Should not raise exception
            await save_results(input_data)

    @pytest.mark.asyncio
    async def test_mark_run_failed_wrapper(self):
        """Test that mark_run_failed wrapper maintains backward compatibility."""
        from app.temporal.activities.test_activities_refactored import mark_run_failed

        input_data = MarkRunFailedInput(
            run_id="run-123",
            error_message="Test error",
        )

        with patch('app.temporal.activities.test_activities_refactored.run_with_session'):
            # Should not raise exception
            await mark_run_failed(input_data)
