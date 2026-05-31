"""
Unit tests for test execution activities.

These tests verify the activity implementations for the Temporal workflow,
focusing on the prepare_test and mark_run_failed activities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.temporal.activities.test_activities import (
    prepare_test,
    mark_run_failed,
    PrepareTestInput,
    MarkRunFailedInput,
)


@pytest.mark.asyncio
async def test_prepare_test_success():
    """Test prepare_test activity with valid test definition."""
    # Create mock test definition
    mock_test_def = MagicMock()
    mock_test_def.id = 123
    mock_test_def.url = "https://example.com"
    mock_test_def.test_goal = "Test login functionality"
    mock_test_def.ai_generated_plan = None
    mock_test_def.plan_generation_status = None

    # Create mock test steps
    mock_step1 = MagicMock()
    mock_step1.step_number = 1
    mock_step1.description = "Navigate to login page"
    mock_step1.type = "navigate"
    mock_step1.params = {"url": "https://example.com/login"}

    mock_step2 = MagicMock()
    mock_step2.step_number = 2
    mock_step2.description = "Enter username"
    mock_step2.type = "fill"
    mock_step2.params = {"selector": "#username", "value": "testuser"}

    # Mock database session and queries
    mock_db = AsyncMock()
    mock_result = AsyncMock()

    # Configure the execute chain for test definition query
    async def mock_execute_func(stmt):
        if "TestDefinition" in str(stmt):
            return mock_result
        # Test steps query
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_step1, mock_step2]
        return result_mock

    mock_db.execute.side_effect = mock_execute_func
    mock_result.scalar_one_or_none.return_value = mock_test_def

    # Mock run_with_session to return our prepared output
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Create input
        input_data = PrepareTestInput(
            test_definition_id="123",
            run_id="test-run-123",
            environment={"BASE_URL": "https://staging.example.com"}
        )

        # Execute the activity
        result = await prepare_test(input_data)

        # Verify the result
        assert result.test_definition_id == "123"
        assert result.run_id == "test-run-123"
        assert result.url == "https://example.com"
        assert result.test_goal == "Test login functionality"
        assert result.environment == {"BASE_URL": "https://staging.example.com"}
        assert result.mode == "execute_only"
        assert len(result.test_steps) == 2
        assert result.test_steps[0]["step_number"] == 1
        assert result.test_steps[0]["description"] == "Navigate to login page"
        assert result.test_steps[1]["step_number"] == 2
        assert result.test_steps[1]["description"] == "Enter username"


@pytest.mark.asyncio
async def test_prepare_test_not_found():
    """Test prepare_test activity with non-existent test definition."""
    # Mock database session that returns None for test definition
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None

    async def mock_execute_func(stmt):
        return mock_result

    mock_db.execute.side_effect = mock_execute_func

    # Mock run_with_session to return our prepared output
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Create input
        input_data = PrepareTestInput(
            test_definition_id="999",
            run_id="test-run-999",
            environment={}
        )

        # Execute the activity and expect ValueError
        with pytest.raises(ValueError, match="Test definition 999 not found"):
            await prepare_test(input_data)


@pytest.mark.asyncio
async def test_prepare_test_with_ai_generated_plan():
    """Test prepare_test activity prioritizes AI-generated plan."""
    import json

    # Create mock test definition with AI-generated plan
    mock_test_def = MagicMock()
    mock_test_def.id = 456
    mock_test_def.url = "https://example.com"
    mock_test_def.test_goal = "Test checkout flow"
    mock_test_def.ai_generated_plan = json.dumps({
        "steps": [
            {"description": "Add item to cart"},
            {"description": "Proceed to checkout"},
            {"description": "Complete payment"}
        ]
    })
    mock_test_def.plan_generation_status = "approved"

    # Mock database session
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_test_def

    async def mock_execute_func(stmt):
        return mock_result

    mock_db.execute.side_effect = mock_execute_func

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Create input
        input_data = PrepareTestInput(
            test_definition_id="456",
            run_id="test-run-456",
            environment={}
        )

        # Execute the activity
        result = await prepare_test(input_data)

        # Verify AI-generated steps are used
        assert result.test_definition_id == "456"
        assert len(result.test_steps) == 3
        assert result.test_steps[0]["description"] == "Add item to cart"
        assert result.test_steps[1]["description"] == "Proceed to checkout"
        assert result.test_steps[2]["description"] == "Complete payment"


@pytest.mark.asyncio
async def test_prepare_test_full_pipeline_mode():
    """Test prepare_test activity sets full_pipeline mode when no steps but has goal."""
    # Create mock test definition with goal but no steps
    mock_test_def = MagicMock()
    mock_test_def.id = 789
    mock_test_def.url = None
    mock_test_def.test_goal = "Explore and test user dashboard"
    mock_test_def.ai_generated_plan = None
    mock_test_def.plan_generation_status = None

    # Mock database session - no test steps found
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_test_def

    async def mock_execute_func(stmt):
        if "TestDefinition" in str(stmt):
            return mock_result
        # Test steps query - return empty list
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        return result_mock

    mock_db.execute.side_effect = mock_execute_func

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Create input
        input_data = PrepareTestInput(
            test_definition_id="789",
            run_id="test-run-789",
            environment={}
        )

        # Execute the activity
        result = await prepare_test(input_data)

        # Verify full_pipeline mode is set
        assert result.mode == "full_pipeline"
        assert result.test_goal == "Explore and test user dashboard"
        assert len(result.test_steps) == 0


@pytest.mark.asyncio
async def test_mark_run_failed():
    """Test mark_run_failed activity marks test run as failed."""
    # Create mock test run
    mock_test_run = MagicMock()
    mock_test_run.id = 1
    mock_test_run.run_id = "test-run-123"
    mock_test_run.status = "running"
    mock_test_run.error_message = None

    # Create mock ExecutionService
    mock_service = AsyncMock()
    mock_service.mark_run_failed.return_value = mock_test_run

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        with patch('app.temporal.activities.test_activities.ExecutionService', return_value=mock_service):
            async def mock_session_func(db_func):
                # Simulate what happens inside run_with_session
                mock_db = AsyncMock()
                return await db_func(mock_db)

            mock_run_session.side_effect = mock_session_func

            # Create input
            input_data = MarkRunFailedInput(
                run_id="test-run-123",
                error_message="Test execution failed: timeout"
            )

            # Execute the activity
            await mark_run_failed(input_data)

            # Verify ExecutionService.mark_run_failed was called
            mock_service.mark_run_failed.assert_called_once_with(
                "test-run-123",
                "Test execution failed: timeout"
            )


@pytest.mark.asyncio
async def test_mark_run_failed_no_error_message():
    """Test mark_run_failed activity works without error message."""
    # Create mock test run
    mock_test_run = MagicMock()
    mock_test_run.id = 1
    mock_test_run.run_id = "test-run-456"
    mock_test_run.status = "running"

    # Create mock ExecutionService
    mock_service = AsyncMock()
    mock_service.mark_run_failed.return_value = mock_test_run

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        with patch('app.temporal.activities.test_activities.ExecutionService', return_value=mock_service):
            async def mock_session_func(db_func):
                mock_db = AsyncMock()
                return await db_func(mock_db)

            mock_run_session.side_effect = mock_session_func

            # Create input without error message
            input_data = MarkRunFailedInput(
                run_id="test-run-456",
                error_message=None
            )

            # Execute the activity
            await mark_run_failed(input_data)

            # Verify ExecutionService.mark_run_failed was called with None
            mock_service.mark_run_failed.assert_called_once_with(
                "test-run-456",
                None
            )


@pytest.mark.asyncio
async def test_prepare_test_invalid_test_definition_id():
    """Test prepare_test activity with invalid test definition ID."""
    # Create input with invalid ID
    input_data = PrepareTestInput(
        test_definition_id="invalid",
        run_id="test-run-invalid",
        environment={}
    )

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            mock_db = AsyncMock()
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Execute the activity and expect ValueError
    with pytest.raises(ValueError, match="Invalid test_definition_id 'invalid'"):
        await prepare_test(input_data)


@pytest.mark.asyncio
async def test_prepare_test_with_empty_environment():
    """Test prepare_test activity handles empty environment correctly."""
    # Create mock test definition
    mock_test_def = MagicMock()
    mock_test_def.id = 321
    mock_test_def.url = "https://example.com"
    mock_test_def.test_goal = "Test search functionality"
    mock_test_def.ai_generated_plan = None
    mock_test_def.plan_generation_status = None

    # Mock test steps
    mock_step = MagicMock()
    mock_step.step_number = 1
    mock_step.description = "Search for products"
    mock_step.type = "fill"
    mock_step.params = {"selector": "#search", "value": "laptop"}

    # Mock database session
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_test_def

    async def mock_execute_func(stmt):
        if "TestDefinition" in str(stmt):
            return mock_result
        # Test steps query
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_step]
        return result_mock

    mock_db.execute.side_effect = mock_execute_func

    # Mock run_with_session
    with patch('app.temporal.activities.test_activities.run_with_session') as mock_run_session:
        async def mock_session_func(db_func):
            return await db_func(mock_db)

        mock_run_session.side_effect = mock_session_func

        # Create input with None environment (should default to {})
        input_data = PrepareTestInput(
            test_definition_id="321",
            run_id="test-run-321",
            environment=None
        )

        # Execute the activity
        result = await prepare_test(input_data)

        # Verify environment defaults to empty dict
        assert result.environment == {}
        assert result.test_definition_id == "321"
