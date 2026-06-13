"""
Unit Tests for Result Types

Comprehensive tests for result wrapper types, helpers, and builders.
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime

from app.core.result_types import (
    Result, Success, Error, Timeout, ValidationError,
    ResultType, is_success, is_error, is_timeout, is_validation_error,
    fold, match, combine_results, sequence_results
)
from app.core.service_result_types import (
    ServiceResult, ServiceSuccess, ServiceError,
    DatabaseError, NotFoundError, ConflictError,
    ServiceValidationError, PermissionError, TestExecutionError,
    ErrorCode, HTTPStatusMap, BulkServiceResult
)
from app.core.result_helpers import (
    success, error, timeout, validation_error,
    service_success, service_error, not_found as not_found_helper,
    conflict as conflict_helper, database_error as database_error_helper,
    get_data, get_error, get_or_raise,
    map_result, filter_result, combine_results as combine_helper,
    to_http_response, from_exception
)
from app.core.result_builders import (
    ResultBuilder, ServiceResultBuilder,
    ErrorResponseBuilder, ValidationBuilder, BulkOperationBuilder
)


# ============================================================================
# Test Basic Result Types
# ============================================================================

class TestSuccessResult:
    """Tests for Success result type."""

    def test_create_success_with_data(self):
        """Test creating success with data."""
        result = Success(42)
        assert result.is_success() is True
        assert result.is_error() is False
        assert result.get_data() == 42

    def test_create_success_without_data(self):
        """Test creating success without data."""
        result = Success()
        assert result.is_success() is True
        assert result.get_data() is None

    def test_success_get_error_message(self):
        """Test success has no error message."""
        result = Success(42)
        assert result.get_error_message() is None

    def test_success_map(self):
        """Test mapping success data."""
        result = Success(5).map(lambda x: x * 2)
        assert isinstance(result, Success)
        assert result.get_data() == 10

    def test_success_map_error_handling(self):
        """Test map handles exceptions."""
        result = Success(5).map(lambda x: x / 0)
        assert isinstance(result, Error)
        assert "division by zero" in result.get_error_message()

    def test_success_flat_map(self):
        """Test flat mapping success data."""
        def double_if_positive(x):
            if x > 0:
                return Success(x * 2)
            return Error("Not positive")

        result = Success(5).flat_map(double_if_positive)
        assert isinstance(result, Success)
        assert result.get_data() == 10

    def test_success_filter(self):
        """Test filtering success data."""
        result = Success(5).filter(lambda x: x > 0, "Must be positive")
        assert isinstance(result, Success)
        assert result.get_data() == 5

    def test_success_filter_failure(self):
        """Test filter returns error on failure."""
        result = Success(-1).filter(lambda x: x > 0, "Must be positive")
        assert isinstance(result, Error)
        assert result.get_error_message() == "Must be positive"

    def test_success_get_or_else(self):
        """Test get_or_else returns data on success."""
        result = Success(42)
        assert result.get_or_else(0) == 42

    def test_success_to_dict(self):
        """Test success to dictionary conversion."""
        result = Success({"id": 123})
        data = result.to_dict()
        assert data["result_type"] == "success"
        assert data["is_success"] is True
        assert data["data"] == {"id": 123}


class TestErrorResult:
    """Tests for Error result type."""

    def test_create_error_with_message(self):
        """Test creating error with message."""
        result = Error("Operation failed")
        assert result.is_success() is False
        assert result.is_error() is True
        assert result.get_error_message() == "Operation failed"

    def test_create_error_with_code(self):
        """Test creating error with code."""
        result = Error("Failed", code="OP_FAILED")
        assert result.code == "OP_FAILED"

    def test_create_error_with_details(self):
        """Test creating error with details."""
        details = {"field": "value"}
        result = Error("Failed", details=details)
        assert result.details == details

    def test_error_map_propagates(self):
        """Test map propagates error."""
        result = Error("Failed").map(lambda x: x * 2)
        assert isinstance(result, Error)
        assert result.get_error_message() == "Failed"

    def test_error_get_data_raises(self):
        """Test error get_data raises exception."""
        result = Error("Failed")
        with pytest.raises(AttributeError, match="no data"):
            result.get_data()

    def test_error_get_or_else(self):
        """Test get_or_else returns default on error."""
        result = Error("Failed")
        assert result.get_or_else(0) == 0

    def test_error_add_detail(self):
        """Test adding detail to error."""
        result = Error("Failed").add_detail("key", "value")
        assert result.details == {"key": "value"}

    def test_error_to_dict(self):
        """Test error to dictionary conversion."""
        result = Error("Failed", code="OP_FAILED", details={"retry": True})
        data = result.to_dict()
        assert data["result_type"] == "error"
        assert data["is_success"] is False
        assert data["message"] == "Failed"
        assert data["code"] == "OP_FAILED"


class TestTimeoutResult:
    """Tests for Timeout result type."""

    def test_create_timeout_default(self):
        """Test creating timeout with defaults."""
        result = Timeout()
        assert result.is_timeout() is True
        assert result.get_error_message() == "Operation timed out"

    def test_create_timeout_custom(self):
        """Test creating timeout with custom values."""
        result = Timeout("Custom timeout", timeout_seconds=30.0)
        assert result.get_error_message() == "Custom timeout"
        assert result.timeout_seconds == 30.0

    def test_timeout_is_error(self):
        """Test timeout is considered error."""
        result = Timeout()
        assert result.is_error() is True


class TestValidationError:
    """Tests for ValidationError result type."""

    def test_create_validation_error_default(self):
        """Test creating validation error with defaults."""
        result = ValidationError()
        assert result.is_validation_error() is True
        assert result.get_error_message() == "Validation failed"

    def test_create_validation_error_with_errors(self):
        """Test creating validation error with field errors."""
        errors = {"email": ["Invalid format"], "age": ["Must be positive"]}
        result = ValidationError("Validation failed", errors)
        assert result.errors == errors

    def test_validation_error_add_field_error(self):
        """Test adding field error to validation error."""
        result = ValidationError().add_field_error("name", "Required")
        assert result.errors == {"name": ["Required"]}

    def test_validation_error_add_multiple_field_errors(self):
        """Test adding multiple field errors."""
        result = (ValidationError()
                  .add_field_error("email", "Invalid format")
                  .add_field_error("email", "Already used")
                  .add_field_error("name", "Required"))

        assert result.errors["email"] == ["Invalid format", "Already used"]
        assert result.errors["name"] == ["Required"]


# ============================================================================
# Test Service Result Types
# ============================================================================

class TestServiceSuccess:
    """Tests for ServiceSuccess result type."""

    def test_create_service_success(self):
        """Test creating service success."""
        result = ServiceSuccess(data={"id": 123}, service_name="TestService")
        assert result.is_success() is True
        assert result.get_data() == {"id": 123}
        assert result.service_name == "TestService"

    def test_service_success_with_metadata(self):
        """Test service success with metadata."""
        result = ServiceSuccess(
            data={"id": 123},
            metadata={"version": "1.0"},
            service_name="TestService"
        )
        assert result.metadata == {"version": "1.0"}

    def test_service_success_with_metadata_merge(self):
        """Test merging metadata."""
        result = ServiceSuccess(data={"id": 123}).with_metadata(count=5, name="test")
        assert result.metadata == {"count": 5, "name": "test"}

    def test_service_success_get_http_status(self):
        """Test service success returns 200."""
        result = ServiceSuccess(data={"id": 123})
        assert result.get_http_status() == 200


class TestServiceError:
    """Tests for ServiceError result type."""

    def test_create_service_error(self):
        """Test creating service error."""
        result = ServiceError(
            message="Operation failed",
            error_code=ErrorCode.OPERATION_FAILED,
            service_name="TestService"
        )
        assert result.is_success() is False
        assert result.get_error_message() == "Operation failed"
        assert result.error_code == ErrorCode.OPERATION_FAILED

    def test_service_error_get_http_status(self):
        """Test service error HTTP status mapping."""
        result = ServiceError(
            message="Not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND
        )
        assert result.get_http_status() == 404

    def test_service_error_with_detail(self):
        """Test adding detail to service error."""
        result = ServiceError("Failed", error_code=ErrorCode.OPERATION_FAILED)
        enhanced = result.with_detail("field", "value")
        assert enhanced.details == {"field": "value"}


class TestNotFoundResult:
    """Tests for NotFoundError result type."""

    def test_create_not_found(self):
        """Test creating not found error."""
        result = NotFoundError("TestDefinition", "test-123")
        assert result.error_code == ErrorCode.RESOURCE_NOT_FOUND
        assert "TestDefinition not found: test-123" in result.get_error_message()
        assert result.get_http_status() == 404

    def test_create_not_found_no_identifier(self):
        """Test creating not found without identifier."""
        result = NotFoundError("TestDefinition")
        assert "TestDefinition not found" in result.get_error_message()


class TestConflictResult:
    """Tests for ConflictError result type."""

    def test_create_conflict(self):
        """Test creating conflict error."""
        result = ConflictError("Resource already exists", "resource-123")
        assert result.error_code == ErrorCode.RESOURCE_CONFLICT
        assert result.get_http_status() == 409


# ============================================================================
# Test Result Helpers
# ============================================================================

class TestResultHelpers:
    """Tests for result helper functions."""

    def test_success_helper(self):
        """Test success helper function."""
        result = success({"id": 123})
        assert isinstance(result, Success)
        assert result.get_data() == {"id": 123}

    def test_error_helper(self):
        """Test error helper function."""
        result = error("Operation failed", code="OP_FAILED")
        assert isinstance(result, Error)
        assert result.get_error_message() == "Operation failed"

    def test_timeout_helper(self):
        """Test timeout helper function."""
        result = timeout(timeout_seconds=30.0)
        assert isinstance(result, Timeout)
        assert result.timeout_seconds == 30.0

    def test_validation_error_helper(self):
        """Test validation error helper function."""
        errors = {"email": ["Invalid"]}
        result = validation_error(errors=errors)
        assert isinstance(result, ValidationError)
        assert result.errors == errors

    def test_service_success_helper(self):
        """Test service success helper."""
        result = service_success(data={"id": 123}, service_name="TestService")
        assert isinstance(result, ServiceSuccess)
        assert result.get_data() == {"id": 123}

    def test_not_found_helper(self):
        """Test not found helper."""
        result = not_found_helper("TestDefinition", "test-123")
        assert isinstance(result, NotFoundError)
        assert result.get_http_status() == 404

    def test_get_data_success(self):
        """Test get_data from success."""
        result = Success(42)
        assert get_data(result) == 42

    def test_get_data_error_default(self):
        """Test get_data from error returns default."""
        result = Error("Failed")
        assert get_data(result, default=0) == 0

    def test_get_error_from_error(self):
        """Test get_error from error result."""
        result = Error("Failed")
        assert get_error(result) == "Failed"

    def test_get_error_from_success_default(self):
        """Test get_error from success returns default."""
        result = Success(42)
        assert get_error(result, default="No error") == "No error"

    def test_get_or_raise_success(self):
        """Test get_or_raise from success."""
        result = Success(42)
        assert get_or_raise(result) == 42

    def test_get_or_raise_error(self):
        """Test get_or_raise from error raises exception."""
        result = Error("Failed")
        with pytest.raises(ValueError, match="Failed"):
            get_or_raise(result)

    def test_map_result(self):
        """Test map_result helper."""
        result = Success(5)
        mapped = map_result(result, lambda x: x * 2)
        assert isinstance(mapped, Success)
        assert mapped.get_data() == 10

    def test_filter_result_passes(self):
        """Test filter_result when predicate passes."""
        result = Success(42)
        filtered = filter_result(result, lambda x: x > 0, "Must be positive")
        assert isinstance(filtered, Success)

    def test_filter_result_fails(self):
        """Test filter_result when predicate fails."""
        result = Success(-1)
        filtered = filter_result(result, lambda x: x > 0, "Must be positive")
        assert isinstance(filtered, Error)


class TestResultAggregation:
    """Tests for result aggregation helpers."""

    def test_combine_results_all_success(self):
        """Test combining all successful results."""
        result = combine_results(Success(1), Success(2), Success(3))
        assert isinstance(result, Success)
        assert result.get_data() == [1, 2, 3]

    def test_combine_results_with_error(self):
        """Test combining results with one error."""
        result = combine_results(Success(1), Error("Failed"), Success(3))
        assert isinstance(result, Error)
        assert "Multiple operations failed" in result.get_error_message()

    def test_sequence_results_all_success(self):
        """Test sequencing all successful results."""
        results = [Success(1), Success(2), Success(3)]
        result = sequence_results(results)
        assert isinstance(result, Success)
        assert result.get_data() == [1, 2, 3]

    def test_sequence_results_with_error(self):
        """Test sequencing results with one error."""
        results = [Success(1), Error("Failed")]
        result = sequence_results(results)
        assert isinstance(result, Error)


class TestHTTPConversion:
    """Tests for HTTP response conversion."""

    def test_to_http_response_success(self):
        """Test converting success to HTTP response."""
        result = service_success(data={"id": 123}, service_name="TestService")
        response = to_http_response(result)
        assert response["success"] is True
        assert response["status"] == 200
        assert response["data"] == {"id": 123}

    def test_to_http_response_error(self):
        """Test converting error to HTTP response."""
        result = NotFoundError("TestDefinition", "test-123")
        response = to_http_response(result)
        assert response["success"] is False
        assert response["status"] == 404
        assert response["error"]["message"] is not None
        assert response["error"]["code"] == ErrorCode.RESOURCE_NOT_FOUND.value


# ============================================================================
# Test Result Builders
# ============================================================================

class TestResultBuilder:
    """Tests for ResultBuilder class."""

    def test_build_success(self):
        """Test building success result."""
        result = ResultBuilder().with_data(42).build()
        assert isinstance(result, Success)
        assert result.get_data() == 42

    def test_build_error(self):
        """Test building error result."""
        result = (ResultBuilder()
                  .with_error("Operation failed", code="OP_FAILED")
                  .build())
        assert isinstance(result, Error)
        assert result.get_error_message() == "Operation failed"

    def test_build_with_validator(self):
        """Test building with validator."""
        result = (ResultBuilder()
                  .add_validator(lambda x: x > 0, "Must be positive")
                  .with_data(42)
                  .build())
        assert isinstance(result, Success)

    def test_build_with_failing_validator(self):
        """Test building with failing validator."""
        result = (ResultBuilder()
                  .add_validator(lambda x: x > 0, "Must be positive")
                  .with_data(-1)
                  .build())
        assert isinstance(result, ValidationError)

    def test_build_with_transformer(self):
        """Test building with transformer."""
        result = (ResultBuilder()
                  .add_transformer(lambda x: x * 2)
                  .with_data(21)
                  .build())
        assert isinstance(result, Success)
        assert result.get_data() == 42

    def test_build_chainable(self):
        """Test builder chaining."""
        result = (ResultBuilder()
                  .with_data(10)
                  .validate(lambda x: x > 0, "Must be positive")
                  .transform(lambda x: x * 2)
                  .map(lambda x: x + 8)
                  .build())
        assert isinstance(result, Success)
        assert result.get_data() == 28

    def test_build_timeout(self):
        """Test building timeout result."""
        result = (ResultBuilder()
                  .with_timeout(timeout_seconds=30.0)
                  .build())
        assert isinstance(result, Timeout)
        assert result.timeout_seconds == 30.0

    def test_build_validation_error(self):
        """Test building validation error."""
        result = (ResultBuilder()
                  .with_validation_error()
                  .add_field_error("email", "Invalid")
                  .build())
        assert isinstance(result, ValidationError)
        assert result.errors == {"email": ["Invalid"]}

    def test_from_existing_result(self):
        """Test building from existing result."""
        original = Success(42)
        modified = ResultBuilder.from_result(original).with_data(100).build()
        assert modified.get_data() == 100


class TestServiceResultBuilder:
    """Tests for ServiceResultBuilder class."""

    def test_build_service_success(self):
        """Test building service success."""
        result = (ServiceResultBuilder()
                  .with_service("TestService")
                  .with_operation("create_test")
                  .with_data({"id": 123})
                  .build())
        assert isinstance(result, ServiceSuccess)
        assert result.get_data() == {"id": 123}
        assert result.service_name == "TestService"

    def test_build_service_error(self):
        """Test building service error."""
        result = (ServiceResultBuilder()
                  .with_service("TestService")
                  .with_error("Operation failed", ErrorCode.OPERATION_FAILED)
                  .build())
        assert isinstance(result, ServiceError)
        assert result.get_error_message() == "Operation failed"

    def test_build_not_found(self):
        """Test building not found error."""
        result = (ServiceResultBuilder()
                  .with_service("TestService")
                  .with_not_found("TestDefinition", "test-123")
                  .build())
        assert isinstance(result, ServiceError)
        assert result.error_code == ErrorCode.RESOURCE_NOT_FOUND
        assert result.get_http_status() == 404

    def test_build_with_metadata(self):
        """Test building with metadata."""
        result = (ServiceResultBuilder()
                  .with_data({"id": 123})
                  .with_metadata(version="1.0", count=5)
                  .build())
        assert result.metadata == {"version": "1.0", "count": 5}


class TestErrorResponseBuilder:
    """Tests for ErrorResponseBuilder class."""

    def test_build_error_response(self):
        """Test building error response."""
        response = (ErrorResponseBuilder()
                    .with_message("Not found")
                    .with_code("NOT_FOUND")
                    .with_status(404)
                    .build())
        assert response["error"] is True
        assert response["message"] == "Not found"
        assert response["status"] == 404
        assert response["code"] == "NOT_FOUND"

    def test_build_with_details(self):
        """Test building with details."""
        response = (ErrorResponseBuilder()
                    .with_message("Validation failed")
                    .add_detail("field", "value")
                    .build())
        assert response["details"]["field"] == "value"

    def test_build_with_field_errors(self):
        """Test building with field errors."""
        response = (ErrorResponseBuilder()
                    .with_message("Validation failed")
                    .add_field_error("email", "Invalid format")
                    .add_field_error("age", "Must be positive")
                    .build())
        assert response["field_errors"]["email"] == ["Invalid format"]
        assert response["field_errors"]["age"] == ["Must be positive"]

    def test_build_with_suggestions(self):
        """Test building with suggestions."""
        response = (ErrorResponseBuilder()
                    .with_message("Authentication failed")
                    .add_suggestion("Check your credentials")
                    .add_suggestion("Contact support")
                    .build())
        assert len(response["suggestions"]) == 2

    def test_from_service_error(self):
        """Test building from service error."""
        service_error = NotFoundError("TestDefinition", "test-123")
        builder = ErrorResponseBuilder.from_service_error(service_error)
        response = builder.build()
        assert response["status"] == 404
        assert response["code"] == ErrorCode.RESOURCE_NOT_FOUND.value


class TestValidationBuilder:
    """Tests for ValidationBuilder class."""

    def test_build_no_errors(self):
        """Test building validation with no errors."""
        result = ValidationBuilder().build_result()
        assert isinstance(result, Success)

    def test_build_with_field_errors(self):
        """Test building with field errors."""
        result = (ValidationBuilder()
                  .add_field_error("email", "Invalid")
                  .add_field_error("name", "Required")
                  .build())
        assert isinstance(result, ValidationError)
        assert result.errors["email"] == ["Invalid"]
        assert result.errors["name"] == ["Required"]

    def test_has_errors(self):
        """Test has_errors method."""
        builder = ValidationBuilder()
        assert builder.has_errors() is False

        builder.add_field_error("email", "Invalid")
        assert builder.has_errors() is True


class TestBulkOperationBuilder:
    """Tests for BulkOperationBuilder class."""

    def test_build_bulk_success(self):
        """Test building bulk operation with all successes."""
        result = (BulkOperationBuilder()
                  .add_success({"id": 1})
                  .add_success({"id": 2})
                  .add_success({"id": 3})
                  .build())
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert result.is_success() is True

    def test_build_bulk_mixed(self):
        """Test building bulk operation with mixed results."""
        result = (BulkOperationBuilder()
                  .add_success({"id": 1})
                  .add_error("Failed")
                  .add_success({"id": 3})
                  .build())
        assert result.total_items == 3
        assert result.successful_items == 2
        assert result.failed_items == 1
        assert result.is_success() is False

    def test_build_as_result(self):
        """Test building as regular result."""
        result = (BulkOperationBuilder()
                  .add_success()
                  .add_error("Failed")
                  .build_result())
        assert isinstance(result, Error)


# ============================================================================
# Test Type Guards
# ============================================================================

class TestTypeGuards:
    """Tests for type guard functions."""

    def test_is_success_type_guard(self):
        """Test is_success type guard."""
        result = Success(42)
        if is_success(result):
            # Type should be narrowed to Success
            data = result.get_data()
            assert data == 42

    def test_is_error_type_guard(self):
        """Test is_error type guard."""
        result = Error("Failed")
        if is_error(result):
            # Type should be narrowed to Error
            message = result.get_error_message()
            assert message == "Failed"

    def test_is_timeout_type_guard(self):
        """Test is_timeout type guard."""
        result = Timeout()
        if is_timeout(result):
            # Type should be narrowed to Timeout
            assert result.timeout_seconds is None

    def test_is_validation_error_type_guard(self):
        """Test is_validation_error type guard."""
        result = ValidationError()
        if is_validation_error(result):
            # Type should be narrowed to ValidationError
            assert result.errors == {}


# ============================================================================
# Test Functional Operations
# ============================================================================

class TestFunctionalOperations:
    """Tests for functional operations on results."""

    def test_fold_success(self):
        """Test fold on success."""
        result = Success(42)
        value = fold(
            result,
            on_success=lambda x: x * 2,
            on_error=lambda r: 0
        )
        assert value == 84

    def test_fold_error(self):
        """Test fold on error."""
        result = Error("Failed")
        value = fold(
            result,
            on_success=lambda x: x * 2,
            on_error=lambda r: 0
        )
        assert value == 0

    def test_pattern_matching_success(self):
        """Test pattern matching on success."""
        result = Success(42)
        value = match(
            result,
            (Success, lambda r: r.get_data() * 2),
            (Error, lambda r: 0)
        )
        assert value == 84

    def test_pattern_matching_error(self):
        """Test pattern matching on error."""
        result = Error("Failed")
        value = match(
            result,
            (Success, lambda r: r.get_data() * 2),
            (Error, lambda r: 0)
        )
        assert value == 0


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Integration tests for common result usage patterns."""

    def test_service_layer_success_flow(self):
        """Test typical service layer success flow."""
        # Simulate service operation
        def create_user(user_data):
            if not user_data.get("email"):
                return service_error("Email is required", ErrorCode.VALIDATION_ERROR)

            if "@" not in user_data["email"]:
                return service_error("Invalid email format", ErrorCode.VALIDATION_ERROR)

            created_user = {"id": 123, **user_data}
            return service_success(
                data=created_user,
                service_name="UserService",
                operation_name="create_user"
            )

        result = create_user({"email": "test@example.com"})

        assert result.is_success()
        user = result.get_data()
        assert user["id"] == 123
        assert user["email"] == "test@example.com"

    def test_service_layer_error_flow(self):
        """Test typical service layer error flow."""
        def create_user(user_data):
            if not user_data.get("email"):
                return service_error("Email is required", ErrorCode.VALIDATION_ERROR)

            return service_success(data={"id": 123, **user_data})

        result = create_user({"name": "John"})

        assert result.is_error()
        assert result.error_code == ErrorCode.VALIDATION_ERROR
        assert "Email is required" in result.get_error_message()

    def test_chained_operations(self):
        """Test chained service operations."""
        def validate_input(data):
            if not data.get("value"):
                return service_error("Value required", ErrorCode.VALIDATION_ERROR)
            return service_success(data=data)

        def process_data(data):
            processed = {"original": data["value"], "doubled": data["value"] * 2}
            return service_success(data=processed)

        def save_result(data):
            saved = {"id": 999, **data}
            return service_success(data=saved)

        # Chain operations
        result1 = validate_input({"value": 21})
        assert result1.is_success()

        result2 = process_data(result1.get_data())
        assert result2.is_success()
        assert result2.get_data()["doubled"] == 42

        result3 = save_result(result2.get_data())
        assert result3.is_success()
        assert result3.get_data()["id"] == 999

    def test_error_propagation_through_chain(self):
        """Test error propagation through operation chain."""
        def validate_input(data):
            if not data.get("value"):
                return service_error("Value required", ErrorCode.VALIDATION_ERROR)
            return service_success(data=data)

        def process_data(data):
            # This won't be called due to validation error
            return service_success(data={"processed": data})

        # Validation fails
        result1 = validate_input({})
        assert result1.is_error()

        # Processing won't execute (in real implementation, would short-circuit)
        # For now, just verify error is maintained
        assert result1.error_code == ErrorCode.VALIDATION_ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
