"""
Tests for Script Generation Service

Unit tests for the ScriptGenerationService class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.script_generation_service import ScriptGenerationService
from app.models.test_definition import TestDefinition
from app.schemas.test_definition import ScriptResponse


class TestScriptGenerationService:
    """Test suite for ScriptGenerationService."""

    @pytest.fixture
    def db_session(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def generation_service(self, db_session):
        """Create a ScriptGenerationService instance."""
        return ScriptGenerationService(db_session)

    @pytest.fixture
    def mock_test_definition(self):
        """Create a mock TestDefinition."""
        test_def = MagicMock(spec=TestDefinition)
        test_def.id = 1
        test_def.url = "https://example.com"
        test_def.test_goal = "Test login functionality"
        test_def.description = "Login test with valid credentials"
        test_def.playwright_script = "async def run_test(page): ..."
        test_def.script_status = "validated"
        test_def.script_metadata = {"version": "1.0"}
        test_def.execution_mode = "script"
        return test_def

    @pytest.mark.asyncio
    async def test_get_test_definition_or_404_found(
        self,
        generation_service,
        db_session,
        mock_test_definition
    ):
        """Test get_test_definition_or_404 when found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        result = await generation_service.get_test_definition_or_404(1)

        assert result == mock_test_definition
        db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_test_definition_or_404_not_found(
        self,
        generation_service,
        db_session
    ):
        """Test get_test_definition_or_404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        result = await generation_service.get_test_definition_or_404(999)

        assert result is None

    def test_validate_test_definition_for_generation_success(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test validation with valid test definition."""
        # Should not raise
        generation_service.validate_test_definition_for_generation(
            mock_test_definition
        )

    def test_validate_test_definition_for_generation_missing_url(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test validation fails when URL is missing."""
        mock_test_definition.url = None
        mock_test_definition.test_goal = "Test goal"

        with pytest.raises(ValueError, match="must have both url and test_goal"):
            generation_service.validate_test_definition_for_generation(
                mock_test_definition
            )

    def test_validate_test_definition_for_generation_missing_goal(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test validation fails when test_goal is missing."""
        mock_test_definition.url = "https://example.com"
        mock_test_definition.test_goal = None

        with pytest.raises(ValueError, match="must have both url and test_goal"):
            generation_service.validate_test_definition_for_generation(
                mock_test_definition
            )

    def test_should_use_existing_script_validated(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test should use existing validated script."""
        mock_test_definition.script_status = "validated"
        mock_test_definition.playwright_script = "script content"

        result = generation_service.should_use_existing_script(
            mock_test_definition,
            force_regenerate=False
        )

        assert result is True

    def test_should_use_existing_script_force_regenerate(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test force_regenerate overrides existing script."""
        mock_test_definition.script_status = "validated"
        mock_test_definition.playwright_script = "script content"

        result = generation_service.should_use_existing_script(
            mock_test_definition,
            force_regenerate=True
        )

        assert result is False

    def test_should_use_existing_script_draft_status(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test should not use script with draft status."""
        mock_test_definition.script_status = "draft"
        mock_test_definition.playwright_script = "script content"

        result = generation_service.should_use_existing_script(
            mock_test_definition,
            force_regenerate=False
        )

        assert result is False

    def test_build_script_response(
        self,
        generation_service,
        mock_test_definition
    ):
        """Test building ScriptResponse from TestDefinition."""
        response = generation_service.build_script_response(
            mock_test_definition
        )

        assert isinstance(response, ScriptResponse)
        assert response.playwright_script == mock_test_definition.playwright_script
        assert response.script_status == mock_test_definition.script_status
        assert response.execution_mode == mock_test_definition.execution_mode

    @pytest.mark.asyncio
    async def test_generate_description_success(
        self,
        generation_service
    ):
        """Test successful description generation."""
        mock_llm_response = MagicMock()
        mock_llm_response.content = "Test login functionality with valid credentials"

        with patch('app.services.script_generation_service.get_llm') as mock_get_llm, \
             patch('app.services.script_generation_service.llm_usage_context'):

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm

            description = await generation_service.generate_description(
                test_goal="Test login",
                test_definition_id=1
            )

            assert description == "Test login functionality with valid credentials"
            mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_description_empty_goal(self, generation_service):
        """Test description generation fails with empty goal."""
        with pytest.raises(ValueError, match="Test goal cannot be empty"):
            await generation_service.generate_description("", 1)

    @pytest.mark.asyncio
    async def test_generate_description_llm_failure(
        self,
        generation_service
    ):
        """Test description generation handles LLM errors."""
        with patch('app.services.script_generation_service.get_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.side_effect = Exception("LLM API error")
            mock_get_llm.return_value = mock_llm

            with pytest.raises(RuntimeError, match="Failed to generate description"):
                await generation_service.generate_description(
                    test_goal="Test goal",
                    test_definition_id=1
                )

    @pytest.mark.asyncio
    async def test_prepare_script_generation_use_existing(
        self,
        generation_service,
        db_session,
        mock_test_definition
    ):
        """Test prepare_script_generation returns existing script."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.script_status = "validated"
        mock_test_definition.playwright_script = "existing script"

        test_def, response = await generation_service.prepare_script_generation(
            test_definition_id=1,
            force_regenerate=False
        )

        assert test_def == mock_test_definition
        assert response is not None
        assert response.playwright_script == "existing script"
        # Verify status was not changed to generating
        assert mock_test_definition.script_status == "validated"

    @pytest.mark.asyncio
    async def test_prepare_script_generation_force_regenerate(
        self,
        generation_service,
        db_session,
        mock_test_definition
    ):
        """Test prepare_script_generation with force_regenerate."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.script_status = "validated"
        mock_test_definition.playwright_script = "existing script"

        test_def, response = await generation_service.prepare_script_generation(
            test_definition_id=1,
            force_regenerate=True
        )

        assert test_def == mock_test_definition
        assert response is None
        # Verify status was changed to generating
        assert mock_test_definition.script_status == "generating"
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_script_generation_not_found(
        self,
        generation_service,
        db_session
    ):
        """Test prepare_script_generation with non-existent test definition."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test definition not found"):
            await generation_service.prepare_script_generation(999)

    @pytest.mark.asyncio
    async def test_run_script_generation_workflow(
        self,
        generation_service
    ):
        """Test running complete script generation workflow."""
        with patch('app.services.script_generation_service.run_script_generation') as mock_run:
            mock_run.return_value = {
                "playwright_script": "generated script",
                "script_status": "draft",
                "script_metadata": {},
                "execution_mode": "script"
            }

            result = await generation_service.run_script_generation_workflow(
                test_definition_id=1,
                url="https://example.com",
                goal="Test goal",
                description="Test description"
            )

            assert result["playwright_script"] == "generated script"
            assert result["script_status"] == "draft"
            mock_run.assert_called_once()
