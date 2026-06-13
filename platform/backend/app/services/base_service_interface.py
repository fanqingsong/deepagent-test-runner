"""
Base Service Interface

Defines standard interfaces for all services following SOLID principles.
Provides base classes for CRUD, Query, and Execution operations.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypeVar, Generic, List, Dict, Any, Optional, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Type Variables
# ============================================================================

T = TypeVar('T')  # Model type
CreateSchema = TypeVar('CreateSchema', bound=BaseModel)
UpdateSchema = TypeVar('UpdateSchema', bound=BaseModel)


# ============================================================================
# Standard Exceptions
# ============================================================================

class ServiceError(Exception):
    """Base service exception with structured error information."""

    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class ValidationError(ServiceError):
    """Validation failed error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class NotFoundError(ServiceError):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(message, "NOT_FOUND")
        self.resource = resource
        self.identifier = identifier


class PermissionError(ServiceError):
    """Permission denied error."""

    def __init__(self, message: str = "Permission denied", action: Optional[str] = None):
        super().__init__(message, "PERMISSION_DENIED")
        self.action = action


class ConflictError(ServiceError):
    """Resource conflict error (e.g., duplicate entry)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT", details)


# ============================================================================
# Base Service Interface
# ============================================================================

class IService(ABC):
    """
    Base interface that all services must implement.

    Provides standard health check and service identification methods.
    """

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health.

        Returns:
            Dict with health status:
            {
                "healthy": bool,
                "status": str,  # "healthy", "degraded", "unhealthy"
                "checks": Dict[str, bool],  # Individual component health
                "timestamp": str  # ISO format
            }
        """
        pass

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Get service name for logging and monitoring.

        Returns:
            Service name as string
        """
        pass

    @abstractmethod
    def get_service_version(self) -> str:
        """
        Get service version.

        Returns:
            Service version string
        """
        pass

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error with consistent format.

        Args:
            error: Exception to log
            context: Optional context information
        """
        logger.error(
            f"Service error in {self.get_service_name()}: {str(error)}",
            extra={
                "service": self.get_service_name(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            },
            exc_info=True
        )


# ============================================================================
# CRUD Service Interface
# ============================================================================

class ICrudService(Generic[T, CreateSchema, UpdateSchema], ABC):
    """
    Standard CRUD operations interface.

    All services that manage entities should implement this interface
    for consistency and testability.
    """

    @abstractmethod
    async def create(
        self,
        data: CreateSchema,
        created_by: Optional[int] = None
    ) -> T:
        """
        Create a new entity.

        Args:
            data: Creation data schema
            created_by: Optional user ID who is creating the entity

        Returns:
            Created entity

        Raises:
            ValidationError: If data is invalid
            PermissionError: If user lacks permission
            ConflictError: If entity already exists
        """
        pass

    @abstractmethod
    async def get_by_id(
        self,
        id: int,
        include_deleted: bool = False
    ) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            id: Entity ID
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Entity or None if not found
        """
        pass

    @abstractmethod
    async def get_or_404(
        self,
        id: int,
        include_deleted: bool = False
    ) -> T:
        """
        Get entity by ID or raise NotFoundError.

        Args:
            id: Entity ID
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Entity

        Raises:
            NotFoundError: If entity not found
        """
        pass

    @abstractmethod
    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[T]:
        """
        List entities with pagination and filtering.

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return
            filters: Optional filter criteria
            sort_by: Field to sort by
            sort_order: Sort direction ("asc" or "desc")

        Returns:
            List of entities
        """
        pass

    @abstractmethod
    async def update(
        self,
        id: int,
        data: UpdateSchema,
        updated_by: Optional[int] = None
    ) -> T:
        """
        Update an entity.

        Args:
            id: Entity ID
            data: Update data schema
            updated_by: Optional user ID who is updating the entity

        Returns:
            Updated entity

        Raises:
            NotFoundError: If entity not found
            ValidationError: If data is invalid
            PermissionError: If user lacks permission
        """
        pass

    @abstractmethod
    async def delete(
        self,
        id: int,
        deleted_by: Optional[int] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete an entity.

        Args:
            id: Entity ID
            deleted_by: Optional user ID who is deleting the entity
            hard_delete: Whether to hard delete (vs soft delete)

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If entity not found
            PermissionError: If user lacks permission
        """
        pass

    @abstractmethod
    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count entities matching filters.

        Args:
            filters: Optional filter criteria

        Returns:
            Count of entities
        """
        pass


# ============================================================================
# Query Service Interface
# ============================================================================

class IQueryService(Generic[T], ABC):
    """
    Standard query operations interface.

    Provides search and filtering capabilities for services.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """
        Search entities by text query.

        Args:
            query: Search query string
            skip: Number of items to skip
            limit: Maximum number of items to return
            filters: Additional filter criteria

        Returns:
            List of matching entities
        """
        pass

    @abstractmethod
    async def filter(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[T]:
        """
        Filter entities by criteria.

        Args:
            filters: Filter criteria
            skip: Number of items to skip
            limit: Maximum number of items to return
            sort_by: Field to sort by
            sort_order: Sort direction

        Returns:
            List of matching entities
        """
        pass

    @abstractmethod
    async def get_related(
        self,
        id: int,
        relation_name: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Any]:
        """
        Get related entities for a given entity.

        Args:
            id: Entity ID
            relation_name: Name of the relationship
            skip: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of related entities
        """
        pass


# ============================================================================
# Execution Service Interface
# ============================================================================

class IExecutionService(ABC):
    """
    Standard execution operations interface.

    For services that execute tasks or workflows.
    """

    @abstractmethod
    async def execute(
        self,
        task_id: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task.

        Args:
            task_id: Task identifier
            parameters: Task execution parameters
            context: Optional execution context

        Returns:
            Execution result with:
            {
                "task_id": str,
                "status": str,  # "completed", "failed", "cancelled"
                "result": Any,
                "error": Optional[str],
                "duration_ms": int,
                "timestamp": str
            }
        """
        pass

    @abstractmethod
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Get status of an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Status information:
            {
                "execution_id": str,
                "status": str,
                "progress": float,  # 0.0 to 1.0
                "started_at": str,
                "updated_at": str,
                "estimated_completion": Optional[str]
            }
        """
        pass

    @abstractmethod
    async def cancel_execution(
        self,
        execution_id: str
    ) -> bool:
        """
        Cancel a running execution.

        Args:
            execution_id: Execution identifier

        Returns:
            True if cancelled successfully
        """
        pass


# ============================================================================
# Base Service Implementation
# ============================================================================

class BaseService(IService):
    """
    Base service implementation with common functionality.

    Provides default implementations for IService interface.
    """

    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        """
        Initialize base service.

        Args:
            service_name: Name of the service
            service_version: Version of the service
        """
        self._service_name = service_name
        self._service_version = service_version

    async def health_check(self) -> Dict[str, Any]:
        """
        Default health check implementation.

        Returns basic health status. Override for custom health checks.
        """
        return {
            "healthy": True,
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_service_name(self) -> str:
        """Get service name."""
        return self._service_name

    def get_service_version(self) -> str:
        """Get service version."""
        return self._service_version


# ============================================================================
# Service Response Wrappers
# ============================================================================

class ServiceResponse:
    """Standard service response wrapper."""

    def __init__(
        self,
        value: Any,
        success: bool = True,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.value = value
        self.success = success
        self.message = message
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "value": self.value,
            "success": self.success,
            "message": self.message,
            "metadata": self.metadata
        }


class ListResponse:
    """Standard list response with pagination."""

    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 50
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    @property
    def has_more(self) -> bool:
        """Check if there are more items."""
        return (self.page * self.page_size) < self.total

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more
        }


# ============================================================================
# Utility Functions
# ============================================================================

def handle_service_error(error: Exception, service_name: str) -> ServiceError:
    """
    Convert unknown exceptions to ServiceError.

    Args:
        error: Original exception
        service_name: Name of the service

    Returns:
        ServiceError instance
    """
    if isinstance(error, ServiceError):
        return error

    logger.error(
        f"Unexpected error in {service_name}: {str(error)}",
        exc_info=True
    )

    return ServiceError(
        message=f"An unexpected error occurred: {str(error)}",
        code="UNEXPECTED_ERROR",
        details={"original_error": str(error)}
    )


async def async_health_check_wrapper(
    health_checks: Dict[str, Any],
    service_name: str
) -> Dict[str, Any]:
    """
    Wrapper for running multiple health checks.

    Args:
        health_checks: Dictionary of health check functions
        service_name: Name of the service

    Returns:
        Combined health check result
    """
    results = {}
    all_healthy = True

    for name, check in health_checks.items():
        try:
            if callable(check):
                result = await check() if asyncio.iscoroutinefunction(check) else check()
                results[name] = result if isinstance(result, bool) else True
            else:
                results[name] = bool(check)
        except Exception as e:
            results[name] = False
            all_healthy = False
            logger.error(f"Health check '{name}' failed: {str(e)}")

    return {
        "healthy": all_healthy,
        "status": "healthy" if all_healthy else "degraded",
        "checks": results,
        "timestamp": datetime.utcnow().isoformat()
    }
