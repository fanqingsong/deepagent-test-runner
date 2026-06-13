"""
Tests for Script Validation Service

Unit tests for the ScriptValidationService class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import async_playwright

from app.services.script_validation_service import ScriptValidationService


class TestScriptValidationService:
    """Test suite for ScriptValidationService."""

    @pytest.fixture
    def validation_service(self):
        """Create a ScriptValidationService instance."""
        return ScriptValidationService(headless=True, timeout=120)

    @pytest.mark.asyncio
    async def test_validate_script_success(self, validation_service):
        """Test successful script validation."""
        mock_script = "async def run_test(page): return {'status': 'passed'}"
        mock_url = "https://example.com"

        with patch('app.services.script_validation_service.async_playwright') as mock_playwright:
            # Setup mock browser
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.return_value.__aenter__.return_value = AsyncMock(
                chromium=AsyncMock(launch=AsyncMock(return_value=mock_browser))
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            with patch('app.services.script_validation_service.execute_script') as mock_execute:
                mock_execute.return_value = {
                    "status": "passed",
                    "step_results": [{"step": "test", "result": "passed"}],
                    "error": None
                }

                result = await validation_service.validate_script(mock_script, mock_url)

                assert result["status"] == "passed"
                assert len(result["step_results"]) == 1
                assert result["error"] is None
                mock_page.goto.assert_called_once_with(
                    mock_url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

    @pytest.mark.asyncio
    async def test_validate_script_failure(self, validation_service):
        """Test script validation with execution failure."""
        mock_script = "async def run_test(page): return {'status': 'failed'}"

        with patch('app.services.script_validation_service.async_playwright') as mock_playwright:
            # Setup mock browser
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.return_value.__aenter__.return_value = AsyncMock(
                chromium=AsyncMock(launch=AsyncMock(return_value=mock_browser))
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            with patch('app.services.script_validation_service.execute_script') as mock_execute:
                mock_execute.return_value = {
                    "status": "failed",
                    "step_results": [],
                    "error": "Element not found"
                }

                result = await validation_service.validate_script(mock_script)

                assert result["status"] == "failed"
                assert result["error"] == "Element not found"

    @pytest.mark.asyncio
    async def test_validate_script_empty_script_raises_error(self, validation_service):
        """Test that empty script raises ValueError."""
        with pytest.raises(ValueError, match="Script cannot be empty"):
            await validation_service.validate_script("")

        with pytest.raises(ValueError, match="Script cannot be empty"):
            await validation_service.validate_script("   ")

    @pytest.mark.asyncio
    async def test_validate_script_without_url(self, validation_service):
        """Test script validation without navigating to URL."""
        mock_script = "async def run_test(page): return {'status': 'passed'}"

        with patch('app.services.script_validation_service.async_playwright') as mock_playwright:
            # Setup mock browser
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.return_value.__aenter__.return_value = AsyncMock(
                chromium=AsyncMock(launch=AsyncMock(return_value=mock_browser))
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            with patch('app.services.script_validation_service.execute_script') as mock_execute:
                mock_execute.return_value = {
                    "status": "passed",
                    "step_results": [],
                    "error": None
                }

                result = await validation_service.validate_script(mock_script, url=None)

                assert result["status"] == "passed"
                # Verify goto was not called when no URL provided
                mock_page.goto.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_script_with_metadata(self, validation_service):
        """Test script validation with existing metadata."""
        mock_script = "async def run_test(page): return {'status': 'passed'}"
        existing_metadata = {"previous_runs": 5, "last_run": "2024-01-01"}

        with patch('app.services.script_validation_service.async_playwright') as mock_playwright:
            # Setup mock browser
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.return_value.__aenter__.return_value = AsyncMock(
                chromium=AsyncMock(launch=AsyncMock(return_value=mock_browser))
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            with patch('app.services.script_validation_service.execute_script') as mock_execute:
                mock_execute.return_value = {
                    "status": "passed",
                    "step_results": [],
                    "error": None
                }

                result = await validation_service.validate_script_with_metadata(
                    mock_script,
                    url=None,
                    existing_metadata=existing_metadata
                )

                assert "validation_result" in result
                assert "updated_metadata" in result
                assert result["updated_metadata"]["previous_runs"] == 5
                assert result["updated_metadata"]["validation_status"] == "passed"

    def test_determine_script_status_passed(self, validation_service):
        """Test determine_script_status with passed result."""
        validation_result = {"status": "passed", "error": None}
        status = validation_service.determine_script_status(validation_result)
        assert status == "validated"

    def test_determine_script_status_failed(self, validation_service):
        """Test determine_script_status with failed result."""
        validation_result = {"status": "failed", "error": "Element not found"}
        status = validation_service.determine_script_status(validation_result)
        assert status == "draft"

    def test_determine_script_status_error(self, validation_service):
        """Test determine_script_status with error result."""
        validation_result = {"status": "error", "error": "Syntax error"}
        status = validation_service.determine_script_status(validation_result)
        assert status == "draft"
