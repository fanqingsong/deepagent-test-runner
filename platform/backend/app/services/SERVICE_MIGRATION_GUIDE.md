# Service Interface Migration Guide

## Overview

This guide provides step-by-step instructions for migrating existing services to use standardized interfaces following SOLID principles.

## Migration Phases

### Phase 1: Foundation (Week 1-2)

#### Step 1.1: Add Health Check Method

**Before:**
```python
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db
```

**After:**
```python
from app.services.base_service_interface import BaseService, IService
from typing import Dict, Any
from datetime import datetime

class MyService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__("MyService", "1.0.0")
        self.db = db

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Test database connection
            await self.db.execute("SELECT 1")

            return {
                "healthy": True,
                "status": "healthy",
                "checks": {
                    "database": True
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "unhealthy",
                "checks": {
                    "database": False
                },
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
```

#### Step 1.2: Add Service Metadata

**Before:**
```python
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db
```

**After:**
```python
class MyService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__("MyService", "1.0.0")
        self.db = db

    # BaseService already provides get_service_name() and get_service_version()
```

#### Step 1.3: Add Type Hints

**Before:**
```python
async def get_by_id(self, id):
    return await self.db.get(...)
```

**After:**
```python
from typing import Optional
from app.models.my_entity import MyEntity

async def get_by_id(self, id: int) -> Optional[MyEntity]:
    return await self.db.get(...)
```

---

### Phase 2: Error Handling (Week 3)

#### Step 2.1: Replace ValueError with ValidationError

**Before:**
```python
async def create(self, data):
    if not data.get("name"):
        raise ValueError("Name is required")
    return await self.db.create(data)
```

**After:**
```python
from app.services.base_service_interface import ValidationError

async def create(self, data):
    if not data.get("name"):
        raise ValidationError("Name is required", field="name")
    return await self.db.create(data)
```

#### Step 2.2: Replace "Not Found" Errors

**Before:**
```python
async def get_by_id(self, id):
    result = await self.db.get(id)
    if not result:
        raise ValueError(f"Item {id} not found")
    return result
```

**After:**
```python
from app.services.base_service_interface import NotFoundError

async def get_by_id(self, id):
    result = await self.db.get(id)
    if not result:
        raise NotFoundError("Item", id)
    return result
```

Or better, use Optional return:

```python
async def get_by_id(self, id) -> Optional[MyEntity]:
    return await self.db.get(id)
```

#### Step 2.3: Add PermissionError

**Before:**
```python
async def delete(self, id, user_id):
    if user_id != 1:
        raise PermissionError("Only admins can delete")
    return await self.db.delete(id)
```

**After:**
```python
from app.services.base_service_interface import PermissionError

async def delete(self, id, user_id):
    if user_id != 1:
        raise PermissionError(
            "Only admins can delete",
            action="delete"
        )
    return await self.db.delete(id)
```

---

### Phase 3: Return Type Standardization (Week 4-5)

#### Step 3.1: Standardize CRUD Operations

**Before:**
```python
async def list(self, skip=0, limit=50):
    return await self.db.query(...).offset(skip).limit(limit).all()
```

**After:**
```python
from typing import List, Dict, Any, Optional
from app.services.base_service_interface import ICrudService

class MyService(BaseService, ICrudService):
    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[MyEntity]:
        query = self.db.query(...)

        if filters:
            for field, value in filters.items():
                query = query.filter(getattr(MyEntity, field) == value)

        if sort_by:
            order_col = getattr(MyEntity, sort_by)
            query = query.order_by(
                order_col.desc() if sort_order == "desc" else order_col.asc()
            )

        return query.offset(skip).limit(limit).all()
```

#### Step 3.2: Create Response Classes

**Before:**
```python
async def execute(self, task_id, params):
    result = await self.run_task(task_id, params)
    return {
        "task_id": task_id,
        "status": "completed",
        "result": result
    }
```

**After:**
```python
from pydantic import BaseModel

class ExecutionResult(BaseModel):
    task_id: str
    status: str
    result: Any
    error: Optional[str] = None
    duration_ms: int
    timestamp: str

async def execute(self, task_id: str, params: Dict[str, Any]) -> ExecutionResult:
    start_time = datetime.utcnow()

    try:
        result = await self.run_task(task_id, params)
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecutionResult(
            task_id=task_id,
            status="completed",
            result=result,
            error=None,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecutionResult(
            task_id=task_id,
            status="failed",
            result=None,
            error=str(e),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat()
        )
```

---

### Phase 4: Service Adapter Integration (Week 6)

#### Step 4.1: Create Adapter for Legacy Service

**Create adapter file:**
```python
# app/services/adapters/my_service_adapter.py
from app.services.my_service import MyService
from app.services.service_adapter import CrudServiceAdapter

class MyServiceAdapter(CrudServiceAdapter):
    """Adapter for MyService."""

    def __init__(self):
        service = MyService()
        super().__init__(service, "MyService")
```

**Use adapter in API:**
```python
from app.services.adapters.my_service_adapter import MyServiceAdapter

@router.get("/items/{item_id}")
async def get_item(item_id: int):
    adapter = MyServiceAdapter()

    # Now get_by_id returns Optional instead of raising
    item = await adapter.get_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return item
```

#### Step 4.2: Gradual Migration

**Step 1: Create adapter**
```python
from app.services.service_adapter import UniversalServiceAdapter
from app.services.my_service import MyService

# Create adapted service
my_service = UniversalServiceAdapter(MyService(db))
```

**Step 2: Update API endpoints gradually**
```python
# Old way
item = await my_service.get_by_id(item_id)

# New way (with adapter)
item = await my_service.get_by_id(item_id)
if not item:
    raise HTTPException(status_code=404, detail="Not found")
```

**Step 3: Update service implementation**
```python
# Update MyService to implement ICrudService
class MyService(BaseService, ICrudService):
    async def get_by_id(self, id: int) -> Optional[MyEntity]:
        # Already returns Optional
        return await self.db.get(id)
```

**Step 4: Remove adapter**
```python
# Once service is updated, use directly
my_service = MyService(db)
```

---

## Specific Service Migration Examples

### ExecutionService Migration

#### Current Issues:
1. No health check
2. Inconsistent return types
3. Delegates without standard interface

#### Migration Steps:

**Step 1: Add health check**
```python
class ExecutionService(BaseService):
    def __init__(self, db, ...):
        super().__init__("ExecutionService", "1.0.0")
        self.db = db
        # ... rest of initialization

    async def health_check(self) -> Dict[str, Any]:
        checks = {
            "database": False,
            "schedule_resolver": False,
            "status_manager": False
        }

        try:
            # Test database
            await self.db.execute("SELECT 1")
            checks["database"] = True

            # Test dependencies
            if self.schedule_resolver:
                checks["schedule_resolver"] = True

            if self.status_manager:
                checks["status_manager"] = True

            return {
                "healthy": all(checks.values()),
                "status": "healthy" if all(checks.values()) else "degraded",
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "unhealthy",
                "checks": checks,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
```

**Step 2: Standardize return types**
```python
# Create result class
class TestRunResult(BaseModel):
    run_id: str
    status: str
    test_definition_id: Optional[int]
    total_tests: int
    passed_tests: int
    failed_tests: int
    error: Optional[str] = None

async def save_test_results(
    self,
    run_id: str,
    results: Dict[str, Any]
) -> TestRunResult:
    """Save test results with standardized return type."""
    try:
        test_run = await self.result_persister.save_test_results(...)

        return TestRunResult(
            run_id=test_run.run_id,
            status=test_run.status,
            test_definition_id=test_run.test_definition_id,
            total_tests=test_run.total_tests,
            passed_tests=test_run.passed_tests,
            failed_tests=test_run.failed_tests,
            error=test_run.error_message
        )
    except Exception as e:
        raise ServiceError(f"Failed to save results: {str(e)}") from e
```

---

### SuiteService Migration

#### Current Issues:
1. No health check
2. Uses ValueError instead of NotFoundError
3. Mixed return types (model vs dict)

#### Migration Steps:

**Step 1: Replace ValueError**
```python
# Before
async def create_suite_run(self, suite_id: int) -> SuiteRun:
    suite = await self._get_suite(suite_id)
    if not suite:
        raise ValueError(f"Test suite {suite_id} not found")
    # ...

# After
async def create_suite_run(self, suite_id: int) -> SuiteRun:
    suite = await self._get_suite(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", suite_id)
    # ...
```

**Step 2: Standardize execute_suite return**
```python
# Create result class
class SuiteExecutionResult(BaseModel):
    run_id: str
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration_ms: int

async def execute_suite(self, suite_run_id: int) -> SuiteExecutionResult:
    """Execute suite with standardized return type."""
    suite_run = await self._get_suite_run(suite_run_id)
    if not suite_run:
        raise NotFoundError("SuiteRun", suite_run_id)

    # ... execution logic ...

    return SuiteExecutionResult(
        run_id=suite_run.run_id,
        status=suite_run.status,
        total_tests=suite_run.total_tests,
        passed_tests=suite_run.passed,
        failed_tests=suite_run.failed,
        skipped_tests=suite_run.skipped,
        total_duration_ms=suite_run.total_duration
    )
```

---

### ScriptValidationService Migration

#### Current Issues:
1. No health check
2. Returns dict instead of structured response

#### Migration Steps:

**Step 1: Create result class**
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ValidationResult(BaseModel):
    """Standardized validation result."""
    status: str  # "passed", "failed", "error"
    step_results: List[Dict[str, Any]]
    error: Optional[str] = None
    duration_ms: int
    timestamp: str
```

**Step 2: Update method signature**
```python
async def validate_script(
    self,
    script: str,
    url: Optional[str] = None
) -> ValidationResult:
    """Validate script with standardized return type."""
    if not script or not script.strip():
        raise ValidationError("Script cannot be empty")

    start_time = datetime.utcnow()

    try:
        # Execute script
        exec_result = await self._execute_script(script, url)

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ValidationResult(
            status=exec_result.get("status", "failed"),
            step_results=exec_result.get("step_results", []),
            error=exec_result.get("error"),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ValidationResult(
            status="error",
            step_results=[],
            error=str(e),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat()
        )
```

**Step 3: Add health check**
```python
async def health_check(self) -> Dict[str, Any]:
    """Check browser availability."""
    try:
        # Try to launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()

        return {
            "healthy": True,
            "status": "healthy",
            "checks": {
                "browser": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "healthy": False,
            "status": "unhealthy",
            "checks": {
                "browser": False
            },
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Testing Migrated Services

### Unit Tests

```python
import pytest
from app.services.my_service import MyService
from app.services.base_service_interface import NotFoundError, ValidationError

class TestMyService:
    @pytest.fixture
    def service(self, db_session):
        return MyService(db_session)

    @pytest.mark.asyncio
    async def test_create_success(self, service):
        result = await service.create({"name": "Test"})
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_create_validation_error(self, service):
        with pytest.raises(ValidationError) as exc_info:
            await service.create({})

        assert exc_info.value.field == "name"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        result = await service.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        health = await service.health_check()

        assert "healthy" in health
        assert "status" in health
        assert "checks" in health
        assert "timestamp" in health
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_service_with_adapter(db_session):
    # Create adapter
    from app.services.service_adapter import CrudServiceAdapter
    from app.services.my_service import MyService

    legacy_service = MyService(db_session)
    adapter = CrudServiceAdapter(legacy_service)

    # Test adapted methods
    result = await adapter.create({"name": "Test"})
    assert result["name"] == "Test"

    # Test get_by_id returns Optional
    result = await adapter.get_by_id(999)
    assert result is None
```

---

## Backward Compatibility

### Using Adapter Pattern

```python
# Old code still works
item = await my_service.get_item(item_id)

# New code with adapter
adapter = CrudServiceAdapter(my_service)
item = await adapter.get_by_id(item_id)
if not item:
    raise NotFoundError("Item", item_id)
```

### Gradual Rollout

1. **Week 1-2**: Add health check and metadata (no breaking changes)
2. **Week 3**: Update error handling (minimal breaking changes)
3. **Week 4-5**: Standardize return types (use adapters for compatibility)
4. **Week 6**: Remove adapters, update all call sites

---

## Common Pitfalls

### 1. Not Adding Type Hints

**Bad:**
```python
async def get_by_id(self, id):
    return await self.db.get(id)
```

**Good:**
```python
async def get_by_id(self, id: int) -> Optional[MyEntity]:
    return await self.db.get(id)
```

### 2. Not Using Standard Exceptions

**Bad:**
```python
if not item:
    raise ValueError("Item not found")
```

**Good:**
```python
if not item:
    raise NotFoundError("Item", id)
```

### 3. Inconsistent Return Types

**Bad:**
```python
# Sometimes returns model
async def get_item(id):
    return await self.db.get(id)

# Sometimes returns dict
async def execute_task(task_id):
    return {"status": "completed"}
```

**Good:**
```python
# Always returns model
async def get_by_id(id: int) -> Optional[MyEntity]:
    return await self.db.get(id)

# Always returns structured result
async def execute(task_id: str) -> ExecutionResult:
    return ExecutionResult(...)
```

---

## Checklist

For each service migration:

- [ ] Add `IService` implementation (health check, metadata)
- [ ] Add `ICrudService` if service manages entities
- [ ] Add `IQueryService` if service performs queries
- [ ] Add `IExecutionService` if service executes tasks
- [ ] Replace `ValueError` with `ValidationError` for input validation
- [ ] Replace "not found" errors with `NotFoundError`
- [ ] Add `PermissionError` for authorization
- [ ] Standardize method signatures (parameter names, types)
- [ ] Add type hints to all public methods
- [ ] Create response classes for complex returns
- [ ] Add comprehensive unit tests
- [ ] Add integration tests
- [ ] Update API endpoints
- [ ] Update documentation
- [ ] Create migration report

---

## Resources

- **Interface Standards**: `interface_standards.md`
- **Base Interface**: `base_service_interface.py`
- **Service Adapter**: `service_adapter.py`
- **Analysis Report**: `service_interface_analysis.md`
- **Test Examples**: `tests/test_base_service_interface.py`
- **Adapter Tests**: `tests/test_service_adapter.py`

---

## Support

For questions or issues during migration:

1. Check the interface standards documentation
2. Review the analysis report for your service
3. Look at existing migrated services as examples
4. Run tests to ensure compatibility
5. Create adapter for backward compatibility if needed

Remember: Migration is gradual. Use adapters to maintain compatibility while updating services incrementally.
