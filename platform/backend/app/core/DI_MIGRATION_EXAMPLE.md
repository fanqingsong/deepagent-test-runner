"""
DI Container Migration Example

This file shows step-by-step how to migrate existing services
to use the new DI Container system.

Example: Migrating ExecutionService
"""

# ============================================================================
# BEFORE: Manual Dependency Injection (Current State)
# ============================================================================

"""
# app/services/execution_service.py (BEFORE)

from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class ExecutionService:
    def __init__(
        self,
        db_session=None,
        schedule_resolver: Optional[ScheduleResolver] = None,
        status_manager: Optional[RunStatusManager] = None,
        result_persister: Optional[ResultPersister] = None,
        test_run_repository: Optional[ITestRunRepository] = None
    ):
        # Manual dependency creation
        self.db_session = db_session
        self.schedule_resolver = schedule_resolver or ScheduleResolver()
        self.status_manager = status_manager or RunStatusManager()
        self.result_persister = result_persister or ResultPersister()
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()

    async def execute_test(self, test_id: str):
        # Manual dependency usage
        schedule = await self.schedule_resolver.resolve_schedule(...)
        await self.status_manager.update_status(...)
        await self.result_persister.save_results(...)
"""

# ============================================================================
# STEP 1: Update Service Constructor
# ============================================================================

"""
# app/services/execution_service.py (STEP 1)

from typing import Optional
from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

class ExecutionService:
    def __init__(
        self,
        schedule_resolver: ScheduleResolver,  # Required now
        status_manager: RunStatusManager,     # Required now
        result_persister: ResultPersister,    # Required now
        test_run_repository: ITestRunRepository  # Required now
    ):
        # Dependencies injected via constructor
        self.schedule_resolver = schedule_resolver
        self.status_manager = status_manager
        self.result_persister = result_persister
        self.test_run_repository = test_run_repository

    async def execute_test(self, test_id: str):
        # Use injected dependencies (no changes needed)
        schedule = await self.schedule_resolver.resolve_schedule(...)
        await self.status_manager.update_status(...)
        await self.result_persister.save_results(...)
"""

# ============================================================================
# STEP 2: Register in Container
# ============================================================================

"""
# app/core/container.py (STEP 2)

# Add imports
from app.services.execution_service import ExecutionService

# In Container class
class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    # Execution Service (already registered!)
    execution_service = providers.Singleton(
        ExecutionService,
        schedule_resolver=schedule_resolver,
        status_manager=run_status_manager,
        result_persister=result_persister,
        test_run_repository=test_run_repository
    )
"""

# ============================================================================
# STEP 3: Update FastAPI Endpoints
# ============================================================================

"""
# app/api/v1/endpoints/tests.py (STEP 3)

from fastapi import APIRouter, Depends
from app.core.container import DependsExecutionService
from app.services.execution_service import ExecutionService

router = APIRouter()

# BEFORE
@router.post("/tests/{test_id}/execute")
async def execute_test(
    test_id: str,
    db_session: AsyncSession = Depends(get_db)
):
    # Manual service creation
    service = ExecutionService(db_session=db_session)
    return await service.execute_test(test_id)

# AFTER
@router.post("/tests/{test_id}/execute")
async def execute_test(
    test_id: str,
    service: ExecutionService = DependsExecutionService  # Injected!
):
    # Service injected by container
    return await service.execute_test(test_id)
"""

# ============================================================================
# STEP 4: Update Temporal Activities
# ============================================================================

"""
# app/temporal/activities/test_activities.py (STEP 4)

from app.core.container import get_container

async def execute_test_activity(test_id: str) -> Dict:
    # BEFORE: Manual service creation
    # service = ExecutionService(db_session=...)

    # AFTER: Get service from container
    container = get_container()
    service = container.execution_service()

    return await service.execute_test(test_id)
"""

# ============================================================================
# STEP 5: Update Tests
# ============================================================================

"""
# tests/services/test_execution_service.py (STEP 5)

import pytest
from unittest.mock import Mock, AsyncMock
from app.services.execution_service import ExecutionService

# BEFORE: Testing with manual mocks
@pytest.mark.asyncio
async def test_execute_test():
    mock_schedule_resolver = Mock()
    mock_status_manager = Mock()
    mock_result_persister = Mock()
    mock_repository = Mock()

    service = ExecutionService(
        schedule_resolver=mock_schedule_resolver,
        status_manager=mock_status_manager,
        result_persister=mock_result_persister,
        test_run_repository=mock_repository
    )

    result = await service.execute_test("test-123")
    assert result is not None

# AFTER: Can also use container overrides
@pytest.mark.asyncio
async def test_execute_test_with_container():
    from app.core.container import override_provider, reset_provider

    # Create mocks
    mock_service = Mock()
    mock_service.execute_test = AsyncMock(return_value={"id": "test-123"})

    # Override container provider
    override_provider("execution_service", mock_service)

    # Test with mocked service
    container = get_container()
    service = container.execution_service()
    result = await service.execute_test("test-123")

    assert result["id"] == "test-123"
    mock_service.execute_test.assert_called_once()

    # Cleanup
    reset_provider("execution_service")
"""

# ============================================================================
# Complete Migration Checklist
# ============================================================================

MIGRATION_CHECKLIST = """
✅ Step 1: Update service constructor
   - Remove Optional dependencies
   - Remove manual dependency creation
   - Make all dependencies required
   - Use interface types for repositories

✅ Step 2: Register in container (if not already)
   - Add providers.Singleton() call
   - Wire up all dependencies
   - Ensure proper lifecycle (singleton/factory)

✅ Step 3: Update FastAPI endpoints
   - Replace Depends(get_db) with service Depends
   - Use provider functions or aliases
   - Remove manual service creation

✅ Step 4: Update Temporal activities
   - Use get_container() to access services
   - Remove manual service creation
   - Use injected dependencies

✅ Step 5: Update tests
   - Update constructor calls
   - Use container overrides for integration tests
   - Ensure mocks are properly configured

✅ Step 6: Remove old code
   - Remove RepositoryFactory usage
   - Remove manual dependency creation
   - Clean up unused imports
"""

# ============================================================================
# Quick Reference: Common Migration Patterns
# ============================================================================

MIGRATION_PATTERNS = """
Pattern 1: Simple Service Migration
-----------------------------------
BEFORE:
    class MyService:
        def __init__(self, db_session=None):
            self.db_session = db_session
            self.repository = RepositoryFactory.get_my_repository()

AFTER:
    class MyService:
        def __init__(self, my_repository: IMyRepository):
            self.my_repository = my_repository

Pattern 2: Service with Multiple Dependencies
-----------------------------------------------
BEFORE:
    class MyService:
        def __init__(self, db_session=None):
            self.db_session = db_session
            self.repo1 = RepositoryFactory.get_repo1()
            self.repo2 = RepositoryFactory.get_repo2()
            self.helper = HelperService()

AFTER:
    class MyService:
        def __init__(
            self,
            repo1: IRepo1Repository,
            repo2: IRepo2Repository,
            helper: HelperService
        ):
            self.repo1 = repo1
            self.repo2 = repo2
            self.helper = helper

Pattern 3: FastAPI Endpoint Migration
---------------------------------------
BEFORE:
    @router.get("/tests")
    async def get_tests(db: AsyncSession = Depends(get_db)):
        service = MyService(db_session=db)
        return await service.get_all_tests()

AFTER:
    @router.get("/tests")
    async def get_tests(
        service: MyService = Depends(provide_my_service)
    ):
        return await service.get_all_tests()

Pattern 4: Temporal Activity Migration
----------------------------------------
BEFORE:
    async def my_activity(test_id: str):
        service = MyService(db_session=get_db())
        return await service.do_something(test_id)

AFTER:
    async def my_activity(test_id: str):
        container = get_container()
        service = container.my_service()
        return await service.do_something(test_id)
"""

# ============================================================================
# Testing Your Migration
# ============================================================================

TESTING_STEPS = """
1. Unit Tests:
   - Test service logic directly with mocked dependencies
   - Verify constructor receives correct dependencies

2. Integration Tests:
   - Test FastAPI endpoints with container
   - Use provider overrides for mocking

3. Manual Testing:
   - Start application: ./start-dev.sh
   - Check logs for container initialization
   - Test endpoints in browser/API client
   - Verify no "Container not initialized" errors

4. Regression Testing:
   - Run existing test suite
   - Verify all tests pass
   - Check for breaking changes

5. Performance Testing:
   - Monitor container overhead
   - Check for memory leaks
   - Verify singleton behavior
"""

if __name__ == "__main__":
    print("DI Container Migration Example")
    print("=" * 60)
    print(MIGRATION_CHECKLIST)
    print("\n" + "=" * 60)
    print("MIGRATION PATTERNS")
    print("=" * 60)
    print(MIGRATION_PATTERNS)
    print("\n" + "=" * 60)
    print("TESTING STEPS")
    print("=" * 60)
    print(TESTING_STEPS)
