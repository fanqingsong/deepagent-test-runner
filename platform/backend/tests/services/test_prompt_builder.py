"""
Unit tests for PromptBuilder
"""

import pytest

from app.services.prompt_builder import PromptBuilder
from app.schemas.test_generation import TestCaseGenerateRequest


class TestPromptBuilder:
    """Test suite for PromptBuilder component."""

    @pytest.fixture
    def prompt_builder(self):
        """Create PromptBuilder instance for testing."""
        return PromptBuilder()

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

    def test_init(self, prompt_builder):
        """Test initialization creates default templates."""
        assert prompt_builder is not None
        assert hasattr(prompt_builder, 'templates')
        assert len(prompt_builder.templates) > 0

    def test_build_test_generation_prompt_basic(self, prompt_builder, sample_request):
        """Test basic prompt building."""
        prompt = prompt_builder.build_test_generation_prompt(sample_request)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "https://example.com" in prompt
        assert "Test application" in prompt
        assert "Test login functionality" in prompt
        assert "functional" in prompt

    def test_build_prompt_with_credentials(self, prompt_builder):
        """Test prompt building with credentials."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Test requirements",
            credentials={"username": "test", "password": "secret"}
        )

        prompt = prompt_builder.build_test_generation_prompt(request)

        assert "Test Credentials:" in prompt
        assert "username" in prompt
        assert "password" in prompt

    def test_build_prompt_with_test_data(self, prompt_builder):
        """Test prompt building with test data."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Test requirements",
            test_data={"users": ["user1", "user2"]}
        )

        prompt = prompt_builder.build_test_generation_prompt(request)

        assert "Test Data:" in prompt
        assert "users" in prompt

    def test_build_prompt_includes_action_types(self, prompt_builder, sample_request):
        """Test prompt includes action type descriptions."""
        prompt = prompt_builder.build_test_generation_prompt(sample_request)

        assert "navigate:" in prompt
        assert "click:" in prompt
        assert "input:" in prompt
        assert "verify:" in prompt
        assert "wait:" in prompt

    def test_build_prompt_includes_output_format(self, prompt_builder, sample_request):
        """Test prompt includes JSON output format specification."""
        prompt = prompt_builder.build_test_generation_prompt(sample_request)

        assert "Return ONLY a valid JSON object" in prompt
        assert '"name":' in prompt
        assert '"steps":' in prompt
        assert '"step_number":' in prompt
        assert '"description":' in prompt

    def test_build_prompt_respects_max_steps(self, prompt_builder):
        """Test prompt respects max_steps parameter."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Test requirements",
            max_steps=15
        )

        prompt = prompt_builder.build_test_generation_prompt(request)

        assert "15" in prompt
        assert "Generate between 5 and 15 steps" in prompt

    def test_get_test_type_context(self, prompt_builder):
        """Test test type context generation."""
        contexts = {
            "functional": "business logic",
            "ui": "user interface",
            "api": "API endpoints",
            "e2e": "complete user journeys",
            "performance": "load times",
            "security": "authentication"
        }

        for test_type, expected_text in contexts.items():
            context = prompt_builder._get_test_type_context(test_type)
            assert context is not None
            assert expected_text in context

    def test_get_prompt_template(self, prompt_builder):
        """Test getting prompt templates."""
        template = prompt_builder.get_prompt_template("functional")

        assert template is not None
        assert template.name == "Functional Test"
        assert template.test_type == "functional"
        assert "requirements" in template.variables

    def test_get_prompt_template_default(self, prompt_builder):
        """Test default template is returned for unknown type."""
        template = prompt_builder.get_prompt_template("unknown_type")

        assert template is not None
        assert template.test_type == "functional"

    def test_templates_contain_all_types(self, prompt_builder):
        """Test that templates exist for all common test types."""
        expected_types = ["functional", "ui", "api", "e2e", "performance", "security"]

        for test_type in expected_types:
            assert test_type in prompt_builder.templates
            template = prompt_builder.templates[test_type]
            assert template.test_type == test_type

    def test_build_batch_prompt(self, prompt_builder):
        """Test batch prompt building."""
        requests = [
            TestCaseGenerateRequest(
                app_url="https://example.com",
                app_description="Test app",
                requirements="First test",
                test_type="functional",
                max_steps=5
            ),
            TestCaseGenerateRequest(
                app_url="https://example.com",
                app_description="Test app",
                requirements="Second test",
                test_type="ui",
                max_steps=8
            )
        ]

        prompt = prompt_builder.build_batch_prompt(requests)

        assert "Generate multiple test cases" in prompt
        assert "First test" in prompt
        assert "Second test" in prompt
        assert "Test Case 1" in prompt
        assert "Test Case 2" in prompt
        assert "---" in prompt

    def test_prompt_length_reasonable(self, prompt_builder, sample_request):
        """Test that generated prompt has reasonable length."""
        prompt = prompt_builder.build_test_generation_prompt(sample_request)

        # Prompt should be comprehensive but not excessively long
        assert len(prompt) > 500
        assert len(prompt) < 10000

    def test_prompt_with_tags(self, prompt_builder):
        """Test prompt building includes tags."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Test requirements",
            tags=["smoke", "critical"]
        )

        prompt = prompt_builder.build_test_generation_prompt(request)

        assert "Test Tags:" in prompt
        assert "smoke" in prompt
        assert "critical" in prompt

    def test_all_action_types_documented(self, prompt_builder, sample_request):
        """Test that all action types are documented in prompt."""
        prompt = prompt_builder.build_test_generation_prompt(sample_request)

        action_types = [
            "navigate", "click", "input", "select", "verify",
            "wait", "hover", "screenshot", "fill", "check", "uncheck"
        ]

        for action_type in action_types:
            assert f"{action_type}:" in prompt
