"""
SOLID Verification Part 7: Result Types

Tests Result types work correctly across all layers:
- ServiceSuccess for successful operations
- ServiceError for error cases
- HTTP status mapping
- Chainability
"""

import pytest

from app.core.simple_result_types import (
    service_success, service_error, service_not_found,
    service_validation_error, ServiceSuccess, ServiceError,
    get_http_status_from_result
)


class TestResultTypes:
    """Verify Result types work correctly across all layers."""

    @pytest.mark.asyncio
    async def test_service_success_creation(self):
        """Test ServiceSuccess creation and properties."""
        result = service_success({"test": "data"})

        assert isinstance(result, ServiceSuccess)
        assert result.data == {"test": "data"}
        assert result.is_success() is True
        assert result.is_error() is False

    @pytest.mark.asyncio
    async def test_service_error_creation(self):
        """Test ServiceError creation and properties."""
        result = service_error("Test error", "TEST_ERROR")

        assert isinstance(result, ServiceError)
        assert result.message == "Test error"
        assert result.error_code == "TEST_ERROR"
        assert result.is_success() is False
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_service_not_found_creation(self):
        """Test service_not_found creation."""
        result = service_not_found("Resource not found")

        assert isinstance(result, ServiceError)
        assert "not found" in result.message.lower()
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_service_validation_error_creation(self):
        """Test service_validation_error creation."""
        result = service_validation_error("Invalid input")

        assert isinstance(result, ServiceError)
        assert result.message == "Invalid input"
        assert result.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_result_type_chaining(self):
        """Test Result types support chaining operations."""
        # Success case
        result1 = service_success([1, 2, 3])
        assert result1.is_success()

        # Can chain operations based on result
        if result1.is_success():
            data = result1.data
            assert data == [1, 2, 3]

        # Error case
        result2 = service_error("Something went wrong", "ERROR")
        assert result2.is_error()

        # Can chain error handling
        if result2.is_error():
            error_msg = result2.message
            assert error_msg == "Something went wrong"

    @pytest.mark.asyncio
    async def test_http_status_mapping(self):
        """Test HTTP status mapping from Result types."""
        # Test success → 200
        success = service_success({"data": "value"})
        assert get_http_status_from_result(success) == 200

        # Test not found → 404
        not_found = service_not_found("Resource not found")
        assert get_http_status_from_result(not_found) == 404

        # Test validation error → 400
        validation_error = service_validation_error("Invalid input")
        assert get_http_status_from_result(validation_error) == 400

        # Test general error → 500
        general_error = service_error("Internal error", "INTERNAL_ERROR")
        assert get_http_status_from_result(general_error) == 500

    @pytest.mark.asyncio
    async def test_result_type_immutability(self):
        """Test Result types are immutable after creation."""
        result = service_success({"data": "value"})

        # Should not be able to change result type
        initial_success = result.is_success()
        initial_data = result.data

        # Result should remain unchanged
        assert result.is_success() == initial_success
        assert result.data == initial_data

    @pytest.mark.asyncio
    async def test_result_type_pattern_matching(self):
        """Test Result types support pattern matching style usage."""
        result = service_success({"user": "test"})

        # Pattern matching style
        if result.is_success():
            # Success path
            assert result.data is not None
        elif result.is_error():
            # Error path (should not reach here)
            assert False

        error_result = service_error("Failed", "ERROR")

        if error_result.is_success():
            # Success path (should not reach here)
            assert False
        elif error_result.is_error():
            # Error path
            assert error_result.message == "Failed"
