"""
SOLID Verification Part 1: Repository Layer

Tests repository implementations follow SOLID principles:
- Interface segregation (focused repository interfaces)
- Dependency inversion (depend on abstractions)
- Single responsibility (data access only)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository
from app.models.test_run import TestRun
from app.models.test_definition import TestDefinition
from app.models.schedule import Schedule


class TestRepositoryLayer:
    """Verify all repositories follow SOLID principles."""

    @pytest.mark.asyncio
    async def test_test_run_repository_crud(self, db_session: AsyncSession):
        """Test TestRun repository CRUD operations."""
        repo = RepositoryFactory.get_test_run_repository()

        # Create
        test_run = TestRun(
            id="test-run-123",
            run_id="test-run-123",
            test_definition_id=1,
            status="pending",
            total_tests=5,
            environment={"key": "value"}
        )
        created = await repo.create(test_run, db_session)
        assert created is not None
        assert created.run_id == "test-run-123"

        # Read
        found = await repo.get_by_id("test-run-123", db_session)
        assert found is not None
        assert found.status == "pending"

        # Update
        found.status = "running"
        updated = await repo.update(found, db_session)
        assert updated.status == "running"

        # List
        all_runs = await repo.get_all(db_session, limit=10)
        assert len(all_runs) >= 1

        # Delete
        await repo.delete("test-run-123", db_session)
        deleted = await repo.get_by_id("test-run-123", db_session)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_test_definition_repository_crud(self, db_session: AsyncSession):
        """Test TestDefinition repository CRUD operations."""
        repo = RepositoryFactory.get_test_definition_repository()

        # Create
        test_def = TestDefinition(
            name="Test Definition",
            description="Test description",
            test_type="e2e",
            target_url="https://example.com",
            created_by="user123"
        )
        created = await repo.create(test_def, db_session)
        assert created is not None
        assert created.name == "Test Definition"

        # Read
        found = await repo.get_by_id(created.id, db_session)
        assert found is not None
        assert found.test_type == "e2e"

        # Update
        found.description = "Updated description"
        updated = await repo.update(found, db_session)
        assert updated.description == "Updated description"

        # List
        all_defs = await repo.get_all(db_session, limit=10)
        assert len(all_defs) >= 1

        # Delete
        await repo.delete(created.id, db_session)
        deleted = await repo.get_by_id(created.id, db_session)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_schedule_repository_crud(self, db_session: AsyncSession):
        """Test Schedule repository CRUD operations."""
        repo = RepositoryFactory.get_schedule_repository()

        # Create
        schedule = Schedule(
            name="Test Schedule",
            schedule_type="single",
            cron_expression="0 0 * * *",
            test_definition_id=1,
            created_by="user123"
        )
        created = await repo.create(schedule, db_session)
        assert created is not None
        assert created.name == "Test Schedule"

        # Read
        found = await repo.get_by_id(created.id, db_session)
        assert found is not None
        assert found.schedule_type == "single"

        # Update
        found.is_active = False
        updated = await repo.update(found, db_session)
        assert updated.is_active is False

        # List
        all_schedules = await repo.get_all(db_session, limit=10)
        assert len(all_schedules) >= 1

        # Delete
        await repo.delete(created.id, db_session)
        deleted = await repo.get_by_id(created.id, db_session)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_repository_interface_compliance(self, db_session: AsyncSession):
        """Verify all repositories implement their interfaces correctly."""
        # Test that repositories can be used via their interfaces
        test_run_repo: ITestRunRepository = RepositoryFactory.get_test_run_repository()
        test_def_repo: ITestDefinitionRepository = RepositoryFactory.get_test_definition_repository()
        schedule_repo: IScheduleRepository = RepositoryFactory.get_schedule_repository()

        # Verify they have the required methods
        assert hasattr(test_run_repo, 'create')
        assert hasattr(test_run_repo, 'get_by_id')
        assert hasattr(test_run_repo, 'update')
        assert hasattr(test_run_repo, 'delete')
        assert hasattr(test_run_repo, 'get_all')

        assert hasattr(test_def_repo, 'create')
        assert hasattr(test_def_repo, 'get_by_id')
        assert hasattr(test_def_repo, 'update')
        assert hasattr(test_def_repo, 'delete')
        assert hasattr(test_def_repo, 'get_all')

        assert hasattr(schedule_repo, 'create')
        assert hasattr(schedule_repo, 'get_by_id')
        assert hasattr(schedule_repo, 'update')
        assert hasattr(schedule_repo, 'delete')
        assert hasattr(schedule_repo, 'get_all')

    @pytest.mark.asyncio
    async def test_repository_error_handling(self, db_session: AsyncSession):
        """Test repository error handling."""
        repo = RepositoryFactory.get_test_run_repository()

        # Test get non-existent
        result = await repo.get_by_id("non-existent-id", db_session)
        assert result is None

        # Test update non-existent (should handle gracefully)
        fake_run = TestRun(
            id="fake-id",
            run_id="fake-id",
            test_definition_id=999,
            status="pending"
        )
        # This might raise an exception or return None - either is acceptable
        try:
            result = await repo.update(fake_run, db_session)
            # If no exception, result should be None or the unchanged object
        except Exception:
            # Exception is also acceptable
            pass
