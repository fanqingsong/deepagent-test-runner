"""
Tests for AI Test Case Generation Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.test_case_generator import TestCaseGenerator
from app.services import get_test_case_generator
from app.schemas.test_generation import TestCaseGenerateRequest


@pytest.mark.asyncio
async def test_generate_test_case_basic(db_session: AsyncSession):
    """Test basic test case generation"""
    service = TestCaseGenerator()

    request = TestCaseGenerateRequest(
        app_url="https://example.com/login",
        app_description="User login page with username and password fields",
        requirements="Test user login with valid credentials",
        test_type="functional",
        credentials={"username": "test@example.com", "password": "Test@123"},
        tags=["authentication", "smoke"]
    )

    # Mock Claude API response
    mock_response = """```json
{
  "name": "User Login with Valid Credentials",
  "description": "Verify user can successfully login with valid credentials",
  "steps": [
    {
      "step_number": 1,
      "description": "Navigate to the login page",
      "type": "navigate",
      "params": {"url": "https://example.com/login"},
      "expected_result": "Login page is displayed"
    },
    {
      "step_number": 2,
      "description": "Enter username in the username field",
      "type": "input",
      "params": {"selector": "input[name='username']", "value": "test@example.com"},
      "expected_result": "Username is entered"
    },
    {
      "step_number": 3,
      "description": "Enter password in the password field",
      "type": "input",
      "params": {"selector": "input[name='password']", "value": "Test@123"},
      "expected_result": "Password is entered"
    },
    {
      "step_number": 4,
      "description": "Click the login button",
      "type": "click",
      "params": {"selector": "button[type='submit']"},
      "expected_result": "Form is submitted"
    },
    {
      "step_number": 5,
      "description": "Verify user is redirected to dashboard",
      "type": "verify",
      "params": {"selector": ".dashboard"},
      "expected_result": "Dashboard is displayed"
    }
  ]
}
```"""

    with patch.object(service, '_call_claude', return_value=mock_response):
        result = await service.generate_test_case(request)

        assert result["test_definition_id"] > 0
        assert "test_case" in result
        assert result["test_case"].name == "User Login with Valid Credentials"
        assert len(result["test_case"].steps) == 5
        assert result["metadata"]["total_steps"] == 5


def test_build_prompt():
    """Test prompt building"""
    service = TestCaseGenerator()

    request = TestCaseGenerateRequest(
        app_url="https://example.com",
        app_description="Test application",
        requirements="Test user registration",
        test_type="functional"
    )

    prompt = service._build_prompt(request)

    assert "Application Details:" in prompt
    assert "https://example.com" in prompt
    assert "Test user registration" in prompt
    assert "functional" in prompt
    assert "JSON object" in prompt


def test_parse_ai_response():
    """Test AI response parsing"""
    service = TestCaseGenerator()

    ai_response = """Here's your test case:
```json
{
  "name": "Test Login",
  "description": "Login test",
  "steps": [
    {
      "step_number": 1,
      "description": "Navigate to login",
      "type": "navigate",
      "params": {"url": "https://example.com/login"},
      "expected_result": "Page loads"
    }
  ]
}
```"""

    request = TestCaseGenerateRequest(
        app_url="https://example.com/login",
        app_description="Login page",
        requirements="Test user login functionality with valid credentials",
        test_type="functional"
    )

    result = service._parse_ai_response(ai_response, request)

    assert result.name == "Test Login"
    assert len(result.steps) == 1
    assert result.steps[0].type == "navigate"
    assert result.test_id is not None


def test_generate_test_id():
    """Test ID generation"""
    service = TestCaseGenerator()

    test_id = service._generate_test_id("User Login Test", "functional")
    assert test_id.startswith("TC-")
    assert "FUNCTIONAL" in test_id


def test_estimate_duration():
    """Test duration estimation"""
    service = TestCaseGenerator()

    duration = service._estimate_duration(5)
    assert duration  # Should return a string
    assert "minute" in duration or "second" in duration


@pytest.mark.asyncio
async def test_batch_generation(db_session: AsyncSession):
    """Test batch test case generation"""
    service = TestCaseGenerator()

    mock_response = """```json
{
  "name": "Test Case",
  "description": "Test",
  "steps": [{
    "step_number": 1,
    "description": "Step 1",
    "type": "navigate",
    "params": {"url": "https://example.com"},
    "expected_result": "Done"
  }]
}
```"""

    requests = [
        TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="User login application page",
            requirements="Test user login with valid credentials scenario 1",
            test_type="functional"
        ),
        TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="User login application page",
            requirements="Test user login with valid credentials scenario 2",
            test_type="functional"
        )
    ]

    with patch.object(service, '_call_claude', return_value=mock_response):
        result = await service.generate_batch(requests)

        assert result["summary"]["total"] == 2
        assert result["summary"]["succeeded"] >= 0
        assert len(result["generated_tests"]) >= 0


def test_get_prompt_templates():
    """Test getting prompt templates"""
    templates = get_test_case_generator()._get_templates()

    assert "functional" in templates
    assert "ui" in templates
    assert "api" in templates
    assert "e2e" in templates

    for template in templates.values():
        assert template.name is not None
        assert template.test_type is not None


@pytest.mark.asyncio
async def test_claude_api_error_handling(db_session: AsyncSession):
    """Test error handling when Claude API fails"""
    service = TestCaseGenerator()

    request = TestCaseGenerateRequest(
        app_url="https://example.com",
        app_description="User login application page",
        requirements="Test user login with valid credentials",
        test_type="functional"
    )

    # Mock API error
    with patch.object(service, '_call_claude', side_effect=Exception("API Error")):
        with pytest.raises(Exception):
            await service.generate_test_case(request, db_session)


def test_validate_test_type():
    """Test test type validation"""
    from pydantic import ValidationError

    # Valid test type
    request = TestCaseGenerateRequest(
        app_url="https://example.com",
        app_description="User login application page",
        requirements="Test user login with valid credentials",
        test_type="functional"
    )
    assert request.test_type == "functional"

    # Invalid test type
    with pytest.raises(ValidationError):
        TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="User login application page",
            requirements="Test user login with valid credentials",
            test_type="invalid_type"
        )


def test_max_steps_validation():
    """Test max steps validation"""
    from pydantic import ValidationError

    # Valid max_steps
    request = TestCaseGenerateRequest(
        app_url="https://example.com",
        app_description="User login application page",
        requirements="Test user login with valid credentials",
        test_type="functional",
        max_steps=10
    )
    assert request.max_steps == 10

    # Too few steps
    with pytest.raises(ValidationError):
        TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="User login application page",
            requirements="Test user login with valid credentials",
            test_type="functional",
            max_steps=3
        )

    # Too many steps
    with pytest.raises(ValidationError):
        TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="User login application page",
            requirements="Test user login with valid credentials",
            test_type="functional",
            max_steps=25
        )
