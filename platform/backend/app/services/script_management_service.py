"""
Script Management Service

Handles script lifecycle management operations.
Extracted from endpoints to follow Single Responsibility Principle.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.test_definition import TestDefinition
from app.schemas.test_definition import ScriptResponse, ScriptUpdateRequest

logger = logging.getLogger(__name__)


class ScriptManagementService:
    """
    Service for managing script lifecycle and metadata.

    Responsible for:
    - Script CRUD operations
    - Status transitions (draft → validated → approved)
    - Metadata updates
    - Script approval workflow
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Script Management Service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_test_definition_or_404(
        self,
        test_definition_id: int
    ) -> Optional[TestDefinition]:
        """
        Load a test definition or return None.

        Args:
            test_definition_id: Test definition ID

        Returns:
            TestDefinition object or None
        """
        result = await self.db.execute(
            select(TestDefinition).where(
                TestDefinition.id == test_definition_id,
                TestDefinition.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_script(
        self,
        test_definition_id: int
    ) -> ScriptResponse:
        """
        Get the current script and its status.

        Args:
            test_definition_id: Test definition ID

        Returns:
            ScriptResponse with current script state

        Raises:
            ValueError: If test definition not found
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    async def update_script(
        self,
        test_definition_id: int,
        update_data: ScriptUpdateRequest
    ) -> ScriptResponse:
        """
        Update script content (user edits).

        Args:
            test_definition_id: Test definition ID
            update_data: Script update data

        Returns:
            Updated ScriptResponse

        Raises:
            ValueError: If test definition not found
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        test_def.playwright_script = update_data.playwright_script
        test_def.script_status = "draft"
        await self.db.commit()
        await self.db.refresh(test_def)

        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    async def approve_script(
        self,
        test_definition_id: int
    ) -> ScriptResponse:
        """
        Approve script for regression testing.

        Args:
            test_definition_id: Test definition ID

        Returns:
            Updated ScriptResponse

        Raises:
            ValueError: If test definition not found or script not ready
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        if not test_def.playwright_script:
            raise ValueError("No script to approve")

        if test_def.script_status != "validated":
            raise ValueError(
                "Script must be validated before approval. "
                f"Current status: {test_def.script_status}"
            )

        test_def.script_status = "approved"
        test_def.execution_mode = "script"
        await self.db.commit()
        await self.db.refresh(test_def)

        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    async def update_script_status(
        self,
        test_definition_id: int,
        new_status: str,
        metadata_updates: Optional[dict] = None
    ) -> ScriptResponse:
        """
        Update script status and optionally merge metadata.

        Args:
            test_definition_id: Test definition ID
            new_status: New script status
            metadata_updates: Optional metadata to merge

        Returns:
            Updated ScriptResponse

        Raises:
            ValueError: If test definition not found
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        test_def.script_status = new_status

        if metadata_updates:
            if test_def.script_metadata is None:
                test_def.script_metadata = {}
            test_def.script_metadata.update(metadata_updates)

        await self.db.commit()
        await self.db.refresh(test_def)

        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    async def save_generated_script(
        self,
        test_definition_id: int,
        script: str,
        script_status: str,
        script_metadata: Optional[dict] = None
    ) -> ScriptResponse:
        """
        Save a generated script to database.

        Args:
            test_definition_id: Test definition ID
            script: Generated Playwright script
            script_status: Status of the script
            script_metadata: Optional metadata

        Returns:
            Updated ScriptResponse

        Raises:
            ValueError: If test definition not found
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        test_def.playwright_script = script
        test_def.script_status = script_status
        test_def.script_metadata = script_metadata or {}
        test_def.execution_mode = "script"

        await self.db.commit()
        await self.db.refresh(test_def)

        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )
