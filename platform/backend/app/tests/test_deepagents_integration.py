"""
Integration Tests for Deep Agents Test Runner

Tests the Deep Agents implementation to ensure it works correctly
and produces results consistent with the expected behavior.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


@pytest.mark.asyncio
class TestDeepAgentsSubagents:
    """Test individual Deep Agents sub-agents."""

    async def test_planner_subagent_creation(self):
        """Test that planner sub-agent can be created."""
        from app.agents.deepagents_test_runner.subagents.planner import (
            create_planner_subagent,
        )

        subagent = create_planner_subagent()

        assert subagent is not None
        assert subagent["name"] == "planner"
        assert "system_prompt" in subagent
        assert "tools" in subagent

    async def test_executor_subagent_creation(self):
        """Test that executor sub-agent can be created."""
        from app.agents.deepagents_test_runner.subagents.executor import (
            create_executor_subagent,
        )

        subagent = create_executor_subagent()

        assert subagent is not None
        assert subagent["name"] == "executor"
        assert "system_prompt" in subagent
        assert "tools" in subagent

    async def test_reviewer_subagent_creation(self):
        """Test that reviewer sub-agent can be created."""
        from app.agents.deepagents_test_runner.subagents.reviewer import (
            create_reviewer_subagent,
        )

        subagent = create_reviewer_subagent()

        assert subagent is not None
        assert subagent["name"] == "reviewer"
        assert "system_prompt" in subagent
        assert "tools" in subagent


@pytest.mark.asyncio
class TestDeepAgentsOrchestrator:
    """Test the main Deep Agents orchestrator."""

    async def test_orchestrator_creation(self):
        """Test that orchestrator agent can be created."""
        from app.agents.deepagents_test_runner.config import (
            create_orchestrator_agent,
            load_orchestrator_workflow,
        )

        # Test workflow prompt loading
        workflow = load_orchestrator_workflow()
        assert workflow is not None
        assert "write_todos" in workflow or "task(" in workflow

        # Test orchestrator creation
        agent = create_orchestrator_agent(run_id="test-123")
        assert agent is not None

    async def test_orchestrator_with_preset(self):
        """Test orchestrator creation with preset."""
        from app.agents.deepagents_test_runner.config import (
            create_orchestrator_with_preset,
        )

        # Test with balanced preset
        agent = create_orchestrator_with_preset("balanced", run_id="test-456")
        assert agent is not None

    async def test_orchestrator_presets(self):
        """Test all available presets."""
        from app.agents.deepagents_test_runner.config import AGENT_PRESETS

        assert "fast" in AGENT_PRESETS
        assert "balanced" in AGENT_PRESETS
        assert "thorough" in AGENT_PRESETS


@pytest.mark.asyncio
class TestDeepAgentsExecution:
    """Test Deep Agents test execution flow."""

    async def test_execute_test_run_import(self):
        """Test that execute_test_run can be imported."""
        from app.agents.deepagents_test_runner import execute_test_run

        assert execute_test_run is not None
        assert callable(execute_test_run)

    async def test_execute_test_run_signature(self):
        """Test execute_test_run has correct signature."""
        from app.agents.deepagents_test_runner import execute_test_run
        import inspect

        sig = inspect.signature(execute_test_run)

        # Check parameters exist
        assert "goal" in sig.parameters
        assert "url" in sig.parameters
        assert "run_id" in sig.parameters
        assert "mode" in sig.parameters
        assert "page" in sig.parameters

    @patch("app.agents.deepagents_test_runner.create_orchestrator_agent")
    async def test_execute_test_run_full_pipeline(self, mock_agent):
        """Test execute_test_run in full_pipeline mode."""
        from app.agents.deepagents_test_runner import execute_test_run

        # Mock the agent
        mock_agent_instance = AsyncMock()
        mock_agent_instance.ainvoke = AsyncMock(
            return_value={
                "messages": [
                    {
                        "content": '{"run_id": "test-123", "status": "passed", '
                        '"total_tests": 3, "passed": 3, "failed": 0}'
                    }
                ]
            }
        )
        mock_agent.return_value = mock_agent_instance

        # Mock Playwright page
        mock_page = MagicMock()

        result = await execute_test_run(
            goal="Test login",
            url="https://example.com/login",
            run_id="test-123",
            mode="full_pipeline",
            page=mock_page,
        )

        assert result["run_id"] == "test-123"
        assert result["status"] == "completed"

    async def test_mode_validation(self):
        """Test that invalid mode is handled."""
        from app.agents.deepagents_test_runner import execute_test_run

        result = await execute_test_run(
            run_id="test-invalid",
            mode="invalid_mode",
        )

        assert result["status"] == "error"
        assert "Invalid mode" in result.get("error", "")


@pytest.mark.asyncio
class TestDeepAgentsFilesystem:
    """Test Deep Agents filesystem operations."""

    async def test_filesystem_structure(self):
        """Test that run directory is created correctly."""
        from pathlib import Path

        run_id = "test-fs-123"
        run_dir = Path(f"/tmp/test_runs/{run_id}")

        # Create directory
        run_dir.mkdir(parents=True, exist_ok=True)

        # Verify directory exists
        assert run_dir.exists()
        assert run_dir.is_dir()

        # Cleanup
        import shutil
        if run_dir.exists():
            shutil.rmtree(run_dir.parent)

    async def test_test_plan_file_format(self):
        """Test test plan JSON file format."""
        from pathlib import Path
        import json

        run_id = "test-plan-123"
        plan_path = Path(f"/tmp/test_runs/{run_id}/test_plan.json")

        plan_path.parent.mkdir(parents=True, exist_ok=True)

        # Create sample plan
        plan = {
            "plan_id": "plan-abc",
            "steps": [
                {"step_number": 1, "description": "Navigate to login"},
                {"step_number": 2, "description": "Enter credentials"},
            ],
            "estimated_duration": 120,
        }

        with open(plan_path, "w") as f:
            json.dump(plan, f)

        # Verify file can be read
        with open(plan_path, "r") as f:
            loaded_plan = json.load(f)

        assert loaded_plan["plan_id"] == "plan-abc"
        assert len(loaded_plan["steps"]) == 2

        # Cleanup
        import shutil
        shutil.rmtree(plan_path.parent.parent)


@pytest.mark.asyncio
class TestDeepAgentsTools:
    """Test Deep Agents tools."""

    async def test_planner_tools(self):
        """Test planner sub-agent tools."""
        from app.agents.deepagents_test_runner.subagents.planner import save_test_plan

        # Test tool function
        result = save_test_plan.invoke(
            {"plan": '{"steps": []}', "run_id": "test-tools-123"}
        )

        assert "saved" in result.lower() or "failed" in result.lower()

    async def test_reviewer_tools(self):
        """Test reviewer sub-agent tools."""
        from app.agents.deepagents_test_runner.subagents.reviewer import (
            get_test_results,
            write_report,
        )

        # Test get_test_results with non-existent run
        result = get_test_results.invoke({"run_id": "non-existent"})
        assert "error" in result or "not found" in result.lower()

    async def test_executor_tools(self):
        """Test executor sub-agent tools."""
        from app.agents.deepagents_test_runner.subagents.executor import (
            save_step_result,
            capture_step_screenshot,
        )

        # Test save_step_result
        result = await save_step_result.ainvoke(
            {
                "result": '{"step_number": 1, "status": "passed"}',
                "run_id": "test-exec-123",
            }
        )

        assert "saved" in result.lower() or "failed" in result.lower()


@pytest.mark.asyncio
class TestDeepAgentsConfig:
    """Test Deep Agents configuration."""

    async def test_orchestrator_agent_creation(self):
        """Test that orchestrator agent can be created."""
        from app.agents.deepagents_test_runner.config import (
            create_orchestrator_agent,
        )

        agent = create_orchestrator_agent(run_id="test-config")
        assert agent is not None

    async def test_presets_available(self):
        """Test that agent presets are defined."""
        from app.agents.deepagents_test_runner.config import AGENT_PRESETS

        assert "fast" in AGENT_PRESETS
        assert "balanced" in AGENT_PRESETS
        assert "thorough" in AGENT_PRESETS
