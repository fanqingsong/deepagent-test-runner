"""
Prompt Builder Service

Constructs comprehensive prompts for LLM test case generation.
Handles different test types and scenarios.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    PromptTemplate
)

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds prompts for LLM test case generation.

    Constructs detailed prompts based on test requirements,
    application context, and test type specifications.
    """

    def __init__(self):
        """Initialize prompt builder with default templates."""
        self.templates = self._get_default_templates()

    def build_test_generation_prompt(
        self,
        request: TestCaseGenerateRequest
    ) -> str:
        """
        Build comprehensive prompt for test case generation.

        Args:
            request: Test generation request with all context

        Returns:
            str: Formatted prompt for LLM
        """
        # Base prompt
        prompt = self._build_base_prompt(request)

        # Add application context
        prompt += self._build_application_context(request)

        # Add credentials if provided
        if request.credentials:
            prompt += self._build_credentials_section(request.credentials)

        # Add test data if provided
        if request.test_data:
            prompt += self._build_test_data_section(request.test_data)

        # Add test-specific instructions
        prompt += self._build_test_instructions(request)

        # Add output format specification
        prompt += self._build_output_format(request)

        logger.debug(f"Generated prompt length: {len(prompt)}")
        return prompt

    def _build_base_prompt(self, request: TestCaseGenerateRequest) -> str:
        """Build base prompt introduction."""
        return f"""You are an expert QA test case generator. Generate a comprehensive test case based on the following requirements.

Application Details:
- URL: {request.app_url}
- Description: {request.app_description}
- Test Type: {request.test_type}

Test Requirements:
{request.requirements}

"""

    def _build_application_context(self, request: TestCaseGenerateRequest) -> str:
        """Build application context section."""
        context_lines = []

        # Add test type context
        type_context = self._get_test_type_context(request.test_type)
        if type_context:
            context_lines.append(f"Test Type Context:\n{type_context}\n")

        # Add tags context
        if request.tags:
            context_lines.append(f"Test Tags: {', '.join(request.tags)}\n")

        return "".join(context_lines)

    def _build_credentials_section(self, credentials: Dict[str, str]) -> str:
        """Build credentials section."""
        return f"\nTest Credentials:\n{json.dumps(credentials, indent=2)}\n"

    def _build_test_data_section(self, test_data: Dict[str, Any]) -> str:
        """Build test data section."""
        return f"\nTest Data:\n{json.dumps(test_data, indent=2)}\n"

    def _build_test_instructions(self, request: TestCaseGenerateRequest) -> str:
        """Build test-specific instructions."""
        instructions = f"""
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
- fill: Fill form with multiple fields (params: dict of selectors and values)
- check: Check checkbox (params: selector)
- uncheck: Uncheck checkbox (params: selector)

"""
        return instructions

    def _build_output_format(self, request: TestCaseGenerateRequest) -> str:
        """Build output format specification."""
        return f"""Return ONLY a valid JSON object in this exact format:
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
- Each step should be independent and verifiable
- Include validation steps after critical actions
"""

    def _get_test_type_context(self, test_type: str) -> Optional[str]:
        """Get context-specific instructions for test type."""
        contexts = {
            "functional": "Focus on business logic and user workflows",
            "ui": "Focus on user interface elements, visual design, and user experience",
            "api": "Focus on API endpoints, request/response validation, and error handling",
            "e2e": "Focus on complete user journeys from start to finish across multiple pages",
            "performance": "Focus on load times, response times, and resource usage",
            "security": "Focus on authentication, authorization, and data protection",
            "smoke": "Focus on critical functionality to determine system stability",
            "regression": "Focus on areas that have been recently modified"
        }
        return contexts.get(test_type)

    def get_prompt_template(self, test_type: str) -> PromptTemplate:
        """
        Get prompt template for specific test type.

        Args:
            test_type: Type of test

        Returns:
            PromptTemplate: Template for the test type
        """
        return self.templates.get(test_type, self.templates["functional"])

    def _get_default_templates(self) -> Dict[str, PromptTemplate]:
        """Get default prompt templates."""
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
            ),
            "performance": PromptTemplate(
                name="Performance Test",
                test_type="performance",
                description="Template for performance testing",
                template="Generate performance test cases for {requirements}",
                variables=["requirements"]
            ),
            "security": PromptTemplate(
                name="Security Test",
                test_type="security",
                description="Template for security testing",
                template="Generate security test cases for {requirements}",
                variables=["requirements"]
            )
        }

    def build_batch_prompt(
        self,
        requests: List[TestCaseGenerateRequest]
    ) -> str:
        """
        Build prompt for batch test generation.

        Args:
            requests: List of test generation requests

        Returns:
            str: Formatted batch prompt
        """
        prompt = """You are an expert QA test case generator. Generate multiple test cases based on the following requirements.

"""
        for idx, request in enumerate(requests, 1):
            prompt += f"\n## Test Case {idx}\n"
            prompt += f"Requirements: {request.requirements}\n"
            prompt += f"Test Type: {request.test_type}\n"
            prompt += f"Max Steps: {request.max_steps}\n\n"

        prompt += """Generate each test case as a separate JSON object, separated by ---.
Follow the same format as single test generation.

"""
        return prompt
