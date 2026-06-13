"""
Test Case Repository

Handles database operations for test cases and test definitions.
Abstracts database access using SQLAlchemy patterns.
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_definition import TestDefinition
from app.schemas.test_generation import GeneratedTestCase

logger = logging.getLogger(__name__)


class TestCaseRepository:
    """
    Repository for test case database operations.

    Handles CRUD operations for test definitions and associated test steps.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def create_test_case(
        self,
        test_case: GeneratedTestCase,
        environment: Optional[Dict[str, str]] = None,
        created_by: Optional[int] = None
    ) -> int:
        """
        Create a new test definition with steps.

        Args:
            test_case: Generated test case data
            environment: Optional environment configuration
            created_by: Optional user ID who created the test

        Returns:
            int: Created test definition ID

        Raises:
            Exception: If database operation fails
        """
        try:
            # Create test definition
            test_def = TestDefinition(
                name=test_case.name,
                description=test_case.description,
                test_id=test_case.test_id,
                url=test_case.url,
                tags=test_case.tags,
                environment=environment or {},
                is_active=True,
                created_by=created_by,
                version=1,
                execution_mode="script",
                script_status="none",
                review_status="draft"
            )

            self.db.add(test_def)
            await self.db.flush()
            await self.db.refresh(test_def)

            logger.info(f"Created test definition {test_def.id}: {test_def.name}")

            # Create test steps (assuming a TestStep model exists)
            await self._create_test_steps(test_def.id, test_case.steps)

            return test_def.id

        except Exception as e:
            logger.error(f"Error creating test case: {str(e)}")
            await self.db.rollback()
            raise

    async def _create_test_steps(
        self,
        test_definition_id: int,
        steps: List
    ) -> None:
        """
        Create test steps for a test definition.

        Args:
            test_definition_id: Test definition ID
            steps: List of test steps
        """
        # Import here to avoid circular dependencies
        try:
            from app.models.test_step import TestStep

            step_records = [
                TestStep(
                    test_definition_id=test_definition_id,
                    step_number=step.step_number,
                    description=step.description,
                    type=step.type,
                    params=step.params,
                    expected_result=step.expected_result
                )
                for step in steps
            ]

            self.db.add_all(step_records)
            await self.db.flush()

            logger.info(
                f"Created {len(step_records)} test steps "
                f"for test definition {test_definition_id}"
            )

        except ImportError:
            # If TestStep model doesn't exist, store steps in test_context
            test_def = await self.get_by_id(test_definition_id)
            if test_def:
                test_def.test_context = {
                    "steps": [
                        {
                            "step_number": step.step_number,
                            "description": step.description,
                            "type": step.type,
                            "params": step.params,
                            "expected_result": step.expected_result
                        }
                        for step in steps
                    ]
                }
                await self.db.flush()
                logger.info(
                    f"Stored {len(steps)} steps in test_context "
                    f"for test definition {test_definition_id}"
                )

    async def bulk_create_test_cases(
        self,
        test_cases: List[GeneratedTestCase],
        environment: Optional[Dict[str, str]] = None,
        created_by: Optional[int] = None
    ) -> List[int]:
        """
        Create multiple test cases in bulk.

        Args:
            test_cases: List of generated test cases
            environment: Optional environment configuration
            created_by: Optional user ID who created the tests

        Returns:
            list: List of created test definition IDs

        Raises:
            Exception: If any database operation fails
        """
        created_ids = []

        try:
            for test_case in test_cases:
                test_id = await self.create_test_case(
                    test_case,
                    environment=environment,
                    created_by=created_by
                )
                created_ids.append(test_id)

            await self.db.commit()

            logger.info(
                f"Bulk created {len(created_ids)} test cases"
            )

            return created_ids

        except Exception as e:
            logger.error(f"Error in bulk creation: {str(e)}")
            await self.db.rollback()
            raise

    async def get_by_id(self, test_definition_id: int) -> Optional[TestDefinition]:
        """
        Get test definition by ID.

        Args:
            test_definition_id: Test definition ID

        Returns:
            TestDefinition if found, None otherwise
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.id == test_definition_id
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Error fetching test definition {test_definition_id}: {str(e)}"
            )
            return None

    async def get_by_test_id(self, test_id: str) -> Optional[TestDefinition]:
        """
        Get test definition by test ID.

        Args:
            test_id: Test identifier string

        Returns:
            TestDefinition if found, None otherwise
        """
        try:
            stmt = select(TestDefinition).where(
                TestDefinition.test_id == test_id
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error fetching test by test_id {test_id}: {str(e)}")
            return None

    async def update_test_case(
        self,
        test_definition_id: int,
        updates: Dict[str, Any]
    ) -> Optional[TestDefinition]:
        """
        Update test definition.

        Args:
            test_definition_id: Test definition ID
            updates: Dictionary of fields to update

        Returns:
            Updated TestDefinition if found, None otherwise
        """
        try:
            test_def = await self.get_by_id(test_definition_id)
            if not test_def:
                return None

            for key, value in updates.items():
                if hasattr(test_def, key):
                    setattr(test_def, key, value)

            await self.db.flush()
            await self.db.refresh(test_def)

            logger.info(f"Updated test definition {test_definition_id}")
            return test_def

        except Exception as e:
            logger.error(
                f"Error updating test definition {test_definition_id}: {str(e)}"
            )
            await self.db.rollback()
            return None

    async def delete_test_case(self, test_definition_id: int) -> bool:
        """
        Delete test definition.

        Args:
            test_definition_id: Test definition ID

        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            test_def = await self.get_by_id(test_definition_id)
            if not test_def:
                return False

            await self.db.delete(test_def)
            await self.db.flush()

            logger.info(f"Deleted test definition {test_definition_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error deleting test definition {test_definition_id}: {str(e)}"
            )
            await self.db.rollback()
            return False

    async def list_test_cases(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> List[TestDefinition]:
        """
        List test definitions with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            is_active: Filter by active status

        Returns:
            list: List of test definitions
        """
        try:
            stmt = select(TestDefinition)

            if is_active is not None:
                stmt = stmt.where(TestDefinition.is_active == is_active)

            stmt = stmt.order_by(TestDefinition.created_at.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error listing test cases: {str(e)}")
            return []

    async def count_test_cases(self, is_active: Optional[bool] = None) -> int:
        """
        Count test definitions.

        Args:
            is_active: Filter by active status

        Returns:
            int: Number of test definitions
        """
        try:
            from sqlalchemy import func

            stmt = select(func.count(TestDefinition.id))

            if is_active is not None:
                stmt = stmt.where(TestDefinition.is_active == is_active)

            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting test cases: {str(e)}")
            return 0
