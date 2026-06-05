"""
Configuration for Deep Agents Test Runner.

Defines the main orchestrator agent with all sub-agents and configurations.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from .tools import read_file, write_file, read_json, write_json

logger = logging.getLogger(__name__)

# Import sub-agent configurations
from .subagents.planner import create_planner_subagent
from .subagents.executor import create_executor_subagent
from .subagents.reviewer import create_reviewer_subagent


def load_orchestrator_workflow() -> str:
    """Load the orchestrator workflow prompt."""
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator_workflow.md"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Failed to load orchestrator workflow: %s", e)
        return "You are a test execution orchestrator. Coordinate planning, execution, and review."


def create_orchestrator_agent(
    model: str | None = None,
    run_id: str | None = None,
) -> Any:
    """Create the main orchestrator agent with all sub-agents.

    Args:
        model: Optional model override (uses global LLM config if not specified)
        run_id: Optional run ID for filesystem backend

    Returns:
        Configured Deep Agents orchestrator instance
    """
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from app.core.agent_config import get_llm

    # Use global LLM config if model not specified
    llm = get_llm(temperature=0.0, max_tokens=8192)

    # Configure filesystem backend
    backend = None
    if run_id:
        backend = FilesystemBackend(root_dir=f"/tmp/test_runs/{run_id}")

    # Create orchestrator with all sub-agents
    agent = create_deep_agent(
        model=llm,
        tools=[read_file, write_file],  # Built-in filesystem tools
        system_prompt=load_orchestrator_workflow(),
        subagents=[
            create_planner_subagent(),
            create_executor_subagent(),
            create_reviewer_subagent(),
        ],
        backend=backend,
    )

    logger.info("Orchestrator agent created with run_id=%s", run_id)
    return agent


# Agent configuration presets for different execution scenarios
AGENT_PRESETS: Dict[str, Dict[str, Any]] = {
    "fast": {
        "description": "Fast execution for simple tests",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "balanced": {
        "description": "Balanced speed and quality",
        "temperature": 0.5,
        "max_tokens": 6144,
    },
    "thorough": {
        "description": "Thorough analysis with more detail",
        "temperature": 0.7,
        "max_tokens": 8192,
    },
}


def create_orchestrator_with_preset(
    preset: str = "balanced",
    run_id: str | None = None,
) -> Any:
    """Create orchestrator agent using a preset configuration.

    Args:
        preset: Preset name ('fast', 'balanced', 'thorough')
        run_id: Optional run ID for filesystem backend

    Returns:
        Configured Deep Agents orchestrator instance
    """
    from app.core.agent_config import get_llm
    from deepagents.backends import FilesystemBackend

    if preset not in AGENT_PRESETS:
        logger.warning("Unknown preset '%s', using 'balanced'", preset)
        preset = "balanced"

    config = AGENT_PRESETS[preset]
    llm = get_llm(
        temperature=config.get("temperature", 0.5),
        max_tokens=config.get("max_tokens", 6144),
    )

    # Configure filesystem backend
    backend = None
    if run_id:
        backend = FilesystemBackend(root_dir=f"/tmp/test_runs/{run_id}")

    from deepagents import create_deep_agent
    agent = create_deep_agent(
        model=llm,
        tools=[read_file, write_file],
        system_prompt=load_orchestrator_workflow(),
        subagents=[
            create_planner_subagent(),
            create_executor_subagent(),
            create_reviewer_subagent(),
        ],
        backend=backend,
    )

    logger.info("Orchestrator agent created with preset=%s, run_id=%s", preset, run_id)
    return agent
