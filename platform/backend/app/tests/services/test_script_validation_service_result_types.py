"""
Tests for ScriptValidationService with Result wrapper types.

Tests the migrated Result-based methods to ensure proper error handling,
type safety, and backward compatibility.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestScriptValidationServiceResultTypes:
    """Test suite for ScriptValidationService Result-based methods."""

    @pytest.fixture
    def validation_service(self):
        """Create ScriptValidationService instance."""
        from app.services.script_validation_service import ScriptValidationService
        return ScriptValidationService(headless=True, timeout=60)

    @pytest.fixture
    def sample_script(self):
        """Sample Playwright script."""
        return """
async function run(page) {
    await page.goto('https://example.com');
    return { status: 'passed', step_results: [] };
}
"""

    @pytest.fixture
    def failing_script(self):
        """Sample failing Playwright script."""
        return """
async function run(page) {
    throw new Error('Test failed');
}
"""

    # ==================== validate_script_v2 tests ====================

    @pytest.mark.asyncio
    async def test_validate_script_v2_success(self, validation_service, sample_script):
        """Test successful script validation."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [
                {"name": "Navigate", "status": "passed"}
            ],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_v2(sample_script)

            assert result.is_success()
            data = result.get_data()
            assert data["status"] == "passed"
            assert len(data["step_results"]) == 1
            assert result.metadata["headless"] is True

    @pytest.mark.asyncio
    async def test_validate_script_v2_with_url(self, validation_service, sample_script):
        """Test script validation with URL navigation."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_v2(
                sample_script,
                url="https://example.com"
            )

            assert result.is_success()
            assert result.get_data()["status"] == "passed"

    @pytest.mark.asyncio
    async def test_validate_script_v2_empty_script(self, validation_service):
        """Test validate_script_v2 with empty script."""
        result = await validation_service.validate_script_v2("")

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "cannot be empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_script_v2_whitespace_only(self, validation_service):
        """Test validate_script_v2 with whitespace-only script."""
        result = await validation_service.validate_script_v2("   \n\t   ")

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_validate_script_v2_execution_error(self, validation_service, sample_script):
        """Test validate_script_v2 with execution error."""
        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(side_effect=Exception("Browser launch failed"))):
            result = await validation_service.validate_script_v2(sample_script)

            assert result.is_error()
            assert result.error_code == "EXECUTION_ERROR"
            assert "Browser launch failed" in result.message

    @pytest.mark.asyncio
    async def test_validate_script_v2_script_error(self, validation_service, failing_script):
        """Test validate_script_v2 with script that returns error status."""
        mock_exec_result = {
            "status": "failed",
            "step_results": [],
            "error": "Test failed"
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_v2(failing_script)

            # Script execution succeeds but returns error status
            assert result.is_success()
            assert result.get_data()["status"] == "failed"
            assert result.get_data()["error"] == "Test failed"

    # ==================== validate_script_with_metadata_v2 tests ====================

    @pytest.mark.asyncio
    async def test_validate_script_with_metadata_v2_success(self, validation_service, sample_script):
        """Test script validation with metadata merge."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_with_metadata_v2(
                sample_script,
                existing_metadata={"version": "1.0"}
            )

            assert result.is_success()
            data = result.get_data()
            assert "validation_result" in data
            assert "updated_metadata" in data
            assert data["updated_metadata"]["version"] == "1.0"
            assert data["updated_metadata"]["validation_status"] == "passed"

    @pytest.mark.asyncio
    async def test_validate_script_with_metadata_v2_no_existing_metadata(self, validation_service, sample_script):
        """Test script validation with metadata without existing metadata."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_with_metadata_v2(sample_script)

            assert result.is_success()
            data = result.get_data()
            assert data["updated_metadata"]["validation_status"] == "passed"
            assert result.metadata["has_existing_metadata"] is False

    @pytest.mark.asyncio
    async def test_validate_script_with_metadata_v2_validation_error(self, validation_service):
        """Test validate_script_with_metadata_v2 with validation error."""
        result = await validation_service.validate_script_with_metadata_v2(
            "",
            existing_metadata={"version": "1.0"}
        )

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_validate_script_with_metadata_v2_execution_error(self, validation_service, sample_script):
        """Test validate_script_with_metadata_v2 with execution error."""
        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(side_effect=Exception("Execution failed"))):
            result = await validation_service.validate_script_with_metadata_v2(sample_script)

            assert result.is_error()
            assert result.error_code == "EXECUTION_ERROR"

    # ==================== determine_script_status_v2 tests ====================

    def test_determine_script_status_v2_passed(self, validation_service):
        """Test determine_script_status_v2 with passed status."""
        validation_result = {"status": "passed", "error": None}

        result = validation_service.determine_script_status_v2(validation_result)

        assert result.is_success()
        assert result.get_data() == "validated"
        assert result.metadata["validation_status"] == "passed"

    def test_determine_script_status_v2_failed(self, validation_service):
        """Test determine_script_status_v2 with failed status."""
        validation_result = {"status": "failed", "error": "Test failed"}

        result = validation_service.determine_script_status_v2(validation_result)

        assert result.is_success()
        assert result.get_data() == "draft"
        assert result.metadata["validation_status"] == "failed"

    def test_determine_script_status_v2_error_status(self, validation_service):
        """Test determine_script_status_v2 with error status."""
        validation_result = {"status": "error", "error": "Syntax error"}

        result = validation_service.determine_script_status_v2(validation_result)

        assert result.is_success()
        assert result.get_data() == "draft"

    def test_determine_script_status_v2_missing_status(self, validation_service):
        """Test determine_script_status_v2 with missing status."""
        validation_result = {"error": "No status"}

        result = validation_service.determine_script_status_v2(validation_result)

        assert result.is_success()
        assert result.get_data() == "draft"  # Defaults to "failed"

    def test_determine_script_status_v2_empty_result(self, validation_service):
        """Test determine_script_status_v2 with empty result."""
        result = validation_service.determine_script_status_v2({})

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"
        assert "cannot be empty" in result.message.lower()

    def test_determine_script_status_v2_none_result(self, validation_service):
        """Test determine_script_status_v2 with None result."""
        result = validation_service.determine_script_status_v2(None)

        assert result.is_error()
        assert result.error_code == "VALIDATION_ERROR"

    # ==================== Backward compatibility tests ====================

    @pytest.mark.asyncio
    async def test_legacy_validate_script_still_works(self, validation_service, sample_script):
        """Test that legacy validate_script method still works."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script(sample_script)

            assert isinstance(result, dict)
            assert result["status"] == "passed"
            # Not a ServiceSuccess - it's the direct dict
            assert not isinstance(result, (ServiceSuccess, ServiceError))

    @pytest.mark.asyncio
    async def test_legacy_validate_script_raises_on_empty(self, validation_service):
        """Test that legacy validate_script raises ValueError on empty script."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await validation_service.validate_script("")

    @pytest.mark.asyncio
    async def test_legacy_validate_script_with_metadata_still_works(self, validation_service, sample_script):
        """Test that legacy validate_script_with_metadata method still works."""
        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            result = await validation_service.validate_script_with_metadata(
                sample_script,
                existing_metadata={"version": "1.0"}
            )

            assert isinstance(result, dict)
            assert "validation_result" in result
            assert "updated_metadata" in result
            # Not a ServiceSuccess - it's the direct dict
            assert not isinstance(result, (ServiceSuccess, ServiceError))

    def test_legacy_determine_script_status_still_works(self, validation_service):
        """Test that legacy determine_script_status method still works."""
        validation_result = {"status": "passed"}

        result = validation_service.determine_script_status(validation_result)

        assert isinstance(result, str)
        assert result == "validated"
        # Not a ServiceSuccess - it's the direct string
        assert not isinstance(result, (ServiceSuccess, ServiceError))


class TestScriptValidationServiceIntegration:
    """Integration tests for ScriptValidationService Result methods."""

    @pytest.mark.asyncio
    async def test_full_validation_workflow(self):
        """Test complete validation workflow with Result types."""
        from app.services.script_validation_service import ScriptValidationService

        service = ScriptValidationService(headless=True, timeout=60)
        script = "async function run(page) { return { status: 'passed' }; }"

        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            # Validate script
            validate_result = await service.validate_script_v2(script)
            assert validate_result.is_success()

            # Validate with metadata
            metadata_result = await service.validate_script_with_metadata_v2(
                script,
                existing_metadata={"version": "1.0"}
            )
            assert metadata_result.is_success()

            # Determine status
            validation_data = validate_result.get_data()
            status_result = service.determine_script_status_v2(validation_data)
            assert status_result.is_success()
            assert status_result.get_data() == "validated"

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery across validation operations."""
        from app.services.script_validation_service import ScriptValidationService

        service = ScriptValidationService(headless=True, timeout=60)

        # Test validation error
        result = await service.validate_script_v2("")
        assert result.is_error()
        assert result.get_http_status() == 400

        # Test metadata error propagation
        metadata_result = await service.validate_script_with_metadata_v2("")
        assert metadata_result.is_error()
        assert metadata_result.get_http_status() == 400

    @pytest.mark.asyncio
    async def test_chained_result_operations(self):
        """Test chaining multiple Result-based operations."""
        from app.services.script_validation_service import ScriptValidationService

        service = ScriptValidationService(headless=True, timeout=60)
        script = "async function run(page) { return { status: 'passed' }; }"

        mock_exec_result = {
            "status": "passed",
            "step_results": [],
            "error": None
        }

        with patch('app.services.script_validation_service.execute_script', new=AsyncMock(return_value=mock_exec_result)):
            # Chain: validate -> determine status
            validate_result = await service.validate_script_v2(script)

            if validate_result.is_success():
                validation_data = validate_result.get_data()
                status_result = service.determine_script_status_v2(validation_data)

                assert status_result.is_success()
                assert status_result.get_data() == "validated"
            else:
                assert False, "Validation should have succeeded"


# Import ServiceSuccess and ServiceError for type checking
from app.core.simple_result_types import ServiceSuccess, ServiceError
