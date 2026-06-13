"""
Integration Tests for TestDefinition Repository

Tests the SQLAlchemy implementation with real database sessions.
These tests require a test database to be available.
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository
from app.models.test_definition import TestDefinition
from app.schemas.test_definition import TestDefinitionCreate


@pytest.mark.integration
class TestTestDefinitionRepositoryIntegration:
    """Integration tests for TestDefinition repository with real database."""

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return SQLAlchemyTestDefinitionRepository()

    @pytest.mark.asyncio
    async def test_create_and_get_test_definition(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test creating and retrieving a test definition."""
        # Create test data
        test_data = TestDefinitionCreate(
            name="Integration Test",
            description="Integration test description",
            test_id="int-test-001",
            url="https://example.com",
            environment={"key": "value"},
            tags=["integration", "test"],
            test_goal="Test integration",
            test_context={"context": "data"}
        )

        # Create test definition
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Verify creation
        assert created.id is not None
        assert created.name == "Integration Test"
        assert created.test_id == "int-test-001"
        assert created.tags == ["integration", "test"]

        # Retrieve by ID
        retrieved = await repository.get_by_id(created.id, test_db_session)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Integration Test"

        # Retrieve by test_id
        by_test_id = await repository.get_by_test_id("int-test-001", test_db_session)
        assert by_test_id is not None
        assert by_test_id.id == created.id

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving all test definitions with pagination."""
        # Create multiple test definitions
        for i in range(5):
            test_data = TestDefinitionCreate(
                name=f"Test {i}",
                description=f"Test description {i}",
                test_id=f"test-00{i}",
                tags=["test"]
            )
            await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Test pagination
        page1 = await repository.get_all(test_db_session, limit=2, offset=0)
        page2 = await repository.get_all(test_db_session, limit=2, offset=2)
        page3 = await repository.get_all(test_db_session, limit=2, offset=4)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) <= 1

    @pytest.mark.asyncio
    async def test_update_test_definition(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test updating a test definition."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="Original Name",
            test_id="update-test-001",
            tags=["original"]
        )
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Update
        updated = await repository.update(
            created.id,
            {
                "name": "Updated Name",
                "description": "Updated description",
                "tags": ["updated"]
            },
            test_db_session
        )
        await test_db_session.commit()

        # Verify update
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.tags == ["updated"]

    @pytest.mark.asyncio
    async def test_delete_test_definition(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test deleting a test definition."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="To Delete",
            test_id="delete-test-001"
        )
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Delete
        result = await repository.delete(created.id, test_db_session)
        await test_db_session.commit()

        # Verify deletion
        assert result is True
        retrieved = await repository.get_by_id(created.id, test_db_session)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_tag(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving test definitions by tag."""
        # Create test definitions with different tags
        test1 = TestDefinitionCreate(name="Test 1", test_id="tag-test-001", tags=["smoke"])
        test2 = TestDefinitionCreate(name="Test 2", test_id="tag-test-002", tags=["regression"])
        test3 = TestDefinitionCreate(name="Test 3", test_id="tag-test-003", tags=["smoke", "regression"])

        await repository.create(test1, test_db_session)
        await repository.create(test2, test_db_session)
        await repository.create(test3, test_db_session)
        await test_db_session.commit()

        # Get by tag
        smoke_tests = await repository.get_by_tag("smoke", test_db_session)
        regression_tests = await repository.get_by_tag("regression", test_db_session)

        assert len(smoke_tests) == 2
        assert len(regression_tests) == 2

    @pytest.mark.asyncio
    async def test_search_test_definitions(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test searching test definitions."""
        # Create test definitions
        test1 = TestDefinitionCreate(
            name="Login Test",
            test_id="search-001",
            description="Test login functionality"
        )
        test2 = TestDefinitionCreate(
            name="Logout Test",
            test_id="search-002",
            description="Test logout functionality"
        )
        test3 = TestDefinitionCreate(
            name="Profile Test",
            test_id="search-003",
            description="Test profile management"
        )

        await repository.create(test1, test_db_session)
        await repository.create(test2, test_db_session)
        await repository.create(test3, test_db_session)
        await test_db_session.commit()

        # Search for "login"
        results = await repository.search("login", test_db_session)
        assert len(results) == 1
        assert "login" in results[0].name.lower() or "login" in results[0].description.lower()

    @pytest.mark.asyncio
    async def test_count_test_definitions(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test counting test definitions."""
        # Initial count
        initial_count = await repository.count(test_db_session)

        # Create test definitions
        for i in range(3):
            test_data = TestDefinitionCreate(
                name=f"Count Test {i}",
                test_id=f"count-test-00{i}"
            )
            await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Verify count increased
        new_count = await repository.count(test_db_session)
        assert new_count == initial_count + 3

    @pytest.mark.asyncio
    async def test_get_active_definitions(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving active test definitions."""
        # Create active and inactive definitions
        active1 = TestDefinitionCreate(name="Active 1", test_id="active-001")
        active2 = TestDefinitionCreate(name="Active 2", test_id="active-002")

        created1 = await repository.create(active1, test_db_session)
        created2 = await repository.create(active2, test_db_session)

        # Make one inactive
        await repository.update(created1.id, {"is_active": False}, test_db_session)
        await test_db_session.commit()

        # Get active definitions
        active = await repository.get_active_definitions(test_db_session)

        # Should only return active definitions
        assert all(td.is_active for td in active)

    @pytest.mark.asyncio
    async def test_update_script(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test updating test definition script."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="Script Test",
            test_id="script-001"
        )
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Update script
        script = "console.log('test');"
        updated = await repository.update_script(
            created.id,
            script,
            "approved",
            {"model": "glm-4"},
            test_db_session
        )
        await test_db_session.commit()

        # Verify
        assert updated.playwright_script == script
        assert updated.script_status == "approved"
        assert updated.script_metadata == {"model": "glm-4"}

    @pytest.mark.asyncio
    async def test_update_review_status(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test updating review status."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="Review Test",
            test_id="review-001"
        )
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Update review status
        updated = await repository.update_review_status(
            created.id,
            "approved",
            reviewed_by=1,
            rejection_reason=None,
            db_session=test_db_session
        )
        await test_db_session.commit()

        # Verify
        assert updated.review_status == "approved"
        assert updated.reviewed_by == 1
        assert updated.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_get_by_review_status(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving test definitions by review status."""
        # Create test definitions with different review statuses
        test1 = TestDefinitionCreate(name="Draft Test", test_id="review-status-001")
        test2 = TestDefinitionCreate(name="Approved Test", test_id="review-status-002")

        created1 = await repository.create(test1, test_db_session)
        created2 = await repository.create(test2, test_db_session)

        # Update review status
        await repository.update_review_status(created2.id, "approved", reviewed_by=1, db_session=test_db_session)
        await test_db_session.commit()

        # Get by review status
        draft_tests = await repository.get_by_review_status("draft", test_db_session)
        approved_tests = await repository.get_by_review_status("approved", test_db_session)

        assert len(draft_tests) >= 1
        assert len(approved_tests) >= 1

    @pytest.mark.asyncio
    async def test_get_by_tags_match_mode_all(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving test definitions by tags with 'all' match mode."""
        # Create test definitions
        test1 = TestDefinitionCreate(name="Both Tags", test_id="match-001", tags=["smoke", "regression"])
        test2 = TestDefinitionCreate(name="One Tag", test_id="match-002", tags=["smoke"])

        await repository.create(test1, test_db_session)
        await repository.create(test2, test_db_session)
        await test_db_session.commit()

        # Get with 'all' mode - should only return test with both tags
        results = await repository.get_by_tags(
            ["smoke", "regression"],
            test_db_session,
            match_mode="all"
        )

        assert len(results) == 1
        assert set(results[0].tags) == {"smoke", "regression"}

    @pytest.mark.asyncio
    async def test_exists_by_test_id(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test checking if test definition exists by test_id."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="Exists Test",
            test_id="exists-001"
        )
        await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Check exists
        exists = await repository.exists_by_test_id("exists-001", test_db_session)
        not_exists = await repository.exists_by_test_id("not-exists-001", test_db_session)

        assert exists is True
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_get_regression_tests(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving regression test definitions."""
        # Create regular and regression tests
        test1 = TestDefinitionCreate(name="Regular Test", test_id="reg-001")
        test2 = TestDefinitionCreate(name="Regression Test", test_id="reg-002")

        created1 = await repository.create(test1, test_db_session)
        created2 = await repository.create(test2, test_db_session)

        # Mark one as regression
        await repository.update(created2.id, {"is_regression": True}, test_db_session)
        await test_db_session.commit()

        # Get regression tests
        regression_tests = await repository.get_regression_tests(test_db_session)

        # Should include our regression test
        assert any(td.id == created2.id for td in regression_tests)

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test retrieving test definition by name."""
        # Create test definition
        test_data = TestDefinitionCreate(
            name="Unique Name Test",
            test_id="name-001"
        )
        created = await repository.create(test_data, test_db_session)
        await test_db_session.commit()

        # Get by name
        retrieved = await repository.get_by_name("Unique Name Test", test_db_session)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Unique Name Test"

    @pytest.mark.asyncio
    async def test_draft_filtering(self, repository: SQLAlchemyTestDefinitionRepository, test_db_session: AsyncSession):
        """Test filtering draft test definitions."""
        # Create draft and non-draft definitions
        test1 = TestDefinitionCreate(name="Published Test", test_id="draft-001")
        test2 = TestDefinitionCreate(name="Draft Test", test_id="draft-002")

        created1 = await repository.create(test1, test_db_session)
        created2 = await repository.create(test2, test_db_session)

        # Mark one as draft
        await repository.update(created2.id, {"is_draft": True}, test_db_session)
        await test_db_session.commit()

        # Get all without drafts
        non_drafts = await repository.get_all(test_db_session, include_drafts=False)

        # Should not include draft
        assert not any(td.is_draft for td in non_drafts)

        # Get all including drafts
        all_tests = await repository.get_all(test_db_session, include_drafts=True)

        # Should include both
        assert len(all_tests) >= len(non_drafts)
