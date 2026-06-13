"""
Response Parser Service

Parses and validates LLM responses into structured test cases.
Handles JSON extraction, validation, and error recovery.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.schemas.test_generation import (
    GeneratedTestCase,
    GeneratedTestStep,
    TestCaseGenerateRequest
)

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parses LLM responses into structured test cases.

    Handles JSON extraction, structure validation,
    and error recovery from malformed responses.
    """

    def __init__(self):
        """Initialize response parser."""
        self.step_number = 1

    def parse_test_case_response(
        self,
        ai_response: str,
        request: TestCaseGenerateRequest
    ) -> GeneratedTestCase:
        """
        Parse LLM response into structured test case.

        Args:
            ai_response: Raw LLM response text
            request: Original generation request

        Returns:
            GeneratedTestCase: Parsed and validated test case

        Raises:
            ValueError: If response is invalid or missing required fields
        """
        # Extract JSON from response
        case_data = self._extract_json(ai_response)

        # Validate required fields
        self._validate_case_structure(case_data)

        # Convert steps
        steps = self._parse_steps(case_data.get("steps", []))

        # Generate metadata
        test_id = self._generate_test_id(
            case_data["name"],
            request.test_type
        )
        estimated_duration = self._estimate_duration(len(steps))

        # Create test case
        test_case = GeneratedTestCase(
            name=case_data["name"],
            description=case_data.get("description", ""),
            test_id=test_id,
            url=request.app_url,
            tags=request.tags,
            steps=steps,
            estimated_duration=estimated_duration
        )

        logger.info(
            f"Parsed test case '{test_case.name}' with {len(steps)} steps, "
            f"ID: {test_id}, duration: {estimated_duration}"
        )

        return test_case

    def _extract_json(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.

        Args:
            response: Raw response text

        Returns:
            dict: Parsed JSON data

        Raises:
            ValueError: If JSON cannot be extracted or parsed
        """
        # Try to find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError(
                "No JSON found in AI response. "
                "Response may be malformed or missing JSON output."
            )

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {str(e)}")
            raise ValueError(
                f"Invalid JSON in AI response: {str(e)}"
            ) from e

    def _validate_case_structure(self, case_data: Dict[str, Any]) -> None:
        """
        Validate required fields in test case data.

        Args:
            case_data: Parsed test case data

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["name", "steps"]
        missing_fields = [
            field for field in required_fields
            if field not in case_data
        ]

        if missing_fields:
            raise ValueError(
                f"AI response missing required fields: {', '.join(missing_fields)}"
            )

        if not isinstance(case_data["steps"], list):
            raise ValueError("Test case 'steps' must be a list")

        if len(case_data["steps"]) == 0:
            raise ValueError("Test case must have at least one step")

    def _parse_steps(self, steps_data: List[Dict[str, Any]]) -> List[GeneratedTestStep]:
        """
        Parse and validate test steps.

        Args:
            steps_data: Raw step data from LLM response

        Returns:
            list: Parsed and validated test steps
        """
        steps = []
        seen_numbers = set()

        for idx, step_data in enumerate(steps_data):
            try:
                # Extract step number
                step_number = step_data.get("step_number", idx + 1)

                # Check for duplicate step numbers
                if step_number in seen_numbers:
                    logger.warning(
                        f"Duplicate step number {step_number}, "
                        f"using sequential number {idx + 1}"
                    )
                    step_number = idx + 1
                seen_numbers.add(step_number)

                # Validate required fields
                if "description" not in step_data:
                    raise ValueError(f"Step {step_number} missing description")

                if "type" not in step_data:
                    logger.warning(
                        f"Step {step_number} missing type, defaulting to 'verify'"
                    )
                    step_data["type"] = "verify"

                # Validate step type
                valid_types = {
                    "navigate", "click", "input", "select", "verify",
                    "wait", "hover", "screenshot", "fill", "check", "uncheck"
                }
                if step_data["type"] not in valid_types:
                    logger.warning(
                        f"Invalid step type '{step_data['type']}' in step {step_number}, "
                        f"defaulting to 'verify'"
                    )
                    step_data["type"] = "verify"

                # Create step
                step = GeneratedTestStep(
                    step_number=step_number,
                    description=step_data.get("description", ""),
                    type=step_data.get("type", "verify"),
                    params=step_data.get("params", {}),
                    expected_result=step_data.get("expected_result", "")
                )
                steps.append(step)

            except Exception as e:
                logger.error(f"Failed to parse step {idx}: {str(e)}")
                raise ValueError(
                    f"Invalid step data at index {idx}: {str(e)}"
                ) from e

        return steps

    def _generate_test_id(self, name: str, test_type: str) -> str:
        """
        Generate unique test case ID.

        Args:
            name: Test case name
            test_type: Type of test

        Returns:
            str: Generated test ID
        """
        # Extract key words from name
        words = re.findall(r'\w+', name.upper())
        prefix = "-".join(words[:3]) if len(words) >= 3 else "-".join(words)

        if not prefix:
            prefix = "TEST"

        return f"TC-{prefix}-{test_type.upper()}"

    def _estimate_duration(self, num_steps: int) -> str:
        """
        Estimate test execution duration.

        Args:
            num_steps: Number of test steps

        Returns:
            str: Estimated duration string
        """
        # Assume 30 seconds per step on average
        total_seconds = num_steps * 30
        minutes = total_seconds // 60

        if minutes > 0:
            return f"{minutes}-{minutes + 2} minutes"
        return f"{total_seconds} seconds"

    def parse_batch_response(
        self,
        ai_response: str,
        requests: List[TestCaseGenerateRequest]
    ) -> List[GeneratedTestCase]:
        """
        Parse batch LLM response into multiple test cases.

        Args:
            ai_response: Raw LLM response with multiple test cases
            requests: Original generation requests

        Returns:
            list: Parsed test cases

        Raises:
            ValueError: If response cannot be parsed
        """
        # Split response by separator
        test_cases = []
        parts = ai_response.split("---")

        if len(parts) != len(requests):
            logger.warning(
                f"Expected {len(requests)} test cases, "
                f"found {len(parts)} parts in response"
            )

        for idx, part in enumerate(parts):
            try:
                request = requests[idx] if idx < len(requests) else requests[-1]
                test_case = self.parse_test_case_response(part, request)
                test_cases.append(test_case)
            except Exception as e:
                logger.error(f"Failed to parse test case {idx}: {str(e)}")
                # Continue parsing other test cases
                continue

        return test_cases

    def validate_step_params(self, step_type: str, params: Dict[str, Any]) -> bool:
        """
        Validate step parameters based on step type.

        Args:
            step_type: Type of step
            params: Step parameters

        Returns:
            bool: True if parameters are valid
        """
        required_params = {
            "navigate": ["url"],
            "click": ["selector"],
            "input": ["selector", "value"],
            "select": ["selector", "value"],
            "verify": ["selector"],  # or "text"
            "wait": ["seconds"],  # or "selector"
            "hover": ["selector"],
            "screenshot": ["filename"],
            "fill": [],  # dict of selectors and values
            "check": ["selector"],
            "uncheck": ["selector"]
        }

        if step_type not in required_params:
            return False

        required = required_params[step_type]
        if not required:
            return True  # No required params

        return all(key in params for key in required)

    def sanitize_test_name(self, name: str) -> str:
        """
        Sanitize test case name.

        Args:
            name: Raw test name

        Returns:
            str: Sanitized test name
        """
        # Remove special characters, replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.strip()
