"""
Test Definition Repository Interface

Abstract interface for TestDefinition repository operations following SOLID principles.
This enables Dependency Inversion - services depend on abstractions, not concretions.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ITestDefinitionRepository(ABC):
    """
    Abstract interface for TestDefinition repository operations.

    This interface defines the contract for TestDefinition data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        test_definition: Any,
        db_session: Any
    ) -> Any:
        """
        Create a new test definition record.

        Args:
            test_definition: TestDefinitionCreate schema with test data
            db_session: Database session

        Returns:
            Created TestDefinition object

        Raises:
            ValueError: If validation fails or test_id already exists
        """
        pass

    @abstractmethod
    async def get_by_id(self, definition_id: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a test definition by its primary key ID.

        Args:
            definition_id: Primary key ID
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_test_id(self, test_id: str, db_session: Any) -> Optional[Any]:
        """
        Retrieve a test definition by its test_id.

        Args:
            test_id: Unique test identifier
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_name(self, name: str, db_session: Any) -> Optional[Any]:
        """
        Retrieve a test definition by its name.

        Args:
            name: Test definition name
            db_session: Database session

        Returns:
            TestDefinition object or None if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0,
        include_drafts: bool = False
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def update(
        self,
        definition_id: int,
        updates: Dict[str, Any],
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def delete(self, definition_id: int, db_session: Any) -> bool:
        """
        Delete a test definition by its ID.

        Args:
            definition_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_by_suite_id(
        self,
        suite_id: int,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_by_tag(
        self,
        tag: str,
        db_session: Any,
        limit: int = 50,
        include_drafts: bool = False
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_by_tags(
        self,
        tags: List[str],
        db_session: Any,
        match_mode: str = "any",
        limit: int = 50,
        include_drafts: bool = False
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        db_session: Any,
        limit: int = 50,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def count(self, db_session: Any, include_drafts: bool = False) -> int:
        """
        Count total test definitions.

        Args:
            db_session: Database session
            include_drafts: Whether to include draft test definitions

        Returns:
            Total count of test definitions
        """
        pass

    @abstractmethod
    async def get_active_definitions(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve all active test definitions.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of active TestDefinition objects
        """
        pass

    @abstractmethod
    async def get_by_workspace_id(
        self,
        workspace_id: int,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_by_review_status(
        self,
        review_status: str,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
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
        pass

    @abstractmethod
    async def get_regression_tests(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve all regression test definitions.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of regression TestDefinition objects
        """
        pass

    @abstractmethod
    async def exists_by_test_id(self, test_id: str, db_session: Any) -> bool:
        """
        Check if a test definition exists by test_id.

        Args:
            test_id: Unique test identifier
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def update_script(
        self,
        definition_id: int,
        playwright_script: str,
        script_status: str,
        script_metadata: Optional[Dict[str, Any]] = None,
        db_session: Any = None
    ) -> Any:
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
        pass

    @abstractmethod
    async def update_review_status(
        self,
        definition_id: int,
        review_status: str,
        reviewed_by: Optional[int] = None,
        rejection_reason: Optional[str] = None,
        db_session: Any = None
    ) -> Any:
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
        pass
