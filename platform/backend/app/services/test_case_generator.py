"""
Test Case Generator Service (Refactored)

Orchestrates test case generation using dependency injection.
Coordinates LLM client, prompt builder, response parser, and repository.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    GeneratedTestCase,
    PromptTemplate
)
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser
from app.repositories.test_case_repository import TestCaseRepository

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """
    Orchestrator for test case generation using LLM.

    Coordinates between LLM client, prompt builder, response parser,
    and repository to generate complete test cases from requirements.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        repository: Optional[TestCaseRepository] = None
    ):
        """
        Initialize test case generator with injected dependencies.

        Args:
            llm_client: LLM API client (creates default if None)
            prompt_builder: Prompt builder (creates default if None)
            response_parser: Response parser (creates default if None)
            repository: Test case repository (requires db session)
        """
        self.llm_client = llm_client or LLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()
        self.repository = repository

    async def generate_test_case(
        self,
        request: TestCaseGenerateRequest,
        db: Optional[AsyncSession] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete test case from requirements.

        Orchestrates the full generation workflow:
        1. Build prompt from request
        2. Call LLM API
        3. Parse response
        4. Save to database (if db session provided)

        Args:
            request: Test generation request
            db: Optional database session for persistence
            created_by: Optional user ID who requested generation

        Returns:
            dict: Generated test case with metadata

        Raises:
            ValueError: If request is invalid
            Exception: If generation fails
        """
        logger.info(
            f"Generating test case for {request.test_type} test: "
            f"{request.app_url}"
        )

        try:
            # Step 1: Build prompt
            prompt = self.prompt_builder.build_test_generation_prompt(request)
            logger.debug(f"Generated prompt ({len(prompt)} chars)")

            # Step 2: Call LLM API
            ai_response = await self.llm_client.generate_test_case(prompt)
            logger.info(f"Received LLM response ({len(ai_response)} chars)")

            # Step 3: Parse response
            generated_case = self.response_parser.parse_test_case_response(
                ai_response,
                request
            )
            logger.info(
                f"Parsed test case '{generated_case.name}' "
                f"with {len(generated_case.steps)} steps"
            )

            # Step 4: Save to database (if session provided)
            test_def_id = None
            if db and self.repository:
                # Create repository with session if not already set
                if not self.repository:
                    self.repository = TestCaseRepository(db)

                test_def_id = await self.repository.create_test_case(
                    generated_case,
                    environment=request.credentials,
                    created_by=created_by
                )
                logger.info(f"Saved test definition {test_def_id} to database")

            # Return result with metadata
            return {
                "test_definition_id": test_def_id,
                "test_case": generated_case.model_dump(),
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "ai_model": self.llm_client.model,
                    "test_type": request.test_type,
                    "total_steps": len(generated_case.steps),
                    "estimated_duration": generated_case.estimated_duration
                }
            }

        except Exception as e:
            logger.error(f"Test case generation failed: {str(e)}")
            raise

    async def generate_batch(
        self,
        requests: List[TestCaseGenerateRequest],
        db: Optional[AsyncSession] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate multiple test cases in batch.

        Args:
            requests: List of test generation requests
            db: Optional database session for persistence
            created_by: Optional user ID who requested generation

        Returns:
            dict: Batch generation results with summary
        """
        logger.info(f"Starting batch generation of {len(requests)} test cases")

        generated = []
        failed = []

        for idx, req in enumerate(requests):
            try:
                result = await self.generate_test_case(req, db, created_by)
                generated.append(result)
                logger.info(f"Generated test case {idx + 1}/{len(requests)}")

            except Exception as e:
                logger.error(f"Failed to generate test case {idx + 1}: {str(e)}")
                failed.append({
                    "index": idx,
                    "requirements": req.requirements,
                    "error": str(e)
                })

        summary = {
            "total": len(requests),
            "succeeded": len(generated),
            "failed": len(failed)
        }

        logger.info(
            f"Batch generation complete: {summary['succeeded']} succeeded, "
            f"{summary['failed']} failed"
        )

        return {
            "generated_tests": generated,
            "summary": summary,
            "failed": failed
        }

    def get_prompt_template(self, test_type: str) -> PromptTemplate:
        """
        Get prompt template for specific test type.

        Args:
            test_type: Type of test

        Returns:
            PromptTemplate: Template for the test type
        """
        return self.prompt_builder.get_prompt_template(test_type)

    async def health_check(self) -> Dict[str, bool]:
        """
        Health check for all components.

        Returns:
            dict: Health status of each component
        """
        health = {
            "llm_client": await self.llm_client.health_check(),
            "prompt_builder": True,  # Always healthy (no external deps)
            "response_parser": True,  # Always healthy (no external deps)
        }

        if self.repository:
            try:
                # Try to count test cases
                count = await self.repository.count_test_cases()
                health["repository"] = count >= 0
            except Exception:
                health["repository"] = False
        else:
            health["repository"] = None  # Not configured

        return health

    def set_repository(self, db: AsyncSession) -> None:
        """
        Set repository with database session.

        Args:
            db: Database session
        """
        self.repository = TestCaseRepository(db)

    async def validate_request(self, request: TestCaseGenerateRequest) -> bool:
        """
        Validate test generation request.

        Args:
            request: Test generation request

        Returns:
            bool: True if request is valid
        """
        try:
            # Pydantic validation is automatic
            # Additional business logic validation can be added here

            if not request.app_url:
                logger.error("App URL is required")
                return False

            if len(request.requirements) < 20:
                logger.error("Requirements must be at least 20 characters")
                return False

            if request.max_steps < 5 or request.max_steps > 20:
                logger.error("Max steps must be between 5 and 20")
                return False

            return True

        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            return False

    async def estimate_generation_time(
        self,
        num_requests: int = 1
    ) -> Dict[str, Any]:
        """
        Estimate generation time for test cases.

        Args:
            num_requests: Number of test cases to generate

        Returns:
            dict: Time estimation details
        """
        # Assume 30 seconds per test case generation
        avg_time_per_test = 30  # seconds

        estimated_total_seconds = num_requests * avg_time_per_test
        estimated_minutes = estimated_total_seconds / 60

        return {
            "num_requests": num_requests,
            "estimated_seconds": estimated_total_seconds,
            "estimated_minutes": estimated_minutes,
            "estimated_time_per_test": avg_time_per_test
        }
