"""
Integration Tests for Script Generation Endpoints

Tests for the refactored script generation API endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.test_definition import TestDefinition
from app.models.user import User


@pytest.mark.asyncio
class TestScriptGenerationEndpoints:
    """Test suite for script generation endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_test_definition(self):
        """Create a mock test definition."""
        test_def = MagicMock(spec=TestDefinition)
        test_def.id = 1
        test_def.url = "https://example.com"
        test_def.test_goal = "Test login"
        test_def.description = "Login test"
        test_def.playwright_script = "async def run_test(page): ..."
        test_def.script_status = "validated"
        test_def.script_metadata = {}
        test_def.execution_mode = "script"
        return test_def

    async def test_generate_script_success(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test successful script generation."""
        with patch('app.api.v1.endpoints.script_generation.get_current_user', return_value=mock_user), \
             patch('app.services.script_generation_service.ScriptGenerationService.get_test_definition_or_404', return_value=mock_test_definition), \
             patch('app.services.script_generation_service.run_script_generation') as mock_run:

            mock_run.return_value = {
                "playwright_script": "generated script",
                "script_status": "draft",
                "script_metadata": {},
                "execution_mode": "script"
            }

            response = await async_client.post(
                "/scripts/test-definitions/1/generate-script",
                json={"force_regenerate": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["playwright_script"] == "generated script"
            assert data["script_status"] == "draft"

    async def test_generate_script_use_existing(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test using existing validated script."""
        with patch('app.api.v1.endpoints.script_generation.get_current_user', return_value=mock_user), \
             patch('app.services.script_generation_service.ScriptGenerationService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.post(
                "/scripts/test-definitions/1/generate-script",
                json={"force_regenerate": False}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["playwright_script"] == "async def run_test(page): ..."
            assert data["script_status"] == "validated"

    async def test_generate_script_not_found(
        self,
        async_client: AsyncClient,
        mock_user
    ):
        """Test generating script for non-existent test definition."""
        with patch('app.api.v1.endpoints.script_generation.get_current_user', return_value=mock_user), \
             patch('app.services.script_generation_service.ScriptGenerationService.get_test_definition_or_404', return_value=None):

            response = await async_client.post(
                "/scripts/test-definitions/999/generate-script"
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_generate_script_missing_fields(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test generating script with missing required fields."""
        mock_test_definition.url = None
        mock_test_definition.test_goal = None

        with patch('app.api.v1.endpoints.script_generation.get_current_user', return_value=mock_user), \
             patch('app.services.script_generation_service.ScriptGenerationService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.post(
                "/scripts/test-definitions/1/generate-script",
                json={"force_regenerate": True}
            )

            assert response.status_code == 400
            assert "url and test_goal" in response.json()["detail"]


@pytest.mark.asyncio
class TestScriptValidationEndpoints:
    """Test suite for script validation endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_test_definition(self):
        """Create a mock test definition."""
        test_def = MagicMock(spec=TestDefinition)
        test_def.id = 1
        test_def.url = "https://example.com"
        test_def.playwright_script = "async def run_test(page): return {'status': 'passed'}"
        test_def.script_status = "draft"
        test_def.script_metadata = {}
        test_def.execution_mode = "script"
        return test_def

    async def test_validate_script_success(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test successful script validation."""
        with patch('app.api.v1.endpoints.script_validation.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition), \
             patch('app.services.script_validation_service.ScriptValidationService.validate_script') as mock_validate:

            mock_validate.return_value = {
                "status": "passed",
                "step_results": [],
                "error": None
            }

            response = await async_client.post(
                "/scripts/test-definitions/1/validate-script"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["script_status"] == "validated"

    async def test_validate_script_failure(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test script validation with execution failure."""
        with patch('app.api.v1.endpoints.script_validation.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition), \
             patch('app.services.script_validation_service.ScriptValidationService.validate_script') as mock_validate:

            mock_validate.return_value = {
                "status": "failed",
                "step_results": [],
                "error": "Element not found"
            }

            response = await async_client.post(
                "/scripts/test-definitions/1/validate-script"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["script_status"] == "draft"
            assert "Element not found" in data["script_metadata"]["last_error"]

    async def test_validate_script_no_script(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test validation when no script exists."""
        mock_test_definition.playwright_script = None

        with patch('app.api.v1.endpoints.script_validation.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.post(
                "/scripts/test-definitions/1/validate-script"
            )

            assert response.status_code == 400
            assert "no script" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestScriptManagementEndpoints:
    """Test suite for script management endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_test_definition(self):
        """Create a mock test definition."""
        test_def = MagicMock(spec=TestDefinition)
        test_def.id = 1
        test_def.playwright_script = "async def run_test(page): ..."
        test_def.script_status = "draft"
        test_def.script_metadata = {}
        test_def.execution_mode = "script"
        return test_def

    async def test_get_script(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test getting script."""
        with patch('app.api.v1.endpoints.script_management.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.get(
                "/scripts/test-definitions/1/script"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["playwright_script"] == "async def run_test(page): ..."
            assert data["script_status"] == "draft"

    async def test_update_script(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test updating script."""
        with patch('app.api.v1.endpoints.script_management.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition):

            new_script = "async def run_test(page): return {'status': 'passed'}"
            response = await async_client.put(
                "/scripts/test-definitions/1/script",
                json={"playwright_script": new_script}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["playwright_script"] == new_script
            assert data["script_status"] == "draft"

    async def test_approve_script_success(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test approving script successfully."""
        mock_test_definition.script_status = "validated"

        with patch('app.api.v1.endpoints.script_management.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.post(
                "/scripts/test-definitions/1/approve-script"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["script_status"] == "approved"

    async def test_approve_script_not_validated(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test approving script that is not validated."""
        mock_test_definition.script_status = "draft"

        with patch('app.api.v1.endpoints.script_management.get_current_user', return_value=mock_user), \
             patch('app.services.script_management_service.ScriptManagementService.get_test_definition_or_404', return_value=mock_test_definition):

            response = await async_client.post(
                "/scripts/test-definitions/1/approve-script"
            )

            assert response.status_code == 400
            assert "must be validated" in response.json()["detail"].lower()

    async def test_generate_description(
        self,
        async_client: AsyncClient,
        mock_user,
        mock_test_definition
    ):
        """Test generating test description."""
        mock_test_definition.test_goal = "Test login functionality"

        with patch('app.api.v1.endpoints.script_management.get_current_user', return_value=mock_user), \
             patch('app.services.script_generation_service.ScriptGenerationService.get_test_definition_or_404', return_value=mock_test_definition), \
             patch('app.services.script_generation_service.ScriptGenerationService.generate_description') as mock_gen:

            mock_gen.return_value = "Test login with valid credentials"

            response = await async_client.post(
                "/scripts/test-definitions/1/generate-description"
            )

            assert response.status_code == 200
            data = response.json()
            assert "description" in data
            assert data["description"] == "Test login with valid credentials"
