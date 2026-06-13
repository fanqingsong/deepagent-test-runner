"""
Test suite for service adapter.

Tests the adapter pattern implementation for gradual service migration.
"""

import pytest
from typing import Dict, Any, List, Optional

from app.services.base_service_interface import (
    ServiceError,
    ValidationError,
    NotFoundError,
)
from app.services.service_adapter import (
    ServiceAdapter,
    CrudServiceAdapter,
    ExecutionServiceAdapter,
    QueryServiceAdapter,
    HealthCheckAdapter,
    UniversalServiceAdapter,
    create_adapter,
    AdapterContext,
    ServiceMigrationHelper,
)


# ============================================================================
# Mock Services for Testing
# ============================================================================

class LegacyCrudService:
    """Legacy service with non-standard interface."""

    def __init__(self):
        self.items: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Legacy method - returns None or raises Exception."""
        item = self.items.get(id)
        if not item:
            raise Exception("Item not found")
        return item

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - no validation."""
        item_id = self._next_id
        self.items[item_id] = {"id": item_id, **data}
        self._next_id += 1
        return self.items[item_id]

    async def update(self, id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - raises Exception if not found."""
        if id not in self.items:
            raise Exception(f"Item {id} not found")
        self.items[id].update(data)
        return self.items[id]

    async def delete(self, id: int) -> None:
        """Legacy method - returns None."""
        if id in self.items:
            del self.items[id]


class LegacyExecutionService:
    """Legacy execution service with non-standard interface."""

    def __init__(self):
        self.executions: Dict[str, Any] = {}

    async def execute(self, task_id: str, params: Dict[str, Any]) -> Any:
        """Legacy method - returns raw result."""
        # Simulate execution
        result = {"output": "success", "task_id": task_id}
        self.executions[task_id] = result
        return result

    async def get_status(self, run_id: str) -> str:
        """Legacy method - returns status string."""
        if run_id not in self.executions:
            raise Exception("Execution not found")
        return "completed"


class LegacyQueryService:
    """Legacy query service with non-standard interface."""

    def __init__(self):
        self.data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]

    async def list(self, offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Legacy method - uses offset instead of skip."""
        return self.data[offset:offset + limit]

    async def search(self, q: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Legacy method - uses q instead of query."""
        results = [item for item in self.data if q in item.get("name", "")]
        return results[:max_results]


class LegacyHealthCheckService:
    """Legacy service with non-standard health check."""

    def __init__(self):
        self._healthy = True

    async def health_check(self) -> bool:
        """Legacy method - returns bool."""
        return self._healthy


# ============================================================================
# Test ServiceAdapter Base Class
# ============================================================================

class TestServiceAdapter:
    """Test base ServiceAdapter functionality."""

    def test_init(self):
        """Test adapter initialization."""
        service = LegacyCrudService()
        adapter = ServiceAdapter(service, "TestService")

        assert adapter.service is service
        assert adapter.service_name == "TestService"

    def test_init_default_name(self):
        """Test adapter with default service name."""
        service = LegacyCrudService()
        adapter = ServiceAdapter(service)

        assert adapter.service_name == "LegacyCrudService"

    def test_proxy_attributes(self):
        """Test that adapter proxies undefined attributes."""
        service = LegacyCrudService()
        adapter = ServiceAdapter(service)

        # Access service attribute through adapter
        assert hasattr(adapter, 'items')
        assert adapter.items == service.items


# ============================================================================
# Test CrudServiceAdapter
# ============================================================================

class TestCrudServiceAdapter:
    """Test CRUD service adapter."""

    @pytest.fixture
    def legacy_service(self):
        """Create legacy service fixture."""
        return LegacyCrudService()

    @pytest.fixture
    def adapter(self, legacy_service):
        """Create adapter fixture."""
        return CrudServiceAdapter(legacy_service)

    @pytest.mark.asyncio
    async def test_adapt_get_by_id_returns_optional(self, adapter):
        """Test that get_by_id returns Optional instead of raising."""
        # Create item first
        legacy = adapter.service
        await legacy.create({"name": "Test"})

        # Found case
        result = await adapter.get_by_id(1)
        assert result is not None
        assert result["id"] == 1

        # Not found case - should return None, not raise
        result = await adapter.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_adapt_create_validates_input(self, adapter):
        """Test that create validates input."""
        legacy = adapter.service

        # Valid data
        result = await adapter.create({"name": "Test"})
        assert result["name"] == "Test"

        # Missing data - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await adapter.create({})

        assert "Data is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_adapt_update_handles_not_found(self, adapter):
        """Test that update raises NotFoundError instead of generic Exception."""
        legacy = adapter.service

        # Create item first
        created = await legacy.create({"name": "Test"})

        # Update existing - should work
        result = await adapter.update(created["id"], {"name": "Updated"})
        assert result["name"] == "Updated"

        # Update non-existent - should raise NotFoundError
        with pytest.raises(NotFoundError) as exc_info:
            await adapter.update(999, {"name": "Updated"})

        assert exc_info.value.resource == "LegacyCrudService"
        assert exc_info.value.identifier == 999

    @pytest.mark.asyncio
    async def test_adapt_delete_returns_bool(self, adapter):
        """Test that delete returns bool instead of None."""
        legacy = adapter.service

        # Create item first
        created = await legacy.create({"name": "Test"})

        # Delete existing - should return True
        result = await adapter.delete(created["id"])
        assert result is True

        # Delete non-existent - should return False
        result = await adapter.delete(999)
        assert result is False


# ============================================================================
# Test ExecutionServiceAdapter
# ============================================================================

class TestExecutionServiceAdapter:
    """Test execution service adapter."""

    @pytest.fixture
    def legacy_service(self):
        """Create legacy service fixture."""
        return LegacyExecutionService()

    @pytest.fixture
    def adapter(self, legacy_service):
        """Create adapter fixture."""
        return ExecutionServiceAdapter(legacy_service)

    @pytest.mark.asyncio
    async def test_adapt_execute_standardizes_result(self, adapter):
        """Test that execute returns standardized result."""
        result = await adapter.execute(
            task_id="task-1",
            parameters={"param": "value"}
        )

        # Check standard fields
        assert "task_id" in result
        assert "status" in result
        assert "result" in result
        assert "error" in result
        assert "duration_ms" in result
        assert "timestamp" in result

        assert result["task_id"] == "task-1"
        assert result["status"] == "completed"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_adapt_execute_handles_error(self, adapter):
        """Test that execute handles errors gracefully."""
        # Make execute fail
        async def failing_execute(*args, **kwargs):
            raise Exception("Execution failed")

        adapter.service.execute = failing_execute

        result = await adapter.execute(
            task_id="task-fail",
            parameters={}
        )

        assert result["status"] == "failed"
        assert result["error"] == "Execution failed"
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_adapt_get_execution_status(self, adapter):
        """Test get_execution_status standardization."""
        # Execute first
        await adapter.execute(task_id="task-1", parameters={})

        # Get status
        status = await adapter.get_execution_status("task-1")

        # Check standard fields
        assert "execution_id" in status
        assert "status" in status
        assert "progress" in status
        assert "started_at" in status
        assert "updated_at" in status

        assert status["execution_id"] == "task-1"

    @pytest.mark.asyncio
    async def test_adapt_get_execution_status_aliases(self, adapter):
        """Test that get_status is aliased to get_execution_status."""
        # Execute first
        await adapter.execute(task_id="task-1", parameters={})

        # Should have both methods
        assert hasattr(adapter, 'get_execution_status')
        assert hasattr(adapter, 'get_status')

        # Both should return same result
        status1 = await adapter.get_execution_status("task-1")
        status2 = await adapter.get_status("task-1")

        assert status1["execution_id"] == status2["execution_id"]


# ============================================================================
# Test QueryServiceAdapter
# ============================================================================

class TestQueryServiceAdapter:
    """Test query service adapter."""

    @pytest.fixture
    def legacy_service(self):
        """Create legacy service fixture."""
        return LegacyQueryService()

    @pytest.fixture
    def adapter(self, legacy_service):
        """Create adapter fixture."""
        return QueryServiceAdapter(legacy_service)

    @pytest.mark.asyncio
    async def test_adapt_list_normalizes_parameters(self, adapter):
        """Test that list normalizes parameter names."""
        # Use offset instead of skip
        result = await adapter.list(skip=1, limit=2)

        assert len(result) == 2
        assert result[0]["id"] == 2  # Skipped first item

    @pytest.mark.asyncio
    async def test_adapt_list_returns_list(self, adapter):
        """Test that list always returns a list."""
        result = await adapter.list(skip=0, limit=2)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_adapt_search_normalizes_parameters(self, adapter):
        """Test that search normalizes parameter names."""
        # Use query instead of q
        result = await adapter.search(query="Item", limit=10)

        assert isinstance(result, list)
        assert len(result) == 3  # All items match


# ============================================================================
# Test HealthCheckAdapter
# ============================================================================

class TestHealthCheckAdapter:
    """Test health check adapter."""

    @pytest.fixture
    def legacy_service(self):
        """Create legacy service fixture."""
        return LegacyHealthCheckService()

    @pytest.fixture
    def adapter(self, legacy_service):
        """Create adapter fixture."""
        return HealthCheckAdapter(legacy_service)

    @pytest.mark.asyncio
    async def test_adapt_health_check_standardizes_result(self, adapter):
        """Test that health_check returns standardized result."""
        result = await adapter.health_check()

        # Check standard fields
        assert "healthy" in result
        assert "status" in result
        assert "checks" in result
        assert "timestamp" in result

        assert result["healthy"] is True
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_adapt_health_check_handles_error(self, adapter):
        """Test that health_check handles errors."""
        # Make health check fail
        async def failing_health_check(*args, **kwargs):
            raise Exception("Health check failed")

        adapter.service.health_check = failing_health_check

        result = await adapter.health_check()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"
        assert "error" in result


# ============================================================================
# Test UniversalServiceAdapter
# ============================================================================

class TestUniversalServiceAdapter:
    """Test universal service adapter."""

    @pytest.fixture
    def crud_service(self):
        """Create CRUD service fixture."""
        return LegacyCrudService()

    @pytest.fixture
    def execution_service(self):
        """Create execution service fixture."""
        return LegacyExecutionService()

    @pytest.mark.asyncio
    async def test_universal_adapter_crud(self, crud_service):
        """Test universal adapter with CRUD service."""
        adapter = UniversalServiceAdapter(crud_service)

        # Should have CRUD adaptations
        result = await adapter.get_by_id(999)
        assert result is None  # Returns Optional

        # Should have health check
        health = await adapter.health_check()
        assert "healthy" in health

    @pytest.mark.asyncio
    async def test_universal_adapter_execution(self, execution_service):
        """Test universal adapter with execution service."""
        adapter = UniversalServiceAdapter(execution_service)

        # Should have execution adaptations
        result = await adapter.execute(task_id="task-1", parameters={})
        assert "status" in result

        # Should have health check
        health = await adapter.health_check()
        assert "healthy" in health


# ============================================================================
# Test Adapter Factory
# ============================================================================

class TestCreateAdapter:
    """Test adapter factory function."""

    def test_create_universal_adapter(self):
        """Test creating universal adapter."""
        service = LegacyCrudService()
        adapter = create_adapter(service, "universal")

        assert isinstance(adapter, UniversalServiceAdapter)

    def test_create_crud_adapter(self):
        """Test creating CRUD adapter."""
        service = LegacyCrudService()
        adapter = create_adapter(service, "crud")

        assert isinstance(adapter, CrudServiceAdapter)

    def test_create_adapter_default_type(self):
        """Test creating adapter with default type."""
        service = LegacyCrudService()
        adapter = create_adapter(service)

        # Should default to universal
        assert isinstance(adapter, UniversalServiceAdapter)


# ============================================================================
# Test AdapterContext
# ============================================================================

class TestAdapterContext:
    """Test adapter context manager."""

    @pytest.mark.asyncio
    async def test_adapter_context(self):
        """Test using adapter context manager."""
        service = LegacyCrudService()

        async with AdapterContext(service, "crud") as adapter:
            assert isinstance(adapter, CrudServiceAdapter)

            # Use adapted method
            result = await adapter.get_by_id(999)
            assert result is None

    @pytest.mark.asyncio
    async def test_adapter_context_cleanup(self):
        """Test that adapter is cleaned up after context."""
        service = LegacyCrudService()

        async with AdapterContext(service) as adapter:
            temp_adapter = adapter

        # Adapter should be None after exiting context
        assert temp_adapter.service is service  # But service reference remains


# ============================================================================
# Test ServiceMigrationHelper
# ============================================================================

class TestServiceMigrationHelper:
    """Test service migration helper."""

    def test_analyze_service(self):
        """Test service analysis."""
        service = LegacyCrudService()
        analysis = ServiceMigrationHelper.analyze_service(service)

        assert "service_name" in analysis
        assert "methods" in analysis
        assert "total_methods" in analysis

        assert analysis["service_name"] == "LegacyCrudService"
        assert len(analysis["methods"]) > 0

        # Check method details
        method_info = analysis["methods"]["get_by_id"]
        assert "signature" in method_info
        assert "parameters" in method_info
        assert "is_async" in method_info

    def test_generate_migration_report(self):
        """Test migration report generation."""
        from app.services.base_service_interface import ICrudService

        old_service = LegacyCrudService()
        report = ServiceMigrationHelper.generate_migration_report(
            old_service,
            ICrudService
        )

        assert "service_name" in report
        assert "matching_methods" in report
        assert "missing_methods" in report
        assert "extra_methods" in report
        assert "migration_required" in report
        assert "adapter_recommended" in report

        # LegacyCrudService has some matching methods
        assert len(report["matching_methods"]) > 0


# ============================================================================
# Test Integration
# ============================================================================

class TestAdapterIntegration:
    """Test adapter integration scenarios."""

    @pytest.mark.asyncio
    async def test_crud_workflow(self):
        """Test complete CRUD workflow with adapter."""
        legacy = LegacyCrudService()
        adapter = CrudServiceAdapter(legacy)

        # Create
        created = await adapter.create({"name": "Test"})
        assert created["name"] == "Test"

        # Read
        result = await adapter.get_by_id(created["id"])
        assert result is not None
        assert result["name"] == "Test"

        # Update
        updated = await adapter.update(created["id"], {"name": "Updated"})
        assert updated["name"] == "Updated"

        # Delete
        deleted = await adapter.delete(created["id"])
        assert deleted is True

        # Verify deletion
        result = await adapter.get_by_id(created["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_execution_workflow(self):
        """Test complete execution workflow with adapter."""
        legacy = LegacyExecutionService()
        adapter = ExecutionServiceAdapter(legacy)

        # Execute
        result = await adapter.execute(
            task_id="task-1",
            parameters={"param": "value"}
        )
        assert result["status"] == "completed"

        # Get status
        status = await adapter.get_execution_status("task-1")
        assert status["execution_id"] == "task-1"

        # Cancel
        cancelled = await adapter.cancel_execution("task-1")
        assert cancelled is True

    @pytest.mark.asyncio
    async def test_query_workflow(self):
        """Test complete query workflow with adapter."""
        legacy = LegacyQueryService()
        adapter = QueryServiceAdapter(legacy)

        # List
        items = await adapter.list(skip=0, limit=2)
        assert len(items) == 2

        # Search
        results = await adapter.search(query="Item")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_multi_adapter_service(self):
        """Test service that implements multiple interfaces."""
        # Create a service that has both CRUD and execution methods
        class MultiService:
            def __init__(self):
                self.items = {}
                self.executions = {}

            async def create(self, data):
                return {"id": 1, **data}

            async def execute(self, task_id, params):
                return {"task_id": task_id, "status": "completed"}

        service = MultiService()
        adapter = UniversalServiceAdapter(service)

        # Should work with both interfaces
        result = await adapter.create({"name": "Test"})
        assert result["name"] == "Test"

        result = await adapter.execute(task_id="task-1", parameters={})
        assert result["status"] == "completed"
