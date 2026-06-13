"""
Tests for Script Management Service

Unit tests for the ScriptManagementService class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.script_management_service import ScriptManagementService
from app.models.test_definition import TestDefinition
from app.schemas.test_definition import ScriptResponse, ScriptUpdateRequest


class TestScriptManagementService:
    """Test suite for ScriptManagementService."""

    @pytest.fixture
    def db_session(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def management_service(self, db_session):
        """Create a ScriptManagementService instance."""
        return ScriptManagementService(db_session)

    @pytest.fixture
    def mock_test_definition(self):
        """Create a mock TestDefinition."""
        test_def = MagicMock(spec=TestDefinition)
        test_def.id = 1
        test_def.playwright_script = "async def run_test(page): ..."
        test_def.script_status = "draft"
        test_def.script_metadata = {}
        test_def.execution_mode = "script"
        return test_def

    @pytest.mark.asyncio
    async def test_get_test_definition_or_404_found(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test get_test_definition_or_404 when found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        result = await management_service.get_test_definition_or_404(1)

        assert result == mock_test_definition

    @pytest.mark.asyncio
    async def test_get_test_definition_or_404_not_found(
        self,
        management_service,
        db_session
    ):
        """Test get_test_definition_or_404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        result = await management_service.get_test_definition_or_404(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_script(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test getting script response."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        response = await management_service.get_script(1)

        assert isinstance(response, ScriptResponse)
        assert response.playwright_script == mock_test_definition.playwright_script
        assert response.script_status == mock_test_definition.script_status

    @pytest.mark.asyncio
    async def test_get_script_not_found(
        self,
        management_service,
        db_session
    ):
        """Test get_script with non-existent test definition."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test definition not found"):
            await management_service.get_script(999)

    @pytest.mark.asyncio
    async def test_update_script(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test updating script content."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        update_data = ScriptUpdateRequest(
            playwright_script="async def run_test(page): return {'status': 'passed'}"
        )

        response = await management_service.update_script(1, update_data)

        assert mock_test_definition.playwright_script == update_data.playwright_script
        assert mock_test_definition.script_status == "draft"
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once_with(mock_test_definition)

    @pytest.mark.asyncio
    async def test_update_script_not_found(
        self,
        management_service,
        db_session
    ):
        """Test update_script with non-existent test definition."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        update_data = ScriptUpdateRequest(playwright_script="new script")

        with pytest.raises(ValueError, match="Test definition not found"):
            await management_service.update_script(999, update_data)

    @pytest.mark.asyncio
    async def test_approve_script_success(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test approving script successfully."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.playwright_script = "script content"
        mock_test_definition.script_status = "validated"

        response = await management_service.approve_script(1)

        assert mock_test_definition.script_status == "approved"
        assert mock_test_definition.execution_mode == "script"
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once_with(mock_test_definition)

    @pytest.mark.asyncio
    async def test_approve_script_no_script(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test approve_script fails when no script exists."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.playwright_script = None
        mock_test_definition.script_status = "validated"

        with pytest.raises(ValueError, match="No script to approve"):
            await management_service.approve_script(1)

    @pytest.mark.asyncio
    async def test_approve_script_not_validated(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test approve_script fails when script is not validated."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.playwright_script = "script content"
        mock_test_definition.script_status = "draft"

        with pytest.raises(ValueError, match="Script must be validated before approval"):
            await management_service.approve_script(1)

    @pytest.mark.asyncio
    async def test_approve_script_not_found(
        self,
        management_service,
        db_session
    ):
        """Test approve_script with non-existent test definition."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test definition not found"):
            await management_service.approve_script(999)

    @pytest.mark.asyncio
    async def test_update_script_status(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test updating script status."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        metadata_updates = {"validation_error": None, "last_run": "2024-01-01"}

        response = await management_service.update_script_status(
            test_definition_id=1,
            new_status="validated",
            metadata_updates=metadata_updates
        )

        assert mock_test_definition.script_status == "validated"
        assert mock_test_definition.script_metadata["last_run"] == "2024-01-01"
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_script_status_no_metadata(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test updating script status without metadata."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        mock_test_definition.script_metadata = None

        response = await management_service.update_script_status(
            test_definition_id=1,
            new_status="draft"
        )

        assert mock_test_definition.script_status == "draft"
        # Metadata should be initialized as empty dict
        assert mock_test_definition.script_metadata == {}

    @pytest.mark.asyncio
    async def test_save_generated_script(
        self,
        management_service,
        db_session,
        mock_test_definition
    ):
        """Test saving generated script."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_test_definition
        db_session.execute.return_value = result_mock

        script = "async def run_test(page): return {'status': 'passed'}"
        metadata = {"version": "1.0", "generated_by": "ai"}

        response = await management_service.save_generated_script(
            test_definition_id=1,
            script=script,
            script_status="draft",
            script_metadata=metadata
        )

        assert mock_test_definition.playwright_script == script
        assert mock_test_definition.script_status == "draft"
        assert mock_test_definition.script_metadata == metadata
        assert mock_test_definition.execution_mode == "script"
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_generated_script_not_found(
        self,
        management_service,
        db_session
    ):
        """Test save_generated_script with non-existent test definition."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Test definition not found"):
            await management_service.save_generated_script(
                test_definition_id=999,
                script="script",
                script_status="draft"
            )
