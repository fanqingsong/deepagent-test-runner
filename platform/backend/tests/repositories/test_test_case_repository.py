"""
Unit tests for TestCaseRepository
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.test_generation import GeneratedTestCase, GeneratedTestStep
from app.models.test_definition import TestDefinition


class TestTestCaseRepository:
    """Test suite for TestCaseRepository component."""

    @pytest.fixture
    def db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, db_session):
        """Create TestCaseRepository instance."""
        return TestCaseRepository(db_session)

    @pytest.fixture
    def sample_test_case(self):
        """Create sample generated test case."""
        return GeneratedTestCase(
            name="Test Login",
            description="Test login functionality",
            test_id="TC-TEST-FUNCTIONAL",
            url="https://example.com",
            tags=["smoke", "critical"],
            steps=[
                GeneratedTestStep(
                    step_number=1,
                    description="Navigate to login",
                    type="navigate",
                    params={"url": "https://example.com/login"},
                    expected_result="Login page loads"
                ),
                GeneratedTestStep(
                    step_number=2,
                    description="Enter credentials",
                    type="input",
                    params={"selector": "#username", "value": "test@example.com"},
                    expected_result="Username entered"
                )
            ]
        )

    def test_init(self, repository, db_session):
        """Test initialization."""
        assert repository.db == db_session

    @pytest.mark.asyncio
    async def test_create_test_case_success(self, repository, sample_test_case):
        """Test successful test case creation."""
        # Mock TestDefinition
        mock_test_def = MagicMock()
        mock_test_def.id = 1
        mock_test_def.name = sample_test_case.name

        with patch('app.repositories.test_case_repository.TestDefinition') as MockTestDef:
            MockTestDef.return_value = mock_test_def

            # Mock _create_test_steps
            repository._create_test_steps = AsyncMock()

            test_id = await repository.create_test_case(sample_test_case)

            assert test_id == 1
            repository.db.add.assert_called_once()
            repository.db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_test_case_with_environment(self, repository, sample_test_case):
        """Test test case creation with environment."""
        mock_test_def = MagicMock()
        mock_test_def.id = 1

        with patch('app.repositories.test_case_repository.TestDefinition') as MockTestDef:
            MockTestDef.return_value = mock_test_def
            repository._create_test_steps = AsyncMock()

            environment = {"username": "test", "password": "secret"}
            await repository.create_test_case(sample_test_case, environment=environment)

            # Verify environment was passed to TestDefinition
            MockTestDef.assert_called_once()
            call_kwargs = MockTestDef.call_args[1]
            assert call_kwargs['environment'] == environment

    @pytest.mark.asyncio
    async def test_create_test_case_with_created_by(self, repository, sample_test_case):
        """Test test case creation with created_by user."""
        mock_test_def = MagicMock()
        mock_test_def.id = 1

        with patch('app.repositories.test_case_repository.TestDefinition') as MockTestDef:
            MockTestDef.return_value = mock_test_def
            repository._create_test_steps = AsyncMock()

            await repository.create_test_case(sample_test_case, created_by=123)

            MockTestDef.assert_called_once()
            call_kwargs = MockTestDef.call_args[1]
            assert call_kwargs['created_by'] == 123

    @pytest.mark.asyncio
    async def test_create_test_case_error_rollback(self, repository, sample_test_case):
        """Test that errors trigger rollback."""
        with patch('app.repositories.test_case_repository.TestDefinition') as MockTestDef:
            MockTestDef.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await repository.create_test_case(sample_test_case)

            repository.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_test_steps(self, repository, sample_test_case):
        """Test test steps creation."""
        with patch('app.repositories.test_case_repository.TestStep') as MockTestStep:
            await repository._create_test_steps(1, sample_test_case.steps)

            # Verify TestStep was created for each step
            assert MockTestStep.call_count == len(sample_test_case.steps)
            repository.db.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_test_steps_fallback(self, repository, sample_test_case):
        """Test test steps fallback to test_context."""
        # Mock TestStep import to fail
        with patch('app.repositories.test_case_repository.TestStep', side_effect=ImportError):
            # Mock get_by_id to return test definition
            mock_test_def = MagicMock()
            mock_test_def.test_context = {}
            repository.get_by_id = AsyncMock(return_value=mock_test_def)

            await repository._create_test_steps(1, sample_test_case.steps)

            # Verify steps were stored in test_context
            assert "steps" in mock_test_def.test_context
            assert len(mock_test_def.test_context["steps"]) == len(sample_test_case.steps)

    @pytest.mark.asyncio
    async def test_bulk_create_test_cases(self, repository, sample_test_case):
        """Test bulk creation of test cases."""
        test_cases = [sample_test_case, sample_test_case]

        with patch.object(repository, 'create_test_case', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [1, 2]  # Return IDs 1 and 2

            ids = await repository.bulk_create_test_cases(test_cases)

            assert len(ids) == 2
            assert ids == [1, 2]
            assert mock_create.call_count == 2
            repository.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_error_rollback(self, repository, sample_test_case):
        """Test that bulk creation errors trigger rollback."""
        test_cases = [sample_test_case]

        with patch.object(repository, 'create_test_case', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Creation failed")

            with pytest.raises(Exception):
                await repository.bulk_create_test_cases(test_cases)

            repository.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, db_session):
        """Test getting test definition by ID when found."""
        mock_test_def = MagicMock()
        mock_test_def.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_test_def
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_id(1)

        assert result == mock_test_def

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, db_session):
        """Test getting test definition by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_test_id_found(self, repository, db_session):
        """Test getting test definition by test_id when found."""
        mock_test_def = MagicMock()
        mock_test_def.test_id = "TC-TEST-FUNCTIONAL"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_test_def
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_test_id("TC-TEST-FUNCTIONAL")

        assert result == mock_test_def

    @pytest.mark.asyncio
    async def test_get_by_test_id_not_found(self, repository, db_session):
        """Test getting test definition by test_id when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_test_id("TC-NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_test_case_found(self, repository, db_session):
        """Test updating test definition when found."""
        mock_test_def = MagicMock()
        mock_test_def.id = 1
        mock_test_def.name = "Old Name"

        with patch.object(repository, 'get_by_id', new_callable=AsyncMock, return_value=mock_test_def):
            result = await repository.update_test_case(1, {"name": "New Name"})

            assert result is not None
            assert result.name == "New Name"
            repository.db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_test_case_not_found(self, repository):
        """Test updating test definition when not found."""
        with patch.object(repository, 'get_by_id', new_callable=AsyncMock, return_value=None):
            result = await repository.update_test_case(999, {"name": "New Name"})

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_test_case_found(self, repository, db_session):
        """Test deleting test definition when found."""
        mock_test_def = MagicMock()
        mock_test_def.id = 1

        with patch.object(repository, 'get_by_id', new_callable=AsyncMock, return_value=mock_test_def):
            result = await repository.delete_test_case(1)

            assert result is True
            repository.db.delete.assert_called_once_with(mock_test_def)

    @pytest.mark.asyncio
    async def test_delete_test_case_not_found(self, repository):
        """Test deleting test definition when not found."""
        with patch.object(repository, 'get_by_id', new_callable=AsyncMock, return_value=None):
            result = await repository.delete_test_case(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_list_test_cases(self, repository, db_session):
        """Test listing test cases."""
        mock_test_def1 = MagicMock()
        mock_test_def2 = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_test_def1, mock_test_def2]
        db_session.execute = AsyncMock(return_value=mock_result)

        results = await repository.list_test_cases(limit=10, offset=0)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_test_cases_with_filter(self, repository, db_session):
        """Test listing test cases with is_active filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)

        await repository.list_test_cases(is_active=True)

        # Verify query was executed
        db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_test_cases(self, repository, db_session):
        """Test counting test cases."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        db_session.execute = AsyncMock(return_value=mock_result)

        count = await repository.count_test_cases()

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_test_cases_with_filter(self, repository, db_session):
        """Test counting test cases with filter."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        db_session.execute = AsyncMock(return_value=mock_result)

        count = await repository.count_test_cases(is_active=True)

        assert count == 10

    @pytest.mark.asyncio
    async def test_count_test_cases_error(self, repository, db_session):
        """Test counting test cases on error."""
        db_session.execute = AsyncMock(side_effect=Exception("DB error"))

        count = await repository.count_test_cases()

        assert count == 0
