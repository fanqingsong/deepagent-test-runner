"""
Simple Service Result Types

Simplified version without frozen dataclasses for compatibility.
"""

from typing import Optional, Dict, Any, List, Type, Set, Generic, TypeVar
from datetime import datetime

from app.core.result_types import Result, Success as BaseSuccess
from app.core.service_result_types import ErrorCode, HTTPStatusMap


T = TypeVar('T')
E = TypeVar('E')


class ServiceSuccess(BaseSuccess, Generic[T]):
    """Simple service success result."""

    def __init__(
        self,
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        **service_context
    ):
        super().__init__(data)
        self.metadata = metadata
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()

    def with_metadata(self, **metadata) -> 'ServiceSuccess[Any]':
        """Create new success with additional metadata."""
        current_metadata = self.metadata or {}
        return ServiceSuccess(
            data=self.data,
            metadata={**current_metadata, **metadata},
            service_name=self.service_name,
            operation_name=self.operation_name,
            request_id=self.request_id,
        )


class NotFoundError(Exception):
    """Simple not found error."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        **service_context
    ):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        self.message = message
        self.error_code = ErrorCode.RESOURCE_NOT_FOUND
        self.details = {"resource": resource, "identifier": identifier}
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()

    def is_error(self) -> bool:
        return True

    def get_http_status(self) -> int:
        return 404


class ConflictError(Exception):
    """Simple conflict error."""

    def __init__(
        self,
        message: str,
        conflicting_resource: Optional[str] = None,
        **service_context
    ):
        self.message = message
        self.error_code = ErrorCode.RESOURCE_CONFLICT
        self.details = {"conflicting_resource": conflicting_resource} if conflicting_resource else {}
        self.service_name = service_context.get('service_name')
        self.operation_name = service_context.get('operation_name')
        self.request_id = service_context.get('request_id')
        self.timestamp = datetime.utcnow()

    def is_error(self) -> bool:
        return True

    def get_http_status(self) -> int:
        return 409
