"""
Test Case Generator Service

Uses LLM (GLM) to generate comprehensive test cases from natural language requirements.
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    GeneratedTestCase,
    GeneratedTestStep,
    PromptTemplate
)

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """
    Service for generating test cases using LLM.

    Converts natural language requirements into structured test cases
    with detailed steps that can be executed by Playwright.
    """

    def __init__(self):
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.llm_model = os.getenv("LLM_MODEL", "glm-4-plus")
        self.timeout = 300.0

    async def generate_test_case(
        self,
        request: TestCaseGenerateRequest
    ) -> Dict[str, Any]:
        """
        Generate a complete test case from requirements.

        Args:
            request: Test generation request

        Returns:
            dict: Generated test case with metadata
        """
        # Build prompt for Claude
        prompt = self._build_prompt(request)

        # Call LLM API
        ai_response = await self._call_llm(prompt)

        # Parse response
        generated_case = self._parse_ai_response(ai_response, request)

        # Save to database
        test_def_id = await self._save_to_database(generated_case, request, None)

        return {
            "test_definition_id": test_def_id,
            "test_case": generated_case,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "ai_model": self.llm_model,
                "test_type": request.test_type,
                "total_steps": len(generated_case.steps)
            }
        }

    def _build_prompt(self, request: TestCaseGenerateRequest) -> str:
        """Build comprehensive prompt for Claude AI."""

        prompt = f"""You are an expert QA test case generator. Generate a comprehensive test case based on the following requirements.

Application Details:
- URL: {request.app_url}
- Description: {request.app_description}
- Test Type: {request.test_type}

Test Requirements:
{request.requirements}

"""

        # Add credentials if provided
        if request.credentials:
            prompt += f"\nTest Credentials:\n{json.dumps(request.credentials, indent=2)}\n"

        # Add test data if provided
        if request.test_data:
            prompt += f"\nTest Data:\n{json.dumps(request.test_data, indent=2)}\n"

        prompt += f"""
Generate a test case with {request.max_steps} detailed steps.

Each step must include:
1. A clear natural language description (this will be used for AI interpretation during execution)
2. Action type: navigate, click, input, verify, wait, select, screenshot, etc.
3. Parameters: CSS selectors, values, URLs, etc.
4. Expected result: What should happen

Action Types:
- navigate: Navigate to a URL (params: url)
- click: Click an element (params: selector)
- input: Enter text in a field (params: selector, value)
- select: Select from dropdown (params: selector, value)
- verify: Verify element exists or text is present (params: selector or text)
- wait: Wait for condition (params: seconds or selector)
- hover: Hover over element (params: selector)
- screenshot: Take screenshot (params: filename)

Return ONLY a valid JSON object in this exact format:
{{
  "name": "Test Case Name",
  "description": "Detailed description of what this test validates",
  "steps": [
    {{
      "step_number": 1,
      "description": "Navigate to the login page",
      "type": "navigate",
      "params": {{"url": "https://example.com/login"}},
      "expected_result": "Login page loads successfully"
    }},
    {{
      "step_number": 2,
      "description": "Enter username in the username field",
      "type": "input",
      "params": {{"selector": "input[name='username']", "value": "test@example.com"}},
      "expected_result": "Username is entered in the field"
    }}
  ]
}}

Important:
- Generate realistic, actionable steps
- Use specific CSS selectors when possible
- Include proper error handling steps
- Make descriptions clear and detailed
- Ensure steps are logically ordered
- Generate between 5 and {request.max_steps} steps
"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM via OpenAI-compatible Chat Completions API."""

        if not self.llm_api_key:
            raise ValueError("LLM_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.llm_model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise

    def _parse_ai_response(self, ai_response: str, request: TestCaseGenerateRequest) -> GeneratedTestCase:
        """Parse Claude AI response into structured test case."""

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', ai_response)
        if not json_match:
            raise ValueError("No JSON found in AI response")

        try:
            case_data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {str(e)}")
            raise ValueError(f"Invalid JSON in AI response: {str(e)}")

        # Validate required fields
        if "name" not in case_data or "steps" not in case_data:
            raise ValueError("AI response missing required fields: name or steps")

        # Convert steps
        steps = []
        for step_data in case_data.get("steps", []):
            step = GeneratedTestStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                description=step_data.get("description", ""),
                type=step_data.get("type", "verify"),
                params=step_data.get("params", {}),
                expected_result=step_data.get("expected_result", "")
            )
            steps.append(step)

        # Generate test ID
        test_id = self._generate_test_id(case_data["name"], request.test_type)

        # Estimate duration
        estimated_duration = self._estimate_duration(len(steps))

        return GeneratedTestCase(
            name=case_data["name"],
            description=case_data.get("description", ""),
            test_id=test_id,
            url=request.app_url,
            tags=request.tags,
            steps=steps,
            estimated_duration=estimated_duration
        )

    def _generate_test_id(self, name: str, test_type: str) -> str:
        """Generate unique test case ID."""
        # Extract key words from name
        words = re.findall(r'\w+', name.upper())
        prefix = "-".join(words[:3]) if len(words) >= 3 else "-".join(words)
        return f"TC-{prefix}-{test_type.upper()}"

    def _estimate_duration(self, num_steps: int) -> str:
        """Estimate test execution duration."""
        # Assume 30 seconds per step on average
        total_seconds = num_steps * 30
        minutes = total_seconds // 60
        if minutes > 0:
            return f"{minutes}-{minutes + 2} minutes"
        return f"{total_seconds} seconds"

    async def _save_to_database(
        self,
        test_case: GeneratedTestCase,
        request: TestCaseGenerateRequest,
        db: Optional[Any]
    ) -> int:
        """Save generated test case to database via API."""

        # Prepare test definition data
        test_def_data = {
            "name": test_case.name,
            "description": test_case.description,
            "test_id": test_case.test_id,
            "url": test_case.url,
            "tags": test_case.tags,
            "environment": request.credentials or {},
            "is_active": True
        }

        # Prepare test steps data
        test_steps_data = [
            {
                "step_number": step.step_number,
                "description": step.description,
                "type": step.type,
                "params": step.params,
                "expected_result": step.expected_result
            }
            for step in test_case.steps
        ]

        try:
            # Call test-case-service API
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create test definition
                response = await client.post(
                    "http://test-case-service:8001/api/v1/test-definitions/",
                    json=test_def_data
                )
                response.raise_for_status()
                result = response.json()
                test_def_id = result.get("id")

                # Create test steps
                for step_data in test_steps_data:
                    step_response = await client.post(
                        f"http://test-case-service:8001/api/v1/test-steps/test-definition/{test_def_id}",
                        json=step_data
                    )
                    step_response.raise_for_status()

            logger.info(f"Created test definition {test_def_id} with {len(test_steps_data)} steps")
            return test_def_id

        except httpx.HTTPError as e:
            logger.error(f"HTTP error saving to database: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            raise

    async def generate_batch(
        self,
        requests: List[TestCaseGenerateRequest]
    ) -> Dict[str, Any]:
        """
        Generate multiple test cases in batch.

        Args:
            requests: List of test generation requests

        Returns:
            dict: Batch generation results
        """
        generated = []
        failed = []

        for idx, req in enumerate(requests):
            try:
                result = await self.generate_test_case(req)
                generated.append(result)
            except Exception as e:
                logger.error(f"Failed to generate test case {idx}: {str(e)}")
                failed.append({
                    "index": idx,
                    "requirements": req.requirements,
                    "error": str(e)
                })

        return {
            "generated_tests": generated,
            "summary": {
                "total": len(requests),
                "succeeded": len(generated),
                "failed": len(failed)
            },
            "failed": failed
        }

    def get_prompt_template(self, test_type: str) -> PromptTemplate:
        """Get prompt template for specific test type."""
        templates = self._get_templates()
        return templates.get(test_type, templates["functional"])

    def _get_templates(self) -> Dict[str, PromptTemplate]:
        """Get all available prompt templates."""
        return {
            "functional": PromptTemplate(
                name="Functional Test",
                test_type="functional",
                description="Template for functional testing",
                template="Generate functional test cases for {requirements}",
                variables=["requirements"]
            ),
            "ui": PromptTemplate(
                name="UI Test",
                test_type="ui",
                description="Template for UI/UX testing",
                template="Generate UI test cases focusing on {requirements}",
                variables=["requirements"]
            ),
            "api": PromptTemplate(
                name="API Test",
                test_type="api",
                description="Template for API testing",
                template="Generate API test cases for {requirements}",
                variables=["requirements"]
            ),
            "e2e": PromptTemplate(
                name="E2E Test",
                test_type="e2e",
                description="Template for end-to-end testing",
                template="Generate E2E test cases covering {requirements}",
                variables=["requirements"]
            )
        }
