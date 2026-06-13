# Service Interface Standards

## Overview

This document defines the standard interface patterns for all services in the application. Following these standards ensures:

- **Liskov Substitution Principle**: Services can be swapped or mocked easily
- **Consistency**: Predictable interfaces across all services
- **Testability**: Easy to mock and test
- **Maintainability**: Clear patterns for new services

## Core Principles

1. **Return Type Consistency**: All methods return standardized types
2. **Error Handling**: Consistent exception handling across services
3. **Parameter Naming**: Standardized parameter names and types
4. **Method Signatures**: Predictable method signatures for similar operations
5. **Type Safety**: Full type hints on all public methods

## Standard Return Types

### Success Responses

```python
# Single object response
from typing import TypeVar, Generic

T = TypeVar('T')

class ServiceResponse(Generic[T]):
    """Standard service response wrapper."""
    value: T
    success: bool = True
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# List response
class ListResponse(Generic[T]):
    """Standard list response with pagination."""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False
```

### Error Handling

```python
class ServiceError(Exception):
    """Base service exception."""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class ValidationError(ServiceError):
    """Validation failed."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field

class NotFoundError(ServiceError):
    """Resource not found."""
    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(message, "NOT_FOUND")
        self.resource = resource
        self.identifier = identifier

class PermissionError(ServiceError):
    """Permission denied."""
    def __init__(self, message: str = "Permission denied", action: Optional[str] = None):
        super().__init__(message, "PERMISSION_DENIED")
        self.action = action
```

## Standard Service Interface

### Base Service Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IService(ABC):
    """Base interface that all services must implement."""

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
```

### CRUD Service Interface

```python
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel

T = TypeVar('T')  # Model type
CreateSchema = TypeVar('CreateSchema', bound=BaseModel)
UpdateSchema = TypeVar('UpdateSchema', bound=BaseModel)

class ICrudService(Generic[T, CreateSchema, UpdateSchema], ABC):
    """Standard CRUD operations interface."""

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
```

### Query Service Interface

```python
class IQueryService(Generic[T], ABC):
    """Standard query operations interface."""

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
```

### Execution Service Interface

```python
class IExecutionService(ABC):
    """Standard execution operations interface."""

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
```

## Parameter Naming Conventions

### Standard Parameter Names

| Concept | Parameter Name | Type | Description |
|---------|---------------|------|-------------|
| Entity ID | `id` | `int` | Primary key identifier |
| String ID | `resource_id` | `str` | String identifier (e.g., run_id) |
| User ID | `user_id` | `int` | User identifier |
| Database session | `db` | `AsyncSession` | Database session |
| Pagination skip | `skip` | `int` | Number of items to skip |
| Pagination limit | `limit` | `int` | Maximum items to return |
| Filters | `filters` | `Dict[str, Any]` | Filter criteria |
| Creation data | `data` | `CreateSchema` | Data for creation |
| Update data | `data` | `UpdateSchema` | Data for update |
| Audit fields | `created_by`, `updated_by`, `deleted_by` | `Optional[int]` | User performing action |
| Soft delete | `include_deleted` | `bool` | Include deleted items |
| Hard delete | `hard_delete` | `bool` | Permanently delete |
| Sorting | `sort_by`, `sort_order` | `Optional[str]`, `str` | Sort field and direction |
| Search | `query` | `str` | Search query string |

## Method Naming Conventions

### CRUD Operations

- `create()` - Create new entity
- `get_by_id()` - Get entity by ID (returns Optional)
- `get_or_404()` - Get entity or raise (returns entity)
- `list()` - List entities with pagination
- `update()` - Update entity
- `delete()` - Delete entity
- `count()` - Count entities

### Query Operations

- `search()` - Text search
- `filter()` - Filter by criteria
- `get_related()` - Get related entities

### Execution Operations

- `execute()` - Execute task
- `get_execution_status()` - Get execution status
- `cancel_execution()` - Cancel execution

### Validation Operations

- `validate()` - Validate data
- `validate_request()` - Validate request
- `check_permission()` - Check permissions

### Status Operations

- `health_check()` - Check service health
- `get_stats()` - Get service statistics

## Error Handling Patterns

### Validation Errors

```python
async def create(self, data: CreateSchema, created_by: Optional[int] = None) -> T:
    # Validate input
    if not data.name:
        raise ValidationError("Name is required", field="name")

    if len(data.name) < 3:
        raise ValidationError(
            "Name must be at least 3 characters",
            field="name",
            details={"min_length": 3, "actual_length": len(data.name)}
        )

    # Check permissions
    if created_by and not await self._can_create(created_by):
        raise PermissionError("Cannot create entity", action="create")

    # Proceed with creation
    ...
```

### Not Found Errors

```python
async def get_or_404(self, id: int, include_deleted: bool = False) -> T:
    entity = await self.get_by_id(id, include_deleted)

    if not entity:
        raise NotFoundError(
            resource=self.__class__.__name__,
            identifier=id
        )

    return entity
```

### Permission Errors

```python
async def update(self, id: int, data: UpdateSchema, updated_by: Optional[int] = None) -> T:
    # Check ownership/permission
    if not await self._can_update(id, updated_by):
        raise PermissionError(
            f"Cannot update entity {id}",
            action="update"
        )

    # Proceed with update
    ...
```

## Service Initialization Patterns

### Standard Constructor

```python
class MyService:
    """Service description."""

    def __init__(
        self,
        db: AsyncSession,
        dependencies: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize service.

        Args:
            db: Database session
            dependencies: Optional dependency dictionary
        """
        self.db = db
        self.dependencies = dependencies or {}

        # Initialize repositories
        self.repository = MyRepository(db)

        # Initialize child services
        self.child_service = ChildService(db)

        # Initialize clients
        self.client = ExternalClient()
```

### Dependency Injection Pattern

```python
class MyService:
    """Service with dependency injection."""

    def __init__(
        self,
        db: AsyncSession,
        repository: Optional[IMyRepository] = None,
        child_service: Optional[IChildService] = None,
        client: Optional[ExternalClient] = None
    ):
        """
        Initialize service with injected dependencies.

        Args:
            db: Database session
            repository: Optional repository (for testing)
            child_service: Optional child service (for testing)
            client: Optional external client (for testing)
        """
        self.db = db
        self.repository = repository or MyRepository(db)
        self.child_service = child_service or ChildService(db)
        self.client = client or ExternalClient()
```

## Logging Patterns

### Standard Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyService:
    """Service with standard logging."""

    async def create(self, data: CreateSchema, created_by: Optional[int] = None) -> T:
        logger.info(
            f"Creating entity with data={data}, created_by={created_by}"
        )

        try:
            result = await self._create_entity(data)
            logger.info(f"Created entity with id={result.id}")
            return result

        except ValidationError as e:
            logger.warning(f"Validation failed: {e.message}")
            raise

        except Exception as e:
            logger.error(f"Failed to create entity: {str(e)}", exc_info=True)
            raise ServiceError(f"Failed to create entity: {str(e)}") from e
```

## Return Type Patterns

### Single Entity

```python
async def get_by_id(self, id: int) -> Optional[T]:
    """Returns entity or None."""
    ...

async def get_or_404(self, id: int) -> T:
    """Returns entity or raises NotFoundError."""
    ...
```

### List with Metadata

```python
async def list(
    self,
    skip: int = 0,
    limit: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> List[T]:
    """Returns list of entities."""
    ...

async def list_with_meta(
    self,
    skip: int = 0,
    limit: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Returns list with metadata."""
    items = await self.list(skip, limit, filters)
    total = await self.count(filters)

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }
```

### Operation Result

```python
async def execute_operation(self, ...) -> Dict[str, Any]:
    """Returns operation result."""
    return {
        "success": True,
        "message": "Operation completed",
        "data": {...},
        "metadata": {
            "duration_ms": 123,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
```

## Examples

### Complete Service Example

```python
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.interface_standards import ICrudService, IService, ServiceError, NotFoundError, ValidationError
from app.models.my_entity import MyEntity
from app.schemas.my_entity import MyEntityCreate, MyEntityUpdate
from app.repositories.my_entity_repository import MyEntityRepository

class MyService(ICrudService[MyEntity, MyEntityCreate, MyEntityUpdate], IService):
    """Service for managing MyEntity."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = MyEntityRepository(db)

    # IService implementation
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Test database connection
            count = await self.repository.count()
            return {
                "healthy": True,
                "status": "healthy",
                "checks": {
                    "database": True,
                    "repository": count >= 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "unhealthy",
                "checks": {"database": False},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_service_name(self) -> str:
        """Get service name."""
        return "MyService"

    def get_service_version(self) -> str:
        """Get service version."""
        return "1.0.0"

    # ICrudService implementation
    async def create(
        self,
        data: MyEntityCreate,
        created_by: Optional[int] = None
    ) -> MyEntity:
        """Create new entity."""
        # Validate
        if not data.name:
            raise ValidationError("Name is required", field="name")

        # Check existence
        existing = await self.repository.find_by_name(data.name)
        if existing:
            raise ValidationError("Name already exists", field="name")

        # Create
        entity = await self.repository.create(data, created_by)
        logger.info(f"Created entity {entity.id}")
        return entity

    async def get_by_id(
        self,
        id: int,
        include_deleted: bool = False
    ) -> Optional[MyEntity]:
        """Get entity by ID."""
        return await self.repository.get_by_id(id, include_deleted)

    async def get_or_404(
        self,
        id: int,
        include_deleted: bool = False
    ) -> MyEntity:
        """Get entity or raise NotFoundError."""
        entity = await self.get_by_id(id, include_deleted)
        if not entity:
            raise NotFoundError("MyEntity", id)
        return entity

    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[MyEntity]:
        """List entities."""
        return await self.repository.list(skip, limit, filters, sort_by, sort_order)

    async def update(
        self,
        id: int,
        data: MyEntityUpdate,
        updated_by: Optional[int] = None
    ) -> MyEntity:
        """Update entity."""
        entity = await self.get_or_404(id)
        return await self.repository.update(entity, data, updated_by)

    async def delete(
        self,
        id: int,
        deleted_by: Optional[int] = None,
        hard_delete: bool = False
    ) -> bool:
        """Delete entity."""
        entity = await self.get_or_404(id)
        return await self.repository.delete(entity, hard_delete, deleted_by)

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count entities."""
        return await self.repository.count(filters)
```

## Migration Guide

### For Existing Services

1. **Add type hints** to all public methods
2. **Standardize return types** - Use Optional for not-found cases
3. **Add validation** - Validate inputs before processing
4. **Improve error handling** - Use specific exception types
5. **Add health check** - Implement `health_check()` method
6. **Document methods** - Add comprehensive docstrings
7. **Add logging** - Log important operations

### Backward Compatibility

When updating existing services:

1. **Keep existing methods** - Mark as deprecated if needed
2. **Add new standard methods** - Alongside existing ones
3. **Use adapters** - Create adapter layer for gradual migration
4. **Update tests** - Ensure tests cover both old and new patterns

## Best Practices

1. **Always use type hints** - For all public methods
2. **Return Optional, not None** - For not-found cases
3. **Use specific exceptions** - Not generic Exception
4. **Validate early** - At method entry point
5. **Log consistently** - Use structured logging
6. **Document thoroughly** - Comprehensive docstrings
7. **Test extensively** - Unit and integration tests
8. **Use dependency injection** - For testability
9. **Keep services focused** - Single responsibility
10. **Use repositories** - For data access
