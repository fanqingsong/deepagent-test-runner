"""
Unit tests for ResponseParser
"""

import pytest

from app.services.response_parser import ResponseParser
from app.schemas.test_generation import TestCaseGenerateRequest, GeneratedTestStep


class TestResponseParser:
    """Test suite for ResponseParser component."""

    @pytest.fixture
    def response_parser(self):
        """Create ResponseParser instance for testing."""
        return ResponseParser()

    @pytest.fixture
    def sample_request(self):
        """Create sample test generation request."""
        return TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test application",
            requirements="Test login functionality",
            test_type="functional",
            max_steps=10
        )

    @pytest.fixture
    def valid_json_response(self):
        """Create valid JSON response."""
        return '''{
  "name": "Login Test",
  "description": "Test user login flow",
  "steps": [
    {
      "step_number": 1,
      "description": "Navigate to login page",
      "type": "navigate",
      "params": {"url": "https://example.com/login"},
      "expected_result": "Login page loads"
    },
    {
      "step_number": 2,
      "description": "Enter username",
      "type": "input",
      "params": {"selector": "#username", "value": "test@example.com"},
      "expected_result": "Username entered"
    }
  ]
}'''

    def test_init(self, response_parser):
        """Test initialization."""
        assert response_parser is not None
        assert hasattr(response_parser, 'step_number')

    def test_parse_valid_response(self, response_parser, valid_json_response, sample_request):
        """Test parsing valid JSON response."""
        test_case = response_parser.parse_test_case_response(valid_json_response, sample_request)

        assert test_case.name == "Login Test"
        assert test_case.description == "Test user login flow"
        assert len(test_case.steps) == 2
        assert test_case.url == "https://example.com"

    def test_parse_response_with_extra_text(self, response_parser, sample_request):
        """Test parsing response with extra text around JSON."""
        response = "Here is the generated test case:\n" + self.valid_json_response() + "\nHope this helps!"

        test_case = response_parser.parse_test_case_response(response, sample_request)

        assert test_case.name == "Login Test"
        assert len(test_case.steps) == 2

    def test_parse_response_missing_json_raises_error(self, response_parser, sample_request):
        """Test that response without JSON raises ValueError."""
        response = "This is plain text without any JSON"

        with pytest.raises(ValueError, match="No JSON found"):
            response_parser.parse_test_case_response(response, sample_request)

    def test_parse_response_invalid_json_raises_error(self, response_parser, sample_request):
        """Test that invalid JSON raises ValueError."""
        response = '{"name": "Test", "invalid": }'

        with pytest.raises(ValueError, match="Invalid JSON"):
            response_parser.parse_test_case_response(response, sample_request)

    def test_parse_response_missing_name_raises_error(self, response_parser, sample_request):
        """Test that response missing 'name' field raises ValueError."""
        response = '{"steps": []}'

        with pytest.raises(ValueError, match="missing required fields"):
            response_parser.parse_test_case_response(response, sample_request)

    def test_parse_response_missing_steps_raises_error(self, response_parser, sample_request):
        """Test that response missing 'steps' field raises ValueError."""
        response = '{"name": "Test"}'

        with pytest.raises(ValueError, match="missing required fields"):
            response_parser.parse_test_case_response(response, sample_request)

    def test_parse_response_empty_steps_raises_error(self, response_parser, sample_request):
        """Test that empty steps array raises ValueError."""
        response = '{"name": "Test", "steps": []}'

        with pytest.raises(ValueError, match="at least one step"):
            response_parser.parse_test_case_response(response, sample_request)

    def test_parse_steps_with_all_fields(self, response_parser, valid_json_response, sample_request):
        """Test parsing steps with all fields present."""
        test_case = response_parser.parse_test_case_response(valid_json_response, sample_request)

        assert len(test_case.steps) == 2

        # Check first step
        step1 = test_case.steps[0]
        assert step1.step_number == 1
        assert step1.description == "Navigate to login page"
        assert step1.type == "navigate"
        assert step1.params == {"url": "https://example.com/login"}
        assert step1.expected_result == "Login page loads"

    def test_parse_steps_missing_defaults_to_verify(self, response_parser, sample_request):
        """Test that missing step type defaults to 'verify'."""
        response = '''{
  "name": "Test",
  "steps": [{
    "step_number": 1,
    "description": "Test step"
  }]
}'''

        test_case = response_parser.parse_test_case_response(response, sample_request)

        assert test_case.steps[0].type == "verify"

    def test_parse_steps_auto_numbering(self, response_parser, sample_request):
        """Test that steps without numbers are auto-numbered."""
        response = '''{
  "name": "Test",
  "steps": [
    {"description": "Step 1", "expected_result": "Result 1"},
    {"description": "Step 2", "expected_result": "Result 2"}
  ]
}'''

        test_case = response_parser.parse_test_case_response(response, sample_request)

        assert test_case.steps[0].step_number == 1
        assert test_case.steps[1].step_number == 2

    def test_parse_steps_duplicate_numbers(self, response_parser, sample_request):
        """Test handling of duplicate step numbers."""
        response = '''{
  "name": "Test",
  "steps": [
    {"step_number": 1, "description": "Step 1"},
    {"step_number": 1, "description": "Step 2"}
  ]
}'''

        test_case = response_parser.parse_test_case_response(response, sample_request)

        # Second step should be renumbered to 2
        assert test_case.steps[0].step_number == 1
        assert test_case.steps[1].step_number == 2

    def test_generate_test_id(self, response_parser):
        """Test test ID generation."""
        test_id = response_parser._generate_test_id("Login Functionality Test", "functional")

        assert test_id == "TC-LOGIN-FUNCTIONAL-TEST-FUNCTIONAL"

    def test_generate_test_id_short_name(self, response_parser):
        """Test test ID generation with short name."""
        test_id = response_parser._generate_test_id("Login", "ui")

        assert test_id == "TC-LOGIN-UI"

    def test_generate_test_id_empty_name(self, response_parser):
        """Test test ID generation with empty name."""
        test_id = response_parser._generate_test_id("", "api")

        assert test_id == "TC-TEST-API"

    def test_estimate_duration_seconds(self, response_parser):
        """Test duration estimation for short tests."""
        duration = response_parser._estimate_duration(1)

        assert duration == "30 seconds"

    def test_estimate_duration_minutes(self, response_parser):
        """Test duration estimation for longer tests."""
        duration = response_parser._estimate_duration(3)

        assert "minutes" in duration
        assert "1-3 minutes" == duration or "1-" in duration

    def test_validate_step_params_valid(self, response_parser):
        """Test step parameter validation with valid params."""
        assert response_parser.validate_step_params("navigate", {"url": "http://example.com"})
        assert response_parser.validate_step_params("click", {"selector": "#button"})
        assert response_parser.validate_step_params("input", {"selector": "#field", "value": "text"})

    def test_validate_step_params_invalid(self, response_parser):
        """Test step parameter validation with invalid params."""
        assert not response_parser.validate_step_params("navigate", {})
        assert not response_parser.validate_step_params("click", {"wrong": "param"})
        assert not response_parser.validate_step_params("unknown_type", {})

    def test_sanitize_test_name(self, response_parser):
        """Test test name sanitization."""
        sanitized = response_parser.sanitize_test_name("Test Name!@#$%^&*()")

        assert sanitized == "Test_Name"
        assert "!" not in sanitized
        assert "@" not in sanitized

    def test_parse_batch_response(self, response_parser, sample_request):
        """Test parsing batch response."""
        response1 = '''{"name": "Test 1", "steps": [{"step_number": 1, "description": "Step 1", "type": "verify", "params": {}, "expected_result": ""}]}'''
        response2 = '''{"name": "Test 2", "steps": [{"step_number": 1, "description": "Step 2", "type": "verify", "params": {}, "expected_result": ""}]}'''

        batch_response = response1 + "\n---\n" + response2
        requests = [sample_request, sample_request]

        test_cases = response_parser.parse_batch_response(batch_response, requests)

        assert len(test_cases) == 2
        assert test_cases[0].name == "Test 1"
        assert test_cases[1].name == "Test 2"

    def test_parse_step_with_invalid_type_defaults(self, response_parser, sample_request):
        """Test that invalid step types default to 'verify'."""
        response = '''{
  "name": "Test",
  "steps": [{
    "step_number": 1,
    "description": "Test step",
    "type": "invalid_type",
    "expected_result": "Some result"
  }]
}'''

        test_case = response_parser.parse_test_case_response(response, sample_request)

        assert test_case.steps[0].type == "verify"

    def test_generated_case_has_metadata(self, response_parser, valid_json_response, sample_request):
        """Test that generated case has all metadata populated."""
        test_case = response_parser.parse_test_case_response(valid_json_response, sample_request)

        assert test_case.test_id is not None
        assert test_case.url == sample_request.app_url
        assert test_case.tags == sample_request.tags
        assert test_case.estimated_duration is not None
        assert len(test_case.estimated_duration) > 0

    def test_parse_response_minimal_valid(self, response_parser, sample_request):
        """Test parsing minimal valid response."""
        response = '''{
  "name": "Minimal Test",
  "steps": [{
    "step_number": 1,
    "description": "A step",
    "type": "verify",
    "params": {},
    "expected_result": "Expected"
  }]
}'''

        test_case = response_parser.parse_test_case_response(response, sample_request)

        assert test_case.name == "Minimal Test"
        assert len(test_case.steps) == 1
        assert test_case.steps[0].description == "A step"
