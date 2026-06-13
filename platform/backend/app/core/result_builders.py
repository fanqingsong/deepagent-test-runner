"""
Result Builders

Builder patterns for fluent result construction and error response building.
Provides type-safe, chainable result construction with validation helpers.
"""

from typing import Any, Optional, Dict, List, Callable, Type, Union, TypeVar
from dataclasses import field, replace
from datetime import datetime
from copy import deepcopy

from app.core.result_types import Result, Success, Error, Timeout, ValidationError
from app.core.error_codes import ErrorCode


T = TypeVar('T')
U = TypeVar('U')


# ============================================================================
# Result Builder
# ============================================================================

class ResultBuilder:
    """
    Fluent builder for constructing Result objects.

    Provides a chainable interface for building complex results
    with validation, transformation, and error handling.

    Examples:
        >>> ResultBuilder().with_data(123).build()
        Success(123)

        >>> (ResultBuilder()
        ...     .validate(lambda x: x > 0, "Must be positive")
        ...     .with_data(42)
        ...     .build())
        Success(42)

        >>> (ResultBuilder()
        ...     .with_error("Operation failed", code="OP_FAILED")
        ...     .build())
        Error('Operation failed', code='OP_FAILED')
    """

    def __init__(self):
        """Initialize result builder with default values."""
        self._data: Any = None
        self._error_message: Optional[str] = None
        self._error_code: Optional[str] = None
        self._error_details: Dict[str, Any] = {}
        self._validation_errors: Dict[str, List[str]] = {}
        self._timeout_seconds: Optional[float] = None
        self._validators: List[Callable[[Any], bool]] = []
        self._transformers: List[Callable[[Any], Any]] = []
        self._is_error: bool = False
        self._is_timeout: bool = False
        self._is_validation_error: bool = False

    def with_data(self, data: Any) -> 'ResultBuilder':
        """
        Set success data.

        Args:
            data: Success data to set

        Returns:
            Self for chaining
        """
        self._data = data
        self._is_error = False
        return self

    def with_error(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'ResultBuilder':
        """
        Set error information.

        Args:
            message: Error message
            code: Optional error code
            details: Optional error details

        Returns:
            Self for chaining
        """
        self._error_message = message
        self._error_code = code
        self._error_details = details or {}
        self._is_error = True
        self._is_timeout = False
        self._is_validation_error = False
        return self

    def with_timeout(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'ResultBuilder':
        """
        Set timeout information.

        Args:
            message: Timeout message
            timeout_seconds: Optional timeout duration
            details: Optional timeout details

        Returns:
            Self for chaining
        """
        self._error_message = message
        self._timeout_seconds = timeout_seconds
        self._error_details = details or {}
        self._is_error = True
        self._is_timeout = True
        self._is_validation_error = False
        return self

    def with_validation_error(
        self,
        message: str = "Validation failed",
        field_errors: Optional[Dict[str, List[str]]] = None
    ) -> 'ResultBuilder':
        """
        Set validation error information.

        Args:
            message: Validation error message
            field_errors: Optional field-level errors

        Returns:
            Self for chaining
        """
        self._error_message = message
        self._validation_errors = field_errors or {}
        self._is_error = True
        self._is_timeout = False
        self._is_validation_error = True
        return self

    def add_validator(
        self,
        validator: Callable[[Any], bool],
        error_message: str = "Validation failed"
    ) -> 'ResultBuilder':
        """
        Add validator function.

        Args:
            validator: Function that validates data
            error_message: Error message if validation fails

        Returns:
            Self for chaining
        """
        self._validators.append((validator, error_message))
        return self

    def add_transformer(
        self,
        transformer: Callable[[Any], Any]
    ) -> 'ResultBuilder':
        """
        Add transformer function.

        Args:
            transformer: Function to transform data

        Returns:
            Self for chaining
        """
        self._transformers.append(transformer)
        return self

    def add_error_detail(self, key: str, value: Any) -> 'ResultBuilder':
        """
        Add detail to error information.

        Args:
            key: Detail key
            value: Detail value

        Returns:
            Self for chaining
        """
        self._error_details[key] = value
        return self

    def add_field_error(self, field: str, error: str) -> 'ResultBuilder':
        """
        Add field-level validation error.

        Args:
            field: Field name
            error: Error message

        Returns:
            Self for chaining
        """
        if field not in self._validation_errors:
            self._validation_errors[field] = []
        self._validation_errors[field].append(error)
        return self

    def validate(
        self,
        predicate: Callable[[Any], bool],
        error_message: str = "Validation failed"
    ) -> 'ResultBuilder':
        """
        Add validation predicate.

        Args:
            predicate: Function to test data
            error_message: Error message if predicate fails

        Returns:
            Self for chaining
        """
        return self.add_validator(predicate, error_message)

    def transform(self, transformer: Callable[[Any], Any]) -> 'ResultBuilder':
        """
        Add transformation function.

        Args:
            transformer: Function to transform data

        Returns:
            Self for chaining
        """
        return self.add_transformer(transformer)

    def map(self, func: Callable[[Any], Any]) -> 'ResultBuilder':
        """
        Add mapping function (alias for transform).

        Args:
            func: Function to map data

        Returns:
            Self for chaining
        """
        return self.transform(func)

    def build(self) -> Result:
        """
        Build the final result.

        Applies validators, transformers, and constructs appropriate result type.

        Returns:
            Constructed result object

        Raises:
            ValueError: If validation fails
        """
        # If explicitly marked as error, return error result
        if self._is_error:
            if self._is_timeout:
                return Timeout(self._error_message, self._timeout_seconds, self._error_details)
            elif self._is_validation_error:
                return ValidationError(self._error_message, self._validation_errors)
            else:
                return Error(self._error_message, self._error_code, self._error_details)

        # Apply validators
        for validator, error_message in self._validators:
            if not validator(self._data):
                return ValidationError(error_message, self._validation_errors)

        # Apply transformers
        for transformer in self._transformers:
            try:
                self._data = transformer(self._data)
            except Exception as e:
                return Error(f"Transform failed: {str(e)}")

        # Return success
        return Success(self._data)

    def build_or_none(self) -> Optional[Result]:
        """
        Build result, returning None if validation fails.

        Returns:
            Result object or None if validation fails
        """
        try:
            return self.build()
        except Exception:
            return None

    @classmethod
    def from_result(cls, result: Result) -> 'ResultBuilder':
        """
        Create builder from existing result.

        Args:
            result: Existing result to copy from

        Returns:
            New builder instance

        Examples:
            >>> builder = ResultBuilder.from_result(Success(42))
            >>> builder.with_data(100).build()
            Success(100)
        """
        builder = cls()
        if result.is_success():
            builder._data = result.get_data()
        elif result.is_timeout():
            timeout_result = result  # type: Timeout
            builder.with_timeout(
                message=timeout_result.message,
                timeout_seconds=timeout_result.timeout_seconds,
                details=timeout_result.details
            )
        elif result.is_validation_error():
            validation_result = result  # type: ValidationError
            builder.with_validation_error(
                message=validation_result.message,
                field_errors=validation_result.errors
            )
        else:
            error_result = result  # type: Error
            builder.with_error(
                message=error_result.message,
                code=error_result.code,
                details=error_result.details
            )
        return builder


# ============================================================================
# Service Result Builder
# ============================================================================

class ResultBuilder:
    """
    Fluent builder for constructing Result objects.

    Extends ResultBuilder with service-specific context and features.

    Examples:
        >>> (ResultBuilder()
        ...     .with_service("ExecutionService")
        ...     .with_operation("create_test_run")
        ...     .with_data({"run_id": "123"})
        ...     .build())
        Success(data={'run_id': '123'}, service_name='ExecutionService')
    """

    def __init__(self):
        """Initialize service result builder."""
        self._data: Any = None
        self._metadata: Dict[str, Any] = {}
        self._error_message: Optional[str] = None
        self._error_code: ErrorCode = ErrorCode.OPERATION_FAILED
        self._error_details: Dict[str, Any] = {}
        self._service_name: Optional[str] = None
        self._operation_name: Optional[str] = None
        self._request_id: Optional[str] = None
        self._is_error: bool = False

    def with_service(self, service_name: str) -> 'ResultBuilder':
        """
        Set service name.

        Args:
            service_name: Name of the service

        Returns:
            Self for chaining
        """
        self._service_name = service_name
        return self

    def with_operation(self, operation_name: str) -> 'ResultBuilder':
        """
        Set operation name.

        Args:
            operation_name: Name of the operation

        Returns:
            Self for chaining
        """
        self._operation_name = operation_name
        return self

    def with_request_id(self, request_id: str) -> 'ResultBuilder':
        """
        Set request ID for tracing.

        Args:
            request_id: Request identifier

        Returns:
            Self for chaining
        """
        self._request_id = request_id
        return self

    def with_data(self, data: Any) -> 'ResultBuilder':
        """
        Set success data.

        Args:
            data: Success data

        Returns:
            Self for chaining
        """
        self._data = data
        self._is_error = False
        return self

    def with_metadata(self, **metadata) -> 'ResultBuilder':
        """
        Add metadata to success result.

        Args:
            **metadata: Metadata key-value pairs

        Returns:
            Self for chaining
        """
        self._metadata.update(metadata)
        return self

    def with_error(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
        details: Optional[Dict[str, Any]] = None
    ) -> 'ResultBuilder':
        """
        Set error information.

        Args:
            message: Error message
            error_code: Error code enum
            details: Optional error details

        Returns:
            Self for chaining
        """
        self._error_message = message
        self._error_code = error_code
        self._error_details = details or {}
        self._is_error = True
        return self

    def with_not_found(
        self,
        resource: str,
        identifier: Optional[str] = None
    ) -> 'ResultBuilder':
        """
        Set not found error.

        Args:
            resource: Resource type
            identifier: Optional resource identifier

        Returns:
            Self for chaining
        """
        self._error_message = f"{resource} not found"
        if identifier:
            self._error_message += f": {identifier}"
        self._error_code = ErrorCode.RESOURCE_NOT_FOUND
        self._error_details.update({"resource": resource, "identifier": identifier})
        self._is_error = True
        return self

    def with_conflict(
        self,
        message: str,
        conflicting_resource: Optional[str] = None
    ) -> 'ResultBuilder':
        """
        Set conflict error.

        Args:
            message: Conflict message
            conflicting_resource: Optional conflicting resource

        Returns:
            Self for chaining
        """
        self._error_message = message
        self._error_code = ErrorCode.RESOURCE_CONFLICT
        if conflicting_resource:
            self._error_details["conflicting_resource"] = conflicting_resource
        self._is_error = True
        return self

    def add_detail(self, key: str, value: Any) -> 'ResultBuilder':
        """
        Add detail to error or metadata.

        Args:
            key: Detail key
            value: Detail value

        Returns:
            Self for chaining
        """
        if self._is_error:
            self._error_details[key] = value
        else:
            self._metadata[key] = value
        return self

    def build(self) -> Result:
        """
        Build the final service result.

        Returns:
            Constructed service result

        Examples:
            >>> builder = ResultBuilder()
            >>> builder.with_service("TestService").with_data({"id": 1}).build()
            Success(data={'id': 1}, service_name='TestService')
        """
        context = {
            "service_name": self._service_name,
            "operation_name": self._operation_name,
            "request_id": self._request_id,
        }

        if self._is_error:
            return Error(
                message=self._error_message,
                error_code=self._error_code,
                details=self._error_details,
                **context
            )

        return Success({
            'data': self._data,
            'metadata': self._metadata,
            'service_name': self._service_name,
            'operation_name': self._operation_name,
            'request_id': self._request_id
        })


# ============================================================================
# Error Response Builder
# ============================================================================

class ErrorResponseBuilder:
    """
    Builder for constructing detailed error responses.

    Provides fluent interface for building comprehensive error responses
    with HTTP status mapping and detailed information.

    Examples:
        >>> (ErrorResponseBuilder()
        ...     .with_message("User not found")
        ...     .with_code("NOT_FOUND")
        ...     .with_status(404)
        ...     .add_detail("user_id", 123)
        ...     .build())
        {'message': 'User not found', 'code': 'NOT_FOUND', 'status': 404, 'details': {'user_id': 123}}
    """

    def __init__(self):
        """Initialize error response builder."""
        self._message: str = "An error occurred"
        self._code: Optional[str] = None
        self._status: int = 500
        self._details: Dict[str, Any] = {}
        self._field_errors: Dict[str, List[str]] = {}
        self._suggestions: List[str] = []
        self._documentation_url: Optional[str] = None
        self._request_id: Optional[str] = None
        self._timestamp: datetime = datetime.utcnow()

    def with_message(self, message: str) -> 'ErrorResponseBuilder':
        """
        Set error message.

        Args:
            message: Error message

        Returns:
            Self for chaining
        """
        self._message = message
        return self

    def with_code(self, code: str) -> 'ErrorResponseBuilder':
        """
        Set error code.

        Args:
            code: Error code string

        Returns:
            Self for chaining
        """
        self._code = code
        return self

    def with_status(self, status: int) -> 'ErrorResponseBuilder':
        """
        Set HTTP status code.

        Args:
            status: HTTP status code

        Returns:
            Self for chaining
        """
        self._status = status
        return self

    def with_error_code(self, error_code: ErrorCode) -> 'ErrorResponseBuilder':
        """
        Set error from ErrorCode enum.

        Args:
            error_code: Error code enum value

        Returns:
            Self for chaining
        """
        self._code = error_code.value
        from app.core.service_result_types import HTTPStatusMap
        self._status = HTTPStatusMap.get_status(error_code)
        return self

    def add_detail(self, key: str, value: Any) -> 'ErrorResponseBuilder':
        """
        Add detail information.

        Args:
            key: Detail key
            value: Detail value

        Returns:
            Self for chaining
        """
        self._details[key] = value
        return self

    def add_field_error(self, field: str, error: str) -> 'ErrorResponseBuilder':
        """
        Add field-level validation error.

        Args:
            field: Field name
            error: Error message

        Returns:
            Self for chaining
        """
        if field not in self._field_errors:
            self._field_errors[field] = []
        self._field_errors[field].append(error)
        return self

    def add_suggestion(self, suggestion: str) -> 'ErrorResponseBuilder':
        """
        Add suggestion for resolving the error.

        Args:
            suggestion: Suggestion text

        Returns:
            Self for chaining
        """
        self._suggestions.append(suggestion)
        return self

    def with_documentation_url(self, url: str) -> 'ErrorResponseBuilder':
        """
        Set documentation URL for error resolution.

        Args:
            url: Documentation URL

        Returns:
            Self for chaining
        """
        self._documentation_url = url
        return self

    def with_request_id(self, request_id: str) -> 'ErrorResponseBuilder':
        """
        Set request ID for error tracking.

        Args:
            request_id: Request identifier

        Returns:
            Self for chaining
        """
        self._request_id = request_id
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build the final error response dictionary.

        Returns:
            Error response dictionary

        Examples:
            >>> builder = ErrorResponseBuilder()
            >>> builder.with_message("Not found").with_status(404).build()
            {'message': 'Not found', 'status': 404, 'timestamp': '...'}
        """
        response: Dict[str, Any] = {
            "error": True,
            "message": self._message,
            "status": self._status,
            "timestamp": self._timestamp.isoformat(),
        }

        if self._code:
            response["code"] = self._code

        if self._details:
            response["details"] = self._details

        if self._field_errors:
            response["field_errors"] = self._field_errors

        if self._suggestions:
            response["suggestions"] = self._suggestions

        if self._documentation_url:
            response["documentation_url"] = self._documentation_url

        if self._request_id:
            response["request_id"] = self._request_id

        return response

    @classmethod
    def from_service_error(cls, error: Error) -> 'ErrorResponseBuilder':
        """
        Create builder from service error.

        Args:
            error: Service error to copy from

        Returns:
            New builder instance

        Examples:
            >>> error = NotFoundError("Test", "123")
            >>> builder = ErrorResponseBuilder.from_service_error(error)
            >>> builder.build()
            {'message': 'Test not found: 123', 'status': 404, 'code': 'RESOURCE_NOT_FOUND'}
        """
        builder = cls()
        builder.with_message(error.message)
        builder.with_error_code(error.error_code)
        builder.with_request_id(error.request_id or "unknown")

        if error.details:
            for key, value in error.details.items():
                builder.add_detail(key, value)

        return builder


# ============================================================================
# Validation Builder
# ============================================================================

class ValidationBuilder:
    """
    Builder for constructing validation results with field-level errors.

    Provides fluent interface for building complex validation results
    with multiple field errors and suggestions.

    Examples:
        >>> (ValidationBuilder()
        ...     .add_field_error("email", "Invalid format")
        ...     .add_field_error("age", "Must be positive")
        ...     .build())
        ValidationError('Validation failed', errors={'email': ['Invalid format'], 'age': ['Must be positive']})
    """

    def __init__(self):
        """Initialize validation builder."""
        self._message: str = "Validation failed"
        self._field_errors: Dict[str, List[str]] = {}
        self._global_errors: List[str] = []
        self._warnings: List[str] = []

    def with_message(self, message: str) -> 'ValidationBuilder':
        """
        Set validation error message.

        Args:
            message: Validation message

        Returns:
            Self for chaining
        """
        self._message = message
        return self

    def add_field_error(self, field: str, error: str) -> 'ValidationBuilder':
        """
        Add field-level validation error.

        Args:
            field: Field name
            error: Error message

        Returns:
            Self for chaining
        """
        if field not in self._field_errors:
            self._field_errors[field] = []
        self._field_errors[field].append(error)
        return self

    def add_global_error(self, error: str) -> 'ValidationBuilder':
        """
        Add global validation error.

        Args:
            error: Global error message

        Returns:
            Self for chaining
        """
        self._global_errors.append(error)
        return self

    def add_warning(self, warning: str) -> 'ValidationBuilder':
        """
        Add validation warning.

        Args:
            warning: Warning message

        Returns:
            Self for chaining
        """
        self._warnings.append(warning)
        return self

    def has_errors(self) -> bool:
        """
        Check if validation has any errors.

        Returns:
            True if errors exist, False otherwise
        """
        return bool(self._field_errors or self._global_errors)

    def build(self) -> ValidationError:
        """
        Build validation error result.

        Returns:
            ValidationError result

        Examples:
            >>> builder = ValidationBuilder()
            >>> builder.add_field_error("name", "Required").build()
            ValidationError('Validation failed', errors={'name': ['Required']})
        """
        all_errors = {}

        if self._field_errors:
            all_errors.update(self._field_errors)

        if self._global_errors:
            all_errors["_global"] = self._global_errors

        if not all_errors:
            # No errors - return success
            return Success(None)  # type: ignore

        return ValidationError(self._message, all_errors)

    def build_result(self) -> Result:
        """
        Build result (Success if no errors, ValidationError otherwise).

        Returns:
            Result object

        Examples:
            >>> builder = ValidationBuilder()
            >>> builder.build_result()
            Success(None)
        """
        if not self.has_errors():
            return Success(None)

        return self.build()


# ============================================================================
# Bulk Operation Builder
# ============================================================================

class BulkOperationBuilder:
    """
    Builder for constructing bulk operation results.

    Provides fluent interface for building results from bulk operations
    with individual item tracking.

    Examples:
        >>> builder = BulkOperationBuilder()
        >>> builder.add_item_result(Success({"id": 1}))
        >>> builder.add_item_result(Error("Failed"))
        >>> builder.build()
        BulkResult(total_items=2, successful_items=1, failed_items=1)
    """

    def __init__(self):
        """Initialize bulk operation builder."""
        self._item_results: List[Result] = []
        self._total_items: int = 0

    def add_item_result(self, result: Result) -> 'BulkOperationBuilder':
        """
        Add individual item result.

        Args:
            result: Result for individual item

        Returns:
            Self for chaining
        """
        self._item_results.append(result)
        self._total_items += 1
        return self

    def add_success(self, data: Any = None) -> 'BulkOperationBuilder':
        """
        Add successful item result.

        Args:
            data: Success data

        Returns:
            Self for chaining
        """
        return self.add_item_result(Success(data))

    def add_error(self, message: str, **kwargs) -> 'BulkOperationBuilder':
        """
        Add error item result.

        Args:
            message: Error message
            **kwargs: Additional error parameters

        Returns:
            Self for chaining
        """
        return self.add_item_result(Error(message, **kwargs))

    def with_total(self, total: int) -> 'BulkOperationBuilder':
        """
        Set total items count.

        Args:
            total: Total number of items

        Returns:
            Self for chaining
        """
        self._total_items = total
        return self

    def build(self) -> Result:
        """
        Build bulk operation result.

        Returns:
            BulkResult with aggregated results

        Examples:
            >>> builder = BulkOperationBuilder()
            >>> builder.add_success().add_success().add_error("Failed").build()
            BulkResult(total_items=3, successful_items=2, failed_items=1)
        """
        successful = sum(1 for r in self._item_results if r.is_success())
        failed = sum(1 for r in self._item_results if r.is_error())

        return BulkResult(
            total_items=self._total_items,
            successful_items=successful,
            failed_items=failed,
            item_results=self._item_results
        )

    def build_result(self) -> Result:
        """
        Build as regular result.

        Returns:
            Result object (Success or Error based on bulk result)

        Examples:
            >>> builder = BulkOperationBuilder()
            >>> builder.add_success().build_result()
            Success({'total_items': 1, 'successful_items': 1, ...})
        """
        bulk_result = self.build()

        if bulk_result.is_success():
            return Success(bulk_result.get_data())
        else:
            return Error(bulk_result.get_error_message())
