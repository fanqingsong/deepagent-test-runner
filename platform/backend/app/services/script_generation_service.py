"""
Script Generation Service

Orchestrates Playwright script generation workflows.
Extracted from endpoints to follow Single Responsibility Principle.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models.test_definition import TestDefinition
from app.schemas.test_definition import ScriptResponse
from app.core.agent_config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_context import llm_usage_context

logger = logging.getLogger(__name__)


class ScriptGenerationService:
    """
    Service for managing Playwright script generation workflows.

    Responsible for:
    - Script generation orchestration
    - Test definition validation and loading
    - Generation workflow coordination
    - Description generation via LLM
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Script Generation Service.

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

    def validate_test_definition_for_generation(
        self,
        test_def: TestDefinition
    ) -> None:
        """
        Validate that test definition has required fields for generation.

        Args:
            test_def: TestDefinition object

        Raises:
            ValueError: If validation fails
        """
        if not test_def.url or not test_def.test_goal:
            raise ValueError(
                "Test definition must have both url and test_goal for script generation"
            )

    def should_use_existing_script(
        self,
        test_def: TestDefinition,
        force_regenerate: bool = False
    ) -> bool:
        """
        Determine if existing validated script should be used.

        Args:
            test_def: TestDefinition object
            force_regenerate: Force regeneration even if script exists

        Returns:
            True if existing script should be used
        """
        return (
            not force_regenerate
            and test_def.playwright_script
            and test_def.script_status == "validated"
        )

    def build_script_response(
        self,
        test_def: TestDefinition
    ) -> ScriptResponse:
        """
        Build ScriptResponse from TestDefinition.

        Args:
            test_def: TestDefinition object

        Returns:
            ScriptResponse object
        """
        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    async def generate_description(
        self,
        test_goal: str,
        test_definition_id: int
    ) -> str:
        """
        Generate a concise description based on test goal using LLM.

        Args:
            test_goal: Natural language test goal
            test_definition_id: Test definition ID for tracking

        Returns:
            Generated description text

        Raises:
            ValueError: If test_goal is empty
            RuntimeError: If LLM generation fails
        """
        if not test_goal or not test_goal.strip():
            raise ValueError("Test goal cannot be empty")

        system_prompt = """You are a technical writing assistant. Generate a concise, clear description for a test case based on its goal.

Rules:
1. Output ONLY the description text, no explanations or markdown
2. Keep it under 100 characters
3. Use active voice and present tense
4. Focus on what is being tested, not how
5. Be specific but brief
6. Do NOT add any introductory or concluding text"""

        user_prompt = f"""Generate a concise description for this test goal:

Test Goal: {test_goal}

Generate the description now."""

        try:
            llm = get_llm(temperature=0.3, max_tokens=150)
            async with llm_usage_context(
                "description_generator",
                test_run_id=f"test_def_{test_definition_id}"
            ):
                response = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
        except Exception as e:
            logger.error(f"Error generating description: {str(e)}")
            raise RuntimeError(f"Failed to generate description: {str(e)}") from e

        content = response.content if hasattr(response, 'content') else str(response)
        generated_description = content.strip()

        # Clean up common LLM artifacts
        generated_description = generated_description.rstrip('."')

        return generated_description

    async def prepare_script_generation(
        self,
        test_definition_id: int,
        force_regenerate: bool = False
    ) -> tuple[TestDefinition, Optional[ScriptResponse]]:
        """
        Prepare test definition for script generation.

        Args:
            test_definition_id: Test definition ID
            force_regenerate: Force regeneration even if script exists

        Returns:
            Tuple of (TestDefinition, Optional[ScriptResponse])
            If ScriptResponse is returned, existing script should be used

        Raises:
            ValueError: If test definition not found or invalid
        """
        test_def = await self.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise ValueError("Test definition not found")

        # Validate test definition has required fields
        self.validate_test_definition_for_generation(test_def)

        # Check if existing validated script should be used
        if self.should_use_existing_script(test_def, force_regenerate):
            return test_def, self.build_script_response(test_def)

        # Mark as generating
        test_def.script_status = "generating"
        await self.db.commit()

        return test_def, None

    async def run_script_generation_workflow(
        self,
        test_definition_id: int,
        url: str,
        goal: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete script generation workflow.

        Args:
            test_definition_id: Test definition ID
            url: Target URL for testing
            goal: Test goal description
            description: Optional additional description

        Returns:
            Dict with generation results
        """
        from app.agents.test_composer.runners import run_script_generation

        return await run_script_generation(
            test_definition_id=test_definition_id,
            url=url,
            goal=goal,
            description=description,
            db=self.db,
        )
