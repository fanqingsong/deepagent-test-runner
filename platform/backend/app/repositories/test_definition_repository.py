"""
Test Definition Repository Implementation

SQLAlchemy implementation of TestDefinition repository following async patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository

logger = logging.getLogger(__name__)


class SQLAlchemyTestDefinitionRepository(ITestDefinitionRepository):
    """
    SQLAlchemy implementation of TestDefinition repository.

    Handles all database operations for TestDefinition model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = TestDefinition

    async def create(
        self,
        test_definition: Any,
        db_session: AsyncSession
    ) -> TestDefinition:
        """
        Create a new test definition record.

        Args:
            test_definition: TestDefinitionCreate schema with test data
            db_session: Database session

        Returns:
            Created TestDefinition object

        Raises:
            ValueError: If test_id already exists or validation fails
        """
        # Check if test_id already exists
        existing = await self.get_by_test_id(test_definition.test_id, db_session)
        if existing:
            raise ValueError(f"Test definition with test_id '{test_definition.test_id}' already exists")

        # Create new test definition
        new_definition = TestDefinition(
            name=test_definition.name,
            description=test_definition.description,
            test_id=test_definition.test_id,
            url=test_definition.url,
            environment=test_definition.environment,
            tags=test_definition.tags,
            test_goal=test_definition.test_goal,
            test_context=test_definition.test_context,
            execution_mode=test_definition.execution_mode,
            is_active=True,
            version=1,
            is_draft=False,
            script_status="none",
            script_metadata={},
            review_status="draft"
        )

        try:
            db_session.add(new_definition)
            await db_session.flush()
            await db_session.refresh(new_definition)

            logger.info(f"Created test definition {new_definition.test_id} with ID {new_definition.id}")
            return new_definition

        except Exception as e:
            logger.error(f"Error creating test definition {test_definition.test_id}: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(self, definition_id: int, db_session: AsyncSession) -> Optional[TestDefinition]:
        """
        Retrieve a test definition by its primary key ID.

        Args:
            definition_id: Primary key ID
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        try:
            stmt = select(TestDefinition).where(TestDefinition.id == definition_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving test definition by id {definition_id}: {e}")
            raise

    async def get_by_test_id(self, test_id: str, db_session: AsyncSession) -> Optional[TestDefinition]:
        """
        Retrieve a test definition by its test_id.

        Args:
            test_id: Unique test identifier
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        try:
            stmt = select(TestDefinition).where(TestDefinition.test_id == test_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving test definition {test_id}: {e}")
            raise

    async def get_by_name(self, name: str, db_session: AsyncSession) -> Optional[TestDefinition]:
        """
        Retrieve a test definition by its name.

        Args:
            name: Test definition name
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        try:
            stmt = select(TestDefinition).where(TestDefinition.name == name)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error retrieving test definition by name {name}: {e}")
            raise

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        include_drafts: bool = False
    ) -> List[TestDefinition]:
        """
        Retrieve all test definitions with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            include_drafts: Whether to include draft test definitions

        Returns:
            List of TestDefinition objects, ordered by created_at DESC
        """
        try:
            stmt = select(TestDefinition)

            if not include_drafts:
                stmt = stmt.where(TestDefinition.is_draft == False)

            stmt = stmt.order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving all test definitions: {e}")
            raise

    async def update(
        self,
        definition_id: int,
        updates: Dict[str, Any],
        db_session: AsyncSession
    ) -> TestDefinition:
        """
        Update a test definition.

        Args:
            definition_id: Primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated TestDefinition object

        Raises:
            ValueError: If test definition not found
        """
        test_definition = await self.get_by_id(definition_id, db_session)
        if not test_definition:
            raise ValueError(f"Test definition {definition_id} not found")

        # Update allowed fields
        allowed_fields = {
            'name', 'description', 'url', 'environment', 'tags',
            'test_goal', 'test_context', 'execution_mode', 'is_active',
            'playwright_script', 'script_status', 'script_metadata',
            'review_status', 'reviewed_by', 'reviewed_at', 'rejection_reason'
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(test_definition, field):
                setattr(test_definition, field, value)

        # Update timestamp
        test_definition.updated_at = datetime.utcnow()

        try:
            await db_session.flush()
            await db_session.refresh(test_definition)

            logger.info(f"Updated test definition {definition_id}")
            return test_definition

        except Exception as e:
            logger.error(f"Error updating test definition {definition_id}: {e}")
            await db_session.rollback()
            raise

    async def delete(self, definition_id: int, db_session: AsyncSession) -> bool:
        """
        Delete a test definition by its ID.

        Args:
            definition_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        try:
            test_definition = await self.get_by_id(definition_id, db_session)
            if not test_definition:
                return False

            db_session.delete(test_definition)
            await db_session.flush()

            logger.info(f"Deleted test definition {definition_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting test definition {definition_id}: {e}")
            await db_session.rollback()
            raise

    async def get_by_suite_id(
        self,
        suite_id: int,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Retrieve test definitions belonging to a specific test suite.

        Args:
            suite_id: Test suite ID
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestDefinition objects
        """
        try:
            # Get test suite to find test_definition_ids
            suite_stmt = select(TestSuite).where(TestSuite.id == suite_id)
            suite_result = await db_session.execute(suite_stmt)
            suite = suite_result.scalar_one_or_none()

            if not suite:
                logger.warning(f"Test suite {suite_id} not found")
                return []

            # Get test definitions from suite entries or fallback to test_definition_ids
            if suite.suite_entries:
                test_definition_ids = [
                    entry.get("test_definition_id")
                    for entry in suite.suite_entries
                    if entry.get("test_definition_id") and entry.get("enabled", True)
                ]
            else:
                test_definition_ids = suite.test_definition_ids

            if not test_definition_ids:
                return []

            # Query test definitions
            stmt = select(TestDefinition).where(
                TestDefinition.id.in_(test_definition_ids)
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving test definitions for suite {suite_id}: {e}")
            raise

    async def get_by_tag(
        self,
        tag: str,
        db_session: AsyncSession,
        limit: int = 50,
        include_drafts: bool = False
    ) -> List[TestDefinition]:
        """
        Retrieve test definitions by tag.

        Args:
            tag: Tag to filter by
            db_session: Database session
            limit: Maximum number of records to return
            include_drafts: Whether to include draft test definitions

        Returns:
            List of TestDefinition objects with the specified tag
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.tags.any(tag)
            )

            if not include_drafts:
                stmt = stmt.where(TestDefinition.is_draft == False)

            stmt = stmt.order_by(desc(TestDefinition.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving test definitions by tag {tag}: {e}")
            raise

    async def get_by_tags(
        self,
        tags: List[str],
        db_session: AsyncSession,
        match_mode: str = "any",
        limit: int = 50,
        include_drafts: bool = False
    ) -> List[TestDefinition]:
        """
        Retrieve test definitions by multiple tags.

        Args:
            tags: List of tags to filter by
            db_session: Database session
            match_mode: Match mode - 'any' (default) or 'all'
            limit: Maximum number of records to return
            include_drafts: Whether to include draft test definitions

        Returns:
            List of TestDefinition objects matching the tag criteria
        """
        try:
            if not tags:
                return []

            if match_mode == "all":
                # All tags must be present
                conditions = [TestDefinition.tags.any(tag) for tag in tags]
                stmt = select(TestDefinition).where(*conditions)
            else:
                # Any tag match (default)
                stmt = select(TestDefinition).where(TestDefinition.tags.any(tags))

            if not include_drafts:
                stmt = stmt.where(TestDefinition.is_draft == False)

            stmt = stmt.order_by(desc(TestDefinition.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving test definitions by tags {tags}: {e}")
            raise

    async def search(
        self,
        query: str,
        db_session: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Search test definitions by name or description.

        Args:
            query: Search query string
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestDefinition objects matching the search query
        """
        try:
            search_pattern = f"%{query}%"

            stmt = select(TestDefinition).where(
                or_(
                    TestDefinition.name.ilike(search_pattern),
                    TestDefinition.description.ilike(search_pattern),
                    TestDefinition.test_id.ilike(search_pattern)
                )
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching test definitions with query '{query}': {e}")
            raise

    async def count(self, db_session: AsyncSession, include_drafts: bool = False) -> int:
        """
        Count total test definitions.

        Args:
            db_session: Database session
            include_drafts: Whether to include draft test definitions

        Returns:
            Total count of test definitions
        """
        try:
            stmt = select(func.count()).select_from(TestDefinition)

            if not include_drafts:
                stmt = stmt.where(TestDefinition.is_draft == False)

            result = await db_session.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting test definitions: {e}")
            raise

    async def get_active_definitions(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Retrieve all active test definitions.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of active TestDefinition objects
        """
        try:
            stmt = select(TestDefinition).where(
                and_(
                    TestDefinition.is_active == True,
                    TestDefinition.is_draft == False
                )
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving active test definitions: {e}")
            raise

    async def get_by_workspace_id(
        self,
        workspace_id: int,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Retrieve test definitions from a specific workspace.

        Args:
            workspace_id: Test workspace ID
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestDefinition objects from the workspace
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.source_workspace_id == workspace_id
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving test definitions for workspace {workspace_id}: {e}")
            raise

    async def get_by_review_status(
        self,
        review_status: str,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Retrieve test definitions by review status.

        Args:
            review_status: Review status (draft, pending_review, approved, rejected)
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestDefinition objects with the specified review status
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.review_status == review_status
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving test definitions by review status {review_status}: {e}")
            raise

    async def get_regression_tests(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestDefinition]:
        """
        Retrieve all regression test definitions.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of regression TestDefinition objects
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.is_regression == True
            ).order_by(desc(TestDefinition.created_at)).limit(limit).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error retrieving regression test definitions: {e}")
            raise

    async def exists_by_test_id(self, test_id: str, db_session: AsyncSession) -> bool:
        """
        Check if a test definition exists by test_id.

        Args:
            test_id: Unique test identifier
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count()).select_from(TestDefinition).where(
                TestDefinition.test_id == test_id
            )
            result = await db_session.execute(stmt)
            count = result.scalar() or 0
            return count > 0

        except Exception as e:
            logger.error(f"Error checking if test definition {test_id} exists: {e}")
            raise

    async def update_script(
        self,
        definition_id: int,
        playwright_script: str,
        script_status: str,
        script_metadata: Optional[Dict[str, Any]] = None,
        db_session: AsyncSession = None
    ) -> TestDefinition:
        """
        Update the Playwright script for a test definition.

        Args:
            definition_id: Primary key ID
            playwright_script: Generated script content
            script_status: Script status (draft, validated, approved, etc.)
            script_metadata: Optional metadata about script generation
            db_session: Database session

        Returns:
            Updated TestDefinition object

        Raises:
            ValueError: If test definition not found
        """
        test_definition = await self.get_by_id(definition_id, db_session)
        if not test_definition:
            raise ValueError(f"Test definition {definition_id} not found")

        # Update script fields
        test_definition.playwright_script = playwright_script
        test_definition.script_status = script_status

        if script_metadata is not None:
            test_definition.script_metadata = script_metadata

        test_definition.updated_at = datetime.utcnow()

        try:
            await db_session.flush()
            await db_session.refresh(test_definition)

            logger.info(f"Updated script for test definition {definition_id} with status {script_status}")
            return test_definition

        except Exception as e:
            logger.error(f"Error updating script for test definition {definition_id}: {e}")
            await db_session.rollback()
            raise

    async def update_review_status(
        self,
        definition_id: int,
        review_status: str,
        reviewed_by: Optional[int] = None,
        rejection_reason: Optional[str] = None,
        db_session: AsyncSession = None
    ) -> TestDefinition:
        """
        Update the review status of a test definition.

        Args:
            definition_id: Primary key ID
            review_status: New review status
            reviewed_by: Optional ID of reviewer
            rejection_reason: Optional reason for rejection
            db_session: Database session

        Returns:
            Updated TestDefinition object

        Raises:
            ValueError: If test definition not found
        """
        test_definition = await self.get_by_id(definition_id, db_session)
        if not test_definition:
            raise ValueError(f"Test definition {definition_id} not found")

        # Update review fields
        test_definition.review_status = review_status
        test_definition.reviewed_by = reviewed_by
        test_definition.reviewed_at = datetime.utcnow()

        if rejection_reason is not None:
            test_definition.rejection_reason = rejection_reason

        test_definition.updated_at = datetime.utcnow()

        try:
            await db_session.flush()
            await db_session.refresh(test_definition)

            logger.info(f"Updated review status for test definition {definition_id} to {review_status}")
            return test_definition

        except Exception as e:
            logger.error(f"Error updating review status for test definition {definition_id}: {e}")
            await db_session.rollback()
            raise
