"""
Test suite for base service interface.

Tests the standard service interfaces, exceptions, and patterns.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.base_service_interface import (
    IService,
    ICrudService,
    IQueryService,
    IExecutionService,
    BaseService,
    ServiceError,
    ValidationError,
    NotFoundError,
    PermissionError,
    ConflictError,
    ServiceResponse,
    ListResponse,
    handle_service_error,
)


# ============================================================================
# Test Service Implementations
# ============================================================================

class DummyService(BaseService):
    """Dummy service for testing."""

    def __init__(self):
        super().__init__("DummyService", "1.0.0")
        self._healthy = True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": self._healthy,
            "status": "healthy" if self._healthy else "unhealthy",
            "checks": {"dummy": self._healthy},
            "timestamp": datetime.utcnow().isoformat()
        }


class DummyCrudService(DummyService, ICrudService):
    """Dummy CRUD service for testing."""

    def __init__(self):
        super().__init__()
        self.items: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    async def create(self, data: Dict[str, Any], created_by: Optional[int] = None) -> Dict[str, Any]:
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")

        item_id = self._next_id
        self.items[item_id] = {
            "id": item_id,
            "name": data["name"],
            "created_by": created_by
        }
        self._next_id += 1
        return self.items[item_id]

    async def get_by_id(self, id: int, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        return self.items.get(id)

    async def get_or_404(self, id: int, include_deleted: bool = False) -> Dict[str, Any]:
        item = await self.get_by_id(id, include_deleted)
        if not item:
            raise NotFoundError("Item", id)
        return item

    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        items = list(self.items.values())
        return items[skip:skip + limit]

    async def update(
        self,
        id: int,
        data: Dict[str, Any],
        updated_by: Optional[int] = None
    ) -> Dict[str, Any]:
        if id not in self.items:
            raise NotFoundError("Item", id)

        self.items[id].update(data)
        self.items[id]["updated_by"] = updated_by
        return self.items[id]

    async def delete(
        self,
        id: int,
        deleted_by: Optional[int] = None,
        hard_delete: bool = False
    ) -> bool:
        if id not in self.items:
            raise NotFoundError("Item", id)

        if hard_delete:
            del self.items[id]
        else:
            self.items[id]["deleted"] = True
            self.items[id]["deleted_by"] = deleted_by

        return True

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        return len(self.items)


class DummyExecutionService(DummyService, IExecutionService):
    """Dummy execution service for testing."""

    def __init__(self):
        super().__init__()
        self.executions: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        task_id: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start_time = datetime.utcnow()

        try:
            # Simulate execution
            result = {
                "task_id": task_id,
                "status": "completed",
                "result": {"output": "success"},
                "error": None,
                "duration_ms": 100,
                "timestamp": datetime.utcnow().isoformat()
            }

            self.executions[task_id] = result
            return result

        except Exception as e:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": str(e),
                "duration_ms": 50,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        if execution_id not in self.executions:
            raise NotFoundError("Execution", execution_id)

        execution = self.executions[execution_id]
        return {
            "execution_id": execution_id,
            "status": execution["status"],
            "progress": 1.0 if execution["status"] == "completed" else 0.5,
            "started_at": execution["timestamp"],
            "updated_at": datetime.utcnow().isoformat(),
            "estimated_completion": None
        }

    async def cancel_execution(self, execution_id: str) -> bool:
        if execution_id not in self.executions:
            raise NotFoundError("Execution", execution_id)

        self.executions[execution_id]["status"] = "cancelled"
        return True


# ============================================================================
# Test Exception Classes
# ============================================================================

class TestServiceError:
    """Test ServiceError exception."""

    def test_service_error_creation(self):
        """Test creating ServiceError."""
        error = ServiceError("Test error", "TEST_ERROR", {"key": "value"})

        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.details == {"key": "value"}

    def test_service_error_to_dict(self):
        """Test converting ServiceError to dict."""
        error = ServiceError("Test error", "TEST_ERROR")
        error_dict = error.to_dict()

        assert error_dict == {
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error",
                "details": {}
            }
        }


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        error = ValidationError("Invalid field", field="name")

        assert error.message == "Invalid field"
        assert error.code == "VALIDATION_ERROR"
        assert error.field == "name"


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_not_found_error_creation(self):
        """Test creating NotFoundError."""
        error = NotFoundError("User", 123)

        assert "User" in error.message
        assert "123" in error.message
        assert error.code == "NOT_FOUND"
        assert error.resource == "User"
        assert error.identifier == 123


class TestPermissionError:
    """Test PermissionError exception."""

    def test_permission_error_creation(self):
        """Test creating PermissionError."""
        error = PermissionError("Cannot delete", action="delete")

        assert error.message == "Cannot delete"
        assert error.code == "PERMISSION_DENIED"
        assert error.action == "delete"


# ============================================================================
# Test BaseService
# ============================================================================

class TestBaseService:
    """Test BaseService implementation."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check method."""
        service = DummyService()
        health = await service.health_check()

        assert health["healthy"] is True
        assert health["status"] == "healthy"
        assert "checks" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when unhealthy."""
        service = DummyService()
        service._healthy = False

        health = await service.health_check()

        assert health["healthy"] is False
        assert health["status"] == "unhealthy"

    def test_get_service_name(self):
        """Test getting service name."""
        service = DummyService()
        assert service.get_service_name() == "DummyService"

    def test_get_service_version(self):
        """Test getting service version."""
        service = DummyService()
        assert service.get_service_version() == "1.0.0"

    def test_log_error(self, caplog):
        """Test error logging."""
        service = DummyService()
        error = Exception("Test error")

        service.log_error(error, {"context": "test"})

        assert "Test error" in caplog.text
        assert "DummyService" in caplog.text


# ============================================================================
# Test ICrudService
# ============================================================================

class TestCrudService:
    """Test CRUD service implementation."""

    @pytest.fixture
    def crud_service(self):
        """Create CRUD service fixture."""
        return DummyCrudService()

    @pytest.mark.asyncio
    async def test_create_success(self, crud_service):
        """Test successful creation."""
        data = {"name": "Test Item"}
        result = await crud_service.create(data, created_by=1)

        assert result["name"] == "Test Item"
        assert result["created_by"] == 1
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_create_validation_error(self, crud_service):
        """Test creation with validation error."""
        data = {}

        with pytest.raises(ValidationError) as exc_info:
            await crud_service.create(data)

        assert "Name is required" in str(exc_info.value)
        assert exc_info.value.field == "name"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, crud_service):
        """Test getting item by ID when found."""
        # Create item first
        created = await crud_service.create({"name": "Test"})

        # Get by ID
        result = await crud_service.get_by_id(created["id"])

        assert result is not None
        assert result["id"] == created["id"]
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, crud_service):
        """Test getting item by ID when not found."""
        result = await crud_service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_404_found(self, crud_service):
        """Test get_or_404 when found."""
        created = await crud_service.create({"name": "Test"})

        result = await crud_service.get_or_404(created["id"])

        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_or_404_not_found(self, crud_service):
        """Test get_or_404 when not found."""
        with pytest.raises(NotFoundError) as exc_info:
            await crud_service.get_or_404(999)

        assert exc_info.value.resource == "Item"
        assert exc_info.value.identifier == 999

    @pytest.mark.asyncio
    async def test_list(self, crud_service):
        """Test listing items."""
        # Create multiple items
        await crud_service.create({"name": "Item 1"})
        await crud_service.create({"name": "Item 2"})
        await crud_service.create({"name": "Item 3"})

        # List all
        items = await crud_service.list()

        assert len(items) == 3

        # List with pagination
        items = await crud_service.list(skip=1, limit=2)

        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_update_success(self, crud_service):
        """Test successful update."""
        created = await crud_service.create({"name": "Original"})

        updated = await crud_service.update(
            created["id"],
            {"name": "Updated"},
            updated_by=2
        )

        assert updated["name"] == "Updated"
        assert updated["updated_by"] == 2

    @pytest.mark.asyncio
    async def test_update_not_found(self, crud_service):
        """Test update when not found."""
        with pytest.raises(NotFoundError):
            await crud_service.update(999, {"name": "Updated"})

    @pytest.mark.asyncio
    async def test_delete_soft(self, crud_service):
        """Test soft delete."""
        created = await crud_service.create({"name": "Test"})

        result = await crud_service.delete(created["id"], deleted_by=1)

        assert result is True
        assert created["id"] in crud_service.items
        assert crud_service.items[created["id"]]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_hard(self, crud_service):
        """Test hard delete."""
        created = await crud_service.create({"name": "Test"})

        result = await crud_service.delete(created["id"], hard_delete=True)

        assert result is True
        assert created["id"] not in crud_service.items

    @pytest.mark.asyncio
    async def test_count(self, crud_service):
        """Test counting items."""
        # Create items
        await crud_service.create({"name": "Item 1"})
        await crud_service.create({"name": "Item 2"})

        count = await crud_service.count()

        assert count == 2


# ============================================================================
# Test IExecutionService
# ============================================================================

class TestExecutionService:
    """Test execution service implementation."""

    @pytest.fixture
    def execution_service(self):
        """Create execution service fixture."""
        return DummyExecutionService()

    @pytest.mark.asyncio
    async def test_execute_success(self, execution_service):
        """Test successful execution."""
        result = await execution_service.execute(
            task_id="task-1",
            parameters={"param": "value"}
        )

        assert result["task_id"] == "task-1"
        assert result["status"] == "completed"
        assert result["error"] is None
        assert "duration_ms" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_execution_status(self, execution_service):
        """Test getting execution status."""
        # Execute first
        await execution_service.execute(task_id="task-1", parameters={})

        # Get status
        status = await execution_service.get_execution_status("task-1")

        assert status["execution_id"] == "task-1"
        assert status["status"] == "completed"
        assert "progress" in status
        assert "timestamp" in status

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, execution_service):
        """Test getting status of non-existent execution."""
        with pytest.raises(NotFoundError):
            await execution_service.get_execution_status("non-existent")

    @pytest.mark.asyncio
    async def test_cancel_execution(self, execution_service):
        """Test cancelling execution."""
        # Execute first
        await execution_service.execute(task_id="task-1", parameters={})

        # Cancel
        result = await execution_service.cancel_execution("task-1")

        assert result is True
        assert execution_service.executions["task-1"]["status"] == "cancelled"


# ============================================================================
# Test Response Wrappers
# ============================================================================

class TestServiceResponse:
    """Test ServiceResponse wrapper."""

    def test_service_response_creation(self):
        """Test creating ServiceResponse."""
        response = ServiceResponse(
            value={"key": "value"},
            success=True,
            message="Operation successful",
            metadata={"duration_ms": 100}
        )

        assert response.value == {"key": "value"}
        assert response.success is True
        assert response.message == "Operation successful"
        assert response.metadata == {"duration_ms": 100}

    def test_service_response_to_dict(self):
        """Test converting ServiceResponse to dict."""
        response = ServiceResponse(value="test")
        response_dict = response.to_dict()

        assert response_dict == {
            "value": "test",
            "success": True,
            "message": None,
            "metadata": {}
        }


class TestListResponse:
    """Test ListResponse wrapper."""

    def test_list_response_creation(self):
        """Test creating ListResponse."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]

        response = ListResponse(
            items=items,
            total=10,
            page=1,
            page_size=3
        )

        assert response.items == items
        assert response.total == 10
        assert response.page == 1
        assert response.page_size == 3

    def test_list_response_has_more(self):
        """Test has_more property."""
        # Has more
        response = ListResponse(items=[1, 2, 3], total=10, page=1, page_size=3)
        assert response.has_more is True

        # No more
        response = ListResponse(items=[1, 2, 3], total=3, page=1, page_size=3)
        assert response.has_more is False

    def test_list_response_to_dict(self):
        """Test converting ListResponse to dict."""
        response = ListResponse(items=[1, 2], total=5, page=1, page_size=2)
        response_dict = response.to_dict()

        assert response_dict == {
            "items": [1, 2],
            "total": 5,
            "page": 1,
            "page_size": 2,
            "has_more": True
        }


# ============================================================================
# Test Utility Functions
# ============================================================================

class TestHandleServiceError:
    """Test handle_service_error utility."""

    def test_handle_service_error_service_error(self):
        """Test handling ServiceError."""
        error = ServiceError("Test error", "TEST_ERROR")
        result = handle_service_error(error, "TestService")

        assert result is error  # ServiceError is returned as-is

    def test_handle_service_error_generic_error(self):
        """Test handling generic exception."""
        error = Exception("Generic error")
        result = handle_service_error(error, "TestService")

        assert isinstance(result, ServiceError)
        assert result.code == "UNEXPECTED_ERROR"
        assert "Generic error" in result.message
