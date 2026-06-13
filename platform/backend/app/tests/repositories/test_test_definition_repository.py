"""
Unit Tests for TestDefinition Repository

Tests the SQLAlchemy implementation of TestDefinition repository
with mocked database sessions.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
from app.models.test_definition import TestDefinition


class TestSQLAlchemyTestDefinitionRepository:
    """Test suite for SQLAlchemyTestDefinitionRepository."""

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return SQLAlchemyTestDefinitionRepository()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.delete = Mock()
        return session

    @pytest.fixture
    def sample_test_definition(self):
        """Create sample test definition."""
        test_def = Mock(spec=TestDefinition)
        test_def.id = 1
        test_def.test_id = "test-001"
        test_def.name = "Sample Test"
        test_def.description = "A sample test definition"
        test_def.url = "https://example.com"
        test_def.environment = {}
        test_def.tags = ["smoke", "regression"]
        test_def.test_goal = "Test login functionality"
        test_def.test_context = {}
        test_def.execution_mode = "script"
        test_def.is_active = True
        test_def.version = 1
        test_def.is_draft = False
        test_def.script_status = "none"
        test_def.script_metadata = {}
        test_def.review_status = "draft"
        test_def.created_at = datetime.utcnow()
        test_def.updated_at = datetime.utcnow()
        return test_def

    @pytest.mark.asyncio
    async def test_create_test_definition(self, repository, mock_db_session, sample_test_definition):
        """Test creating a new test definition."""
        # Mock get_by_test_id to return None (no duplicate)
        repository.get_by_test_id = AsyncMock(return_value=None)

        # Mock the create input
        test_data = Mock()
        test_data.name = "New Test"
        test_data.description = "Test description"
        test_data.test_id = "test-002"
        test_data.url = "https://example.com"
        test_data.environment = {}
        test_data.tags = ["smoke"]
        test_data.test_goal = "Test goal"
        test_data.test_context = {}
        test_data.execution_mode = "script"

        # Execute
        result = await repository.create(test_data, mock_db_session)

        # Verify
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_test_id_raises_error(self, repository, mock_db_session, sample_test_definition):
        """Test that creating duplicate test_id raises ValueError."""
        # Mock get_by_test_id to return existing test
        repository.get_by_test_id = AsyncMock(return_value=sample_test_definition)

        test_data = Mock()
        test_data.test_id = "test-001"  # Duplicate

        # Execute & Assert
        with pytest.raises(ValueError, match="already exists"):
            await repository.create(test_data, mock_db_session)

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definition by ID."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_test_definition
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_id(1, mock_db_session)

        # Verify
        assert result == sample_test_definition
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_test_id(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definition by test_id."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_test_definition
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_test_id("test-001", mock_db_session)

        # Verify
        assert result == sample_test_definition
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definition by name."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_test_definition
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_name("Sample Test", mock_db_session)

        # Verify
        assert result == sample_test_definition
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving all test definitions."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_all(mock_db_session, limit=100, offset=0)

        # Verify
        assert len(result) == 1
        assert result[0] == sample_test_definition
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_db_session, sample_test_definition):
        """Test updating a test definition."""
        # Mock get_by_id to return test definition
        repository.get_by_id = AsyncMock(return_value=sample_test_definition)

        # Execute
        updates = {
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["updated"]
        }
        result = await repository.update(1, updates, mock_db_session)

        # Verify
        assert sample_test_definition.name == "Updated Name"
        assert sample_test_definition.description == "Updated description"
        assert sample_test_definition.tags == ["updated"]
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises_error(self, repository, mock_db_session):
        """Test that updating non-existent test definition raises ValueError."""
        # Mock get_by_id to return None
        repository.get_by_id = AsyncMock(return_value=None)

        # Execute & Assert
        with pytest.raises(ValueError, match="not found"):
            await repository.update(999, {"name": "Updated"}, mock_db_session)

    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_db_session, sample_test_definition):
        """Test deleting a test definition."""
        # Mock get_by_id to return test definition
        repository.get_by_id = AsyncMock(return_value=sample_test_definition)

        # Mock delete to avoid actual deletion
        mock_db_session.delete = Mock()
        mock_db_session.flush = AsyncMock()

        # Execute
        result = await repository.delete(1, mock_db_session)

        # Verify
        assert result is True
        mock_db_session.delete.assert_called_once_with(sample_test_definition)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repository, mock_db_session):
        """Test that deleting non-existent test definition returns False."""
        # Mock get_by_id to return None
        repository.get_by_id = AsyncMock(return_value=None)

        # Execute
        result = await repository.delete(999, mock_db_session)

        # Verify
        assert result is False
        mock_db_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_tag(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definitions by tag."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_tag("smoke", mock_db_session)

        # Verify
        assert len(result) == 1
        assert result[0] == sample_test_definition
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_tags_any_mode(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definitions by tags with 'any' mode."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_tags(
            ["smoke", "regression"],
            mock_db_session,
            match_mode="any"
        )

        # Verify
        assert len(result) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search(self, repository, mock_db_session, sample_test_definition):
        """Test searching test definitions."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.search("login", mock_db_session)

        # Verify
        assert len(result) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(self, repository, mock_db_session):
        """Test counting test definitions."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.count(mock_db_session)

        # Verify
        assert result == 42
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_definitions(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving active test definitions."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_active_definitions(mock_db_session)

        # Verify
        assert len(result) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_by_test_id(self, repository, mock_db_session):
        """Test checking if test definition exists by test_id."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.exists_by_test_id("test-001", mock_db_session)

        # Verify
        assert result is True
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_script(self, repository, mock_db_session, sample_test_definition):
        """Test updating test definition script."""
        # Mock get_by_id to return test definition
        repository.get_by_id = AsyncMock(return_value=sample_test_definition)

        # Execute
        result = await repository.update_script(
            definition_id=1,
            playwright_script="console.log('test')",
            script_status="approved",
            script_metadata={"model": "glm-4"},
            db_session=mock_db_session
        )

        # Verify
        assert sample_test_definition.playwright_script == "console.log('test')"
        assert sample_test_definition.script_status == "approved"
        assert sample_test_definition.script_metadata == {"model": "glm-4"}
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_review_status(self, repository, mock_db_session, sample_test_definition):
        """Test updating test definition review status."""
        # Mock get_by_id to return test definition
        repository.get_by_id = AsyncMock(return_value=sample_test_definition)

        # Execute
        result = await repository.update_review_status(
            definition_id=1,
            review_status="approved",
            reviewed_by=10,
            rejection_reason=None,
            db_session=mock_db_session
        )

        # Verify
        assert sample_test_definition.review_status == "approved"
        assert sample_test_definition.reviewed_by == 10
        assert sample_test_definition.reviewed_at is not None
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_review_status(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving test definitions by review status."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_by_review_status("draft", mock_db_session)

        # Verify
        assert len(result) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_regression_tests(self, repository, mock_db_session, sample_test_definition):
        """Test retrieving regression test definitions."""
        # Mock query result
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_test_definition]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await repository.get_regression_tests(mock_db_session)

        # Verify
        assert len(result) == 1
        mock_db_session.execute.assert_called_once()


class TestTestDefinitionRepositoryInterface:
    """Test that repository properly implements the interface."""

    def test_repository_implements_interface(self):
        """Test that SQLAlchemyTestDefinitionRepository implements ITestDefinitionRepository."""
        from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
        from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository

        # Verify the repository implements the interface
        assert issubclass(SQLAlchemyTestDefinitionRepository, ITestDefinitionRepository)

    def test_interface_has_required_methods(self):
        """Test that interface has all required abstract methods."""
        from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
        import inspect

        # Get abstract methods
        abstract_methods = ITestDefinitionRepository.__abstractmethods__

        # Verify all required methods exist
        required_methods = {
            'create', 'get_by_id', 'get_by_test_id', 'get_by_name',
            'get_all', 'update', 'delete', 'get_by_suite_id',
            'get_by_tag', 'get_by_tags', 'search', 'count',
            'get_active_definitions', 'get_by_workspace_id',
            'get_by_review_status', 'get_regression_tests',
            'exists_by_test_id', 'update_script', 'update_review_status'
        }

        assert abstract_methods == required_methods

    @pytest.mark.asyncio
    async def test_all_methods_are_async(self):
        """Test that all interface methods are async."""
        from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
        import inspect

        # Get all public methods
        methods = [
            name for name, method in inspect.getmembers(ITestDefinitionRepository, predicate=inspect.isfunction)
            if not name.startswith('_')
        ]

        # Verify all methods are async
        for method_name in methods:
            method = getattr(ITestDefinitionRepository, method_name)
            assert inspect.iscoroutinefunction(method), f"Method {method_name} must be async"


class TestRepositoryFactory:
    """Test repository factory functionality."""

    def test_get_test_definition_repository_returns_instance(self):
        """Test that factory returns TestDefinition repository instance."""
        from app.repositories.repository_factory import RepositoryFactory
        from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository

        repo = RepositoryFactory.get_test_definition_repository()

        assert isinstance(repo, ITestDefinitionRepository)
        assert repo is not None

    def test_get_test_definition_repository_singleton(self):
        """Test that factory returns same instance (singleton)."""
        from app.repositories.repository_factory import RepositoryFactory

        repo1 = RepositoryFactory.get_test_definition_repository()
        repo2 = RepositoryFactory.get_test_definition_repository()

        assert repo1 is repo2

    def test_set_custom_test_definition_repository(self):
        """Test setting custom repository implementation."""
        from app.repositories.repository_factory import RepositoryFactory
        from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository

        # Create mock repository
        mock_repo = Mock(spec=ITestDefinitionRepository)

        # Set custom repository
        RepositoryFactory.set_test_definition_repository(mock_repo)

        # Get repository
        repo = RepositoryFactory.get_test_definition_repository()

        # Verify
        assert repo is mock_repo

        # Reset for other tests
        RepositoryFactory.reset()

    def test_reset_clears_repositories(self):
        """Test that reset clears all repository instances."""
        from app.repositories.repository_factory import RepositoryFactory

        # Get repositories
        repo1 = RepositoryFactory.get_test_definition_repository()
        RepositoryFactory.reset()
        repo2 = RepositoryFactory.get_test_definition_repository()

        # Verify different instances after reset
        assert repo1 is not repo2
