"""
Repository Pattern Usage Examples

This file provides practical examples of how to use the repository pattern
in the DeepAgent test runner application.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.services.execution_service import ExecutionService
from app.services.result_persister import ResultPersister


async def example_basic_usage():
    """Example: Basic repository usage."""
    # Get repository instance
    repo = RepositoryFactory.get_test_run_repository()

    # You'll need a database session
    # (This is usually provided by FastAPI dependency injection)
    # async with async_session_maker() as db:
    #     test_run = await repo.create(...)


async def example_service_with_repository():
    """Example: Service using repository pattern."""
    # Create service with repository injection
    service = ExecutionService(
        db_session=None,  # Will be provided by FastAPI
        test_run_repository=RepositoryFactory.get_test_run_repository()
    )

    # Service now uses repository for all database operations
    # Benefits:
    # 1. Easy to test (inject mock repository)
    # 2. Follows SOLID principles
    # 3. Can swap database implementation without changing service


async def example_testing_with_mock():
    """Example: Testing with mock repository."""
    from unittest.mock import Mock

    # Create mock repository
    mock_repo = Mock(spec=ITestRunRepository)
    mock_repo.create.return_value = Mock(
        id=1,
        run_id="test-123",
        status="pending"
    )

    # Inject into service
    service = ExecutionService(
        db_session=None,
        test_run_repository=mock_repo
    )

    # Test service logic without database
    # ... test logic ...

    # Verify repository was called
    mock_repo.create.assert_called_once()


async def example_custom_repository():
    """Example: Creating custom repository implementation."""
    from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

    class CachedTestRunRepository(ITestRunRepository):
        """Custom repository with caching layer."""

        def __init__(self, base_repository: ITestRunRepository):
            self.base = base_repository
            self.cache = {}

        async def get_by_id(self, run_id: str, db_session):
            # Check cache first
            if run_id in self.cache:
                return self.cache[run_id]

            # Delegate to base repository
            result = await self.base.get_by_id(run_id, db_session)

            # Store in cache
            if result:
                self.cache[run_id] = result

            return result

        # Implement other methods...

    # Use custom repository
    base_repo = RepositoryFactory.get_test_run_repository()
    cached_repo = CachedTestRunRepository(base_repo)

    RepositoryFactory.set_test_run_repository(cached_repo)


async def example_repository_methods():
    """Example: Available repository methods."""
    repo = RepositoryFactory.get_test_run_repository()

    # Create
    # test_run = await repo.create(
    #     run_id="test-123",
    #     test_definition_id=100,
    #     start_time_ms=1000000,
    #     db_session=db
    # )

    # Retrieve
    # test_run = await repo.get_by_id("test-123", db)

    # Update status
    # updated = await repo.update_status(
    #     run_id="test-123",
    #     status="running",
    #     db_session=db
    # )

    # Update results
    # results = {
    #     'total_tests': 10,
    #     'passed': 8,
    #     'failed': 1,
    #     'skipped': 1,
    #     'status': 'passed'
    # }
    # updated = await repo.update_results("test-123", results, db)

    # Query methods
    # runs = await repo.get_by_test_definition_id(100, db, limit=10)
    # pending = await repo.get_pending_runs(db, limit=100)
    # recent = await repo.get_recent_runs(db, days=7)
    # count = await repo.count_by_status("passed", db)

    # Utility methods
    # exists = await repo.exists("test-123", db)
    # deleted = await repo.delete("test-123", db)
    # all_runs = await repo.get_all(db, limit=50)

    # Statistics
    # from datetime import datetime, timedelta
    # stats = await repo.get_stats_by_date_range(
    #     start_date=datetime.utcnow() - timedelta(days=7),
    #     end_date=datetime.utcnow(),
    #     db_session=db
    # )


async def example_migration_from_direct_db():
    """Example: Migrating from direct database access."""

    # BEFORE: Direct database access (violates DIP)
    # ❌
    # test_run = TestRun(
    #     run_id="test-123",
    #     test_definition_id=100,
    #     status='pending'
    # )
    # self.db.add(test_run)
    # await self.db.commit()
    # await self.db.refresh(test_run)

    # AFTER: Using repository pattern (follows DIP)
    # ✅
    # test_run = await self.test_run_repository.create(
    #     run_id="test-123",
    #     test_definition_id=100,
    #     start_time_ms=1000000,
    #     db_session=self.db
    # )


async def example_error_handling():
    """Example: Error handling with repositories."""
    repo = RepositoryFactory.get_test_run_repository()

    try:
        # Attempt to create test run
        # test_run = await repo.create(...)
        pass
    except ValueError as e:
        # Validation error (e.g., duplicate run_id)
        print(f"Validation error: {e}")
        raise
    except Exception as e:
        # Database error
        print(f"Database error: {e}")
        raise


async def example_transaction_management():
    """Example: Transaction management with repositories."""
    # async with async_session_maker() as db:
    #     try:
    #         # Create test run
    #         test_run = await repo.create(..., db_session=db)
    #
    #         # Update status
    #         await repo.update_status(..., db_session=db)
    #
    #         # All operations succeed - commit
    #         await db.commit()
    #
    #     except Exception as e:
    #         # Error occurs - rollback
    #         await db.rollback()
    #         raise
    pass


# For more information, see:
# platform/backend/app/repositories/README.md
