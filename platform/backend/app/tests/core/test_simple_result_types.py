"""
Tests for Simple Result Wrapper Types

Tests for lightweight, easy-to-use result types.
"""

import pytest
from typing import Dict, Any

from app.core.simple_result_types import (
    Result, Success, Error,
    ServiceResult, ServiceSuccess, ServiceError,
    ResultStatus,
    success, error, not_found, validation_error, permission_denied,
    service_success, service_error, service_not_found,
    service_validation_error, service_permission_denied,
    is_success, is_error, fold, map_result, get_or_else, get_or_raise
)


class TestBasicResultTypes:
    """Test basic result type functionality."""

    def test_success_creation(self):
        """Test creating success result."""
        result = Success(data="test data")

        assert result.is_success() is True
        assert result.is_error() is False
        assert result.get_data() == "test data"
        assert result.get_error() is None

    def test_success_with_no_data(self):
        """Test success result without data."""
        result = Success()

        assert result.is_success() is True
        assert result.get_data() is None

    def test_error_creation(self):
        """Test creating error result."""
        result = Error(message="Test error", code="TEST_ERROR")

        assert result.is_success() is False
        assert result.is_error() is True
        assert result.get_error() == "Test error"
        assert result.code == "TEST_ERROR"
        assert result.get_data() is None

    def test_error_with_details(self):
        """Test error result with details."""
        details = {"field": "value", "count": 10}
        result = Error(message="Error with details", code="ERROR", details=details)

        assert result.is_error() is True
        assert result.details == details

    def test_success_type_guard(self):
        """Test success type guard function."""
        result: Result = Success(data="test")

        if is_success(result):
            # Type should be narrowed to Success here
            assert result.get_data() == "test"
            assert result.is_success()
        else:
            pytest.fail("Result should be identified as success")

    def test_error_type_guard(self):
        """Test error type guard function."""
        result: Result = Error(message="test error")

        if is_error(result):
            # Type should be narrowed to Error here
            assert result.get_error() == "test error"
            assert result.is_error()
        else:
            pytest.fail("Result should be identified as error")


class TestHelperFunctions:
    """Test result helper functions."""

    def test_success_helper(self):
        """Test success creation helper."""
        result = success("test data")

        assert isinstance(result, Success)
        assert result.get_data() == "test data"

    def test_success_helper_no_data(self):
        """Test success helper without data."""
        result = success()

        assert isinstance(result, Success)
        assert result.get_data() is None

    def test_error_helper(self):
        """Test error creation helper."""
        result = error("Test error", "TEST_CODE")

        assert isinstance(result, Error)
        assert result.get_error() == "Test error"
        assert result.code == "TEST_CODE"

    def test_not_found_helper(self):
        """Test not found helper."""
        result = not_found("User", "123")

        assert isinstance(result, Error)
        assert result.code == "NOT_FOUND"
        assert "User not found" in result.get_error()
        assert "123" in result.get_error()

    def test_not_found_helper_no_identifier(self):
        """Test not found helper without identifier."""
        result = not_found("Resource")

        assert isinstance(result, Error)
        assert "Resource not found" in result.get_error()

    def test_validation_error_helper(self):
        """Test validation error helper."""
        field_errors = {"email": "Invalid email format", "age": "Must be positive"}
        result = validation_error("Validation failed", field_errors)

        assert isinstance(result, Error)
        assert result.code == "VALIDATION_ERROR"
        assert result.details["field_errors"] == field_errors

    def test_permission_denied_helper(self):
        """Test permission denied helper."""
        result = permission_denied("Access denied", "admin:write")

        assert isinstance(result, Error)
        assert result.code == "PERMISSION_DENIED"
        assert result.details["required_permission"] == "admin:write"

    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        result = error("Test error", "TEST_CODE", {"key": "value"})

        error_dict = result.to_dict()
        assert error_dict["status"] == "error"
        assert error_dict["message"] == "Test error"
        assert error_dict["code"] == "TEST_CODE"
        assert error_dict["details"]["key"] == "value"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_fold_success(self):
        """Test fold with success result."""
        result = Success(data=10)

        output = fold(
            result,
            on_success=lambda x: x * 2,
            on_error=lambda e: 0
        )

        assert output == 20

    def test_fold_error(self):
        """Test fold with error result."""
        result = Error(message="Failed")

        output = fold(
            result,
            on_success=lambda x: x * 2,
            on_error=lambda e: -1
        )

        assert output == -1

    def test_map_result_success(self):
        """Test map_result with success."""
        result = Success(data=5)

        mapped = map_result(result, lambda x: x * 3)

        assert isinstance(mapped, Success)
        assert mapped.get_data() == 15

    def test_map_result_error(self):
        """Test map_result with error."""
        result = Error(message="Original error")

        mapped = map_result(result, lambda x: x * 3)

        assert isinstance(mapped, Error)
        assert mapped.get_error() == "Original error"

    def test_map_result_exception(self):
        """Test map_result with exception in function."""
        result = Success(data="not a number")

        mapped = map_result(result, lambda x: int(x) * 2)

        assert isinstance(mapped, Error)
        assert "invalid literal" in mapped.get_error().lower()

    def test_get_or_else_success(self):
        """Test get_or_else with success."""
        result = Success(data="actual value")

        value = get_or_else(result, "default")

        assert value == "actual value"

    def test_get_or_else_error(self):
        """Test get_or_else with error."""
        result = Error(message="Failed")

        value = get_or_else(result, "default")

        assert value == "default"

    def test_get_or_raise_success(self):
        """Test get_or_raise with success."""
        result = Success(data="success data")

        value = get_or_raise(result)

        assert value == "success data"

    def test_get_or_raise_error(self):
        """Test get_or_raise with error."""
        result = Error(message="Operation failed")

        with pytest.raises(ValueError, match="Operation failed"):
            get_or_raise(result)

    def test_get_or_raise_custom_exception(self):
        """Test get_or_raise with custom exception."""
        result = Error(message="Custom error")

        with pytest.raises(RuntimeError, match="Custom error"):
            get_or_raise(result, exception=RuntimeError)


class TestServiceResultTypes:
    """Test service-level result types."""

    def test_service_success_creation(self):
        """Test creating service success."""
        result = ServiceSuccess(data={"id": 123})

        assert result.is_success() is True
        assert result.get_data() == {"id": 123}
        assert result.get_http_status() == 200

    def test_service_success_with_metadata(self):
        """Test service success with metadata."""
        metadata = {"version": "1.0", "count": 5}
        result = ServiceSuccess(data="success", metadata=metadata)

        assert result.is_success() is True
        assert result.metadata == metadata

    def test_service_error_creation(self):
        """Test creating service error."""
        result = ServiceError(message="Service failed", error_code="OPERATION_FAILED")

        assert result.is_error() is True
        assert result.get_http_status() == 500
        assert result.error_code == "OPERATION_FAILED"

    def test_service_error_http_status_mapping(self):
        """Test HTTP status code mapping for different errors."""
        not_found = ServiceError(message="Not found", error_code="NOT_FOUND")
        assert not_found.get_http_status() == 404

        conflict = ServiceError(message="Conflict", error_code="CONFLICT")
        assert conflict.get_http_status() == 409

        validation = ServiceError(message="Invalid", error_code="VALIDATION_ERROR")
        assert validation.get_http_status() == 400

        permission = ServiceError(message="Denied", error_code="PERMISSION_DENIED")
        assert permission.get_http_status() == 403

    def test_service_error_to_dict(self):
        """Test converting service error to dict."""
        result = ServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"}
        )

        error_dict = result.to_dict()
        assert error_dict["status"] == "error"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["http_status"] == 500


class TestServiceHelperFunctions:
    """Test service-level helper functions."""

    def test_service_success_helper(self):
        """Test service success helper."""
        result = service_success({"id": 123}, version="1.0")

        assert isinstance(result, ServiceSuccess)
        assert result.get_data() == {"id": 123}
        assert result.metadata["version"] == "1.0"

    def test_service_error_helper(self):
        """Test service error helper."""
        result = service_error("Service failed", "SERVICE_ERROR")

        assert isinstance(result, ServiceError)
        assert result.get_error() == "Service failed"
        assert result.error_code == "SERVICE_ERROR"

    def test_service_not_found_helper(self):
        """Test service not found helper."""
        result = service_not_found("TestResource", "456")

        assert isinstance(result, ServiceError)
        assert result.error_code == "NOT_FOUND"
        assert result.get_http_status() == 404
        assert result.details["resource"] == "TestResource"
        assert result.details["identifier"] == "456"

    def test_service_validation_error_helper(self):
        """Test service validation error helper."""
        field_errors = {"name": "Required", "email": "Invalid format"}
        result = service_validation_error("Validation failed", field_errors)

        assert isinstance(result, ServiceError)
        assert result.error_code == "VALIDATION_ERROR"
        assert result.get_http_status() == 400
        assert result.details["field_errors"] == field_errors

    def test_service_permission_denied_helper(self):
        """Test service permission denied helper."""
        result = service_permission_denied("Admin access required", "admin:write")

        assert isinstance(result, ServiceError)
        assert result.error_code == "PERMISSION_DENIED"
        assert result.get_http_status() == 403
        assert result.details["required_permission"] == "admin:write"


class TestResultTypeSafety:
    """Test type safety and mypy compatibility."""

    def test_generic_success_type(self):
        """Test generic Success with specific type."""
        result: Success[int] = Success(data=42)
        value: int = result.get_data()

        assert value == 42
        assert isinstance(value, int)

    def test_generic_string_type(self):
        """Test generic Success with string type."""
        result: Success[str] = Success(data="test string")
        value: str = result.get_data()

        assert value == "test string"
        assert isinstance(value, str)

    def test_generic_dict_type(self):
        """Test generic Success with dict type."""
        data = {"key": "value", "count": 10}
        result: Success[Dict[str, Any]] = Success(data=data)
        value: Dict[str, Any] = result.get_data()

        assert value == data
        assert isinstance(value, dict)

    def test_error_with_generic_type(self):
        """Test Error with generic type."""
        result: Error[str] = Error(message="Error occurred")

        assert result.is_error()
        error: str = result.get_error()
        assert error == "Error occurred"


class TestResultPolymorphism:
    """Test polymorphic behavior of result types."""

    def test_result_base_class(self):
        """Test using Result as base class type."""
        def process_result(result: Result) -> str:
            if result.is_success():
                return f"Success: {result.get_data()}"
            else:
                return f"Error: {result.get_error()}"

        success_result: Result = Success(data="test")
        error_result: Result = Error(message="failed")

        assert process_result(success_result) == "Success: test"
        assert process_result(error_result) == "Error: failed"

    def test_service_result_base_class(self):
        """Test using ServiceResult as base class type."""
        def process_service_result(result: ServiceResult) -> int:
            return result.get_http_status()

        success = ServiceSuccess(data="test")
        error = ServiceError(message="failed", error_code="NOT_FOUND")

        assert process_service_result(success) == 200
        assert process_service_result(error) == 404


class TestErrorHandlingPatterns:
    """Test common error handling patterns."""

    def test_chained_operations(self):
        """Test chaining multiple operations."""
        result = success(10)
        result = map_result(result, lambda x: x * 2)
        result = map_result(result, lambda x: x + 5)

        assert result.is_success()
        assert result.get_data() == 25

    def test_chained_with_error(self):
        """Test chaining operations that fails."""
        result = success(10)
        result = map_result(result, lambda x: x * 2)
        result = map_result(result, lambda x: 1 / 0)  # Division by zero

        assert result.is_error()
        assert "division by zero" in result.get_error()

    def test_short_circuit_on_error(self):
        """Test that operations short-circuit on error."""
        error_result = error("Initial error")
        result = map_result(error_result, lambda x: x * 2)

        assert result.is_error()
        assert result.get_error() == "Initial error"

    def test_default_values_pattern(self):
        """Test using default values for error cases."""
        result = error("Failed")
        value = get_or_else(result, default_value=42)

        assert value == 42

    def test_error_recovery_pattern(self):
        """Test error recovery pattern."""
        def risky_operation(value: int) -> Result:
            if value < 0:
                return error("Negative values not allowed")
            return success(value * 2)

        def recover(result: Result) -> Result:
            if result.is_error():
                return success(0)  # Recovery value
            return result

        result1 = risky_operation(5)
        result1 = recover(result1)
        assert result1.get_data() == 10

        result2 = risky_operation(-1)
        result2 = recover(result2)
        assert result2.get_data() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
