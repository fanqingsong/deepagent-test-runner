"""
Integration tests for refactored TestCaseGenerator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.test_case_generator import TestCaseGenerator
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.test_generation import TestCaseGenerateRequest, GeneratedTestCase, GeneratedTestStep


class TestTestCaseGeneratorIntegration:
    """Integration tests for refactored TestCaseGenerator."""

    @pytest.fixture
    def db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def sample_request(self):
        """Create sample test generation request."""
        return TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test application for login testing",
            requirements="Test user login with valid credentials",
            test_type="functional",
            max_steps=10,
            tags=["smoke", "authentication"]
        )

    @pytest.fixture
    def generator(self, db_session):
        """Create TestCaseGenerator with all dependencies."""
        llm_client = LLMClient(api_key="test_key")
        prompt_builder = PromptBuilder()
        response_parser = ResponseParser()
        repository = TestCaseRepository(db_session)

        return TestCaseGenerator(
            llm_client=llm_client,
            prompt_builder=prompt_builder,
            response_parser=response_parser,
            repository=repository
        )

    @pytest.mark.asyncio
    async def test_generate_test_case_full_workflow(self, generator, sample_request):
        """Test complete workflow from request to test case."""
        # Mock LLM response
        llm_response = '''{
  "name": "User Login Test",
  "description": "Test user login with valid credentials",
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
    },
    {
      "step_number": 3,
      "description": "Enter password",
      "type": "input",
      "params": {"selector": "#password", "value": "secret123"},
      "expected_result": "Password entered"
    }
  ]
}'''

        # Mock LLM client
        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            # Mock repository
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, return_value=1):
                result = await generator.generate_test_case(sample_request)

                # Verify result structure
                assert "test_definition_id" in result
                assert "test_case" in result
                assert "metadata" in result

                # Verify test case data
                assert result["test_case"]["name"] == "User Login Test"
                assert len(result["test_case"]["steps"]) == 3
                assert result["metadata"]["test_type"] == "functional"
                assert result["metadata"]["total_steps"] == 3

    @pytest.mark.asyncio
    async def test_generate_test_case_without_db(self, generator, sample_request):
        """Test generation without database persistence."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": "Result"}]}'

        # Create generator without repository
        generator_no_db = TestCaseGenerator(
            llm_client=generator.llm_client,
            prompt_builder=generator.prompt_builder,
            response_parser=generator.response_parser,
            repository=None
        )

        with patch.object(generator_no_db.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            result = await generator_no_db.generate_test_case(sample_request)

                # Should succeed without database
                assert result["test_definition_id"] is None
                assert result["test_case"]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_generate_batch_test_cases(self, generator, sample_request):
        """Test batch generation of multiple test cases."""
        requests = [
            sample_request,
            TestCaseGenerateRequest(
                app_url="https://example.com",
                app_description="Test app",
                requirements="Test logout functionality",
                test_type="functional",
                max_steps=5
            )
        ]

        llm_responses = [
            '{"name": "Login Test", "steps": [{"step_number": 1, "description": "Step 1", "type": "verify", "params": {}, "expected_result": ""}]}',
            '{"name": "Logout Test", "steps": [{"step_number": 1, "description": "Step 1", "type": "verify", "params": {}, "expected_result": ""}]}'
        ]

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, side_effect=llm_responses):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, side_effect=[1, 2]):
                result = await generator.generate_batch(requests)

                # Verify batch result structure
                assert "generated_tests" in result
                assert "summary" in result
                assert "failed" in result

                # Verify summary
                assert result["summary"]["total"] == 2
                assert result["summary"]["succeeded"] == 2
                assert result["summary"]["failed"] == 0

    @pytest.mark.asyncio
    async def test_generate_batch_with_failures(self, generator, sample_request):
        """Test batch generation with some failures."""
        requests = [sample_request, sample_request]

        # First succeeds, second fails
        llm_responses = [
            '{"name": "Success Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": ""}]}',
            Exception("LLM API error")
        ]

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, side_effect=llm_responses):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, return_value=1):
                result = await generator.generate_batch(requests)

                # Verify one succeeded, one failed
                assert result["summary"]["succeeded"] == 1
                assert result["summary"]["failed"] == 1
                assert len(result["failed"]) == 1
                assert result["failed"][0]["error"] == "LLM API error"

    @pytest.mark.asyncio
    async def test_health_check_all_components(self, generator):
        """Test health check for all components."""
        with patch.object(generator.llm_client, 'health_check', new_callable=AsyncMock, return_value=True):
            with patch.object(generator.repository, 'count_test_cases', new_callable=AsyncMock, return_value=10):
                health = await generator.health_check()

                assert health["llm_client"] is True
                assert health["prompt_builder"] is True
                assert health["response_parser"] is True
                assert health["repository"] is True

    @pytest.mark.asyncio
    async def test_health_check_without_repository(self):
        """Test health check when repository is not configured."""
        generator = TestCaseGenerator(
            llm_client=LLMClient(api_key="test"),
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser(),
            repository=None
        )

        with patch.object(generator.llm_client, 'health_check', new_callable=AsyncMock, return_value=True):
            health = await generator.health_check()

                assert health["repository"] is None

    @pytest.mark.asyncio
    async def test_validate_request_valid(self, generator, sample_request):
        """Test validation of valid request."""
        result = await generator.validate_request(sample_request)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_request_missing_url(self, generator):
        """Test validation fails with missing URL."""
        request = TestCaseGenerateRequest(
            app_url="",  # Empty URL
            app_description="Test app",
            requirements="Test requirements " * 5,  # Make it long enough
            test_type="functional"
        )

        result = await generator.validate_request(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_request_short_requirements(self, generator):
        """Test validation fails with short requirements."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Too short",  # Less than 20 characters
            test_type="functional"
        )

        result = await generator.validate_request(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_request_invalid_max_steps(self, generator):
        """Test validation fails with invalid max_steps."""
        request = TestCaseGenerateRequest(
            app_url="https://example.com",
            app_description="Test app",
            requirements="Test requirements " * 5,
            test_type="functional",
            max_steps=25  # Over limit of 20
        )

        result = await generator.validate_request(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_estimate_generation_time(self, generator):
        """Test generation time estimation."""
        result = await generator.estimate_generation_time(num_requests=5)

        assert result["num_requests"] == 5
        assert result["estimated_seconds"] == 150  # 5 * 30
        assert result["estimated_minutes"] == 2.5
        assert result["estimated_time_per_test"] == 30

    @pytest.mark.asyncio
    async def test_get_prompt_template(self, generator):
        """Test getting prompt templates."""
        template = generator.get_prompt_template("functional")

        assert template is not None
        assert template.name == "Functional Test"
        assert template.test_type == "functional"

    @pytest.mark.asyncio
    async def test_set_repository(self, generator, db_session):
        """Test setting repository dynamically."""
        new_repository = TestCaseRepository(db_session)

        generator.set_repository(db_session)

        assert generator.repository is not None

    @pytest.mark.asyncio
    async def test_generate_with_custom_created_by(self, generator, sample_request):
        """Test generation with custom created_by user."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": ""}]}'

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, return_value=1) as mock_create:
                await generator.generate_test_case(sample_request, created_by=42)

                # Verify created_by was passed
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['created_by'] == 42

    @pytest.mark.asyncio
    async def test_backward_compatibility_original_interface(self, generator, sample_request):
        """Test that original interface is maintained for backward compatibility."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": ""}]}'

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, return_value=1):
                # Original interface: request parameter only
                result = await generator.generate_test_case(sample_request)

                # Should work the same as with optional parameters
                assert "test_definition_id" in result
                assert "test_case" in result
                assert "metadata" in result

    @pytest.mark.asyncio
    async def test_workflow_components_called_in_order(self, generator, sample_request):
        """Test that workflow components are called in correct order."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": ""}]}'

        call_order = []

        # Mock prompt builder
        original_build_prompt = generator.prompt_builder.build_test_generation_prompt
        def track_prompt_build(*args, **kwargs):
            call_order.append('prompt_builder')
            return original_build_prompt(*args, **kwargs)

        generator.prompt_builder.build_test_generation_prompt = track_prompt_build

        # Mock LLM client
        async def track_llm_call(*args, **kwargs):
            call_order.append('llm_client')
            return llm_response

        generator.llm_client.generate_test_case = track_llm_call

        # Mock response parser
        original_parse = generator.response_parser.parse_test_case_response
        def track_parse(*args, **kwargs):
            call_order.append('response_parser')
            return original_parse(*args, **kwargs)

        generator.response_parser.parse_test_case_response = track_parse

        # Mock repository
        async def track_repository(*args, **kwargs):
            call_order.append('repository')
            return 1

        generator.repository.create_test_case = track_repository

        # Execute workflow
        await generator.generate_test_case(sample_request)

        # Verify order
        assert call_order == ['prompt_builder', 'llm_client', 'response_parser', 'repository']

    @pytest.mark.asyncio
    async def test_llm_client_failure_propagates(self, generator, sample_request):
        """Test that LLM client failures are properly propagated."""
        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, side_effect=Exception("LLM failed")):
            with pytest.raises(Exception, match="LLM failed"):
                await generator.generate_test_case(sample_request)

    @pytest.mark.asyncio
    async def test_response_parser_failure_propagates(self, generator, sample_request):
        """Test that response parser failures are properly propagated."""
        invalid_response = "Invalid JSON response"

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=invalid_response):
            with pytest.raises(ValueError):  # Response parser raises ValueError for invalid JSON
                await generator.generate_test_case(sample_request)

    @pytest.mark.asyncio
    async def test_repository_failure_propagates(self, generator, sample_request):
        """Test that repository failures are properly propagated."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": ""}]}'

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, side_effect=Exception("DB error")):
                with pytest.raises(Exception, match="DB error"):
                    await generator.generate_test_case(sample_request)

    @pytest.mark.asyncio
    async def test_metadata_completeness(self, generator, sample_request):
        """Test that response metadata is complete."""
        llm_response = '{"name": "Test", "steps": [{"step_number": 1, "description": "Step", "type": "verify", "params": {}, "expected_result": "Result"}]}'

        with patch.object(generator.llm_client, 'generate_test_case', new_callable=AsyncMock, return_value=llm_response):
            with patch.object(generator.repository, 'create_test_case', new_callable=AsyncMock, return_value=1):
                result = await generator.generate_test_case(sample_request)

                metadata = result["metadata"]
                assert "generated_at" in metadata
                assert "ai_model" in metadata
                assert "test_type" in metadata
                assert "total_steps" in metadata
                assert metadata["test_type"] == "functional"
                assert metadata["total_steps"] == 1
