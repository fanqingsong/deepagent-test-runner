"""
Planner Sub-Agent — AI-powered test plan generation using Deep Agents.

Generates structured test plans from natural language goals using
Deep Agents framework with filesystem backend.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# Load system prompt
def _load_system_prompt() -> str:
    """Load the planner system prompt from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "planner_system.md"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Failed to load planner prompt: %s", e)
        return "You are a test automation planner. Generate test plans from goals."


# Tools for the planner sub-agent

@tool
def save_test_plan(plan: str, run_id: str) -> str:
    """Save the generated test plan to the filesystem.

    Args:
        plan: The JSON plan content to save
        run_id: The test run ID for the plan

    Returns:
        Confirmation message with file path
    """
    plan_path = Path(f"/tmp/test_runs/{run_id}/test_plan.json")
    try:
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan)
        logger.info("Test plan written to %s", plan_path)
        return f"Plan saved to {plan_path}"
    except Exception as e:
        logger.error("Failed to save plan: %s", e)
        return f"Failed to save plan: {e}"


# Create the planner sub-agent configuration
def create_planner_subagent() -> Dict[str, Any]:
    """Create the planner sub-agent configuration for Deep Agents.

    Returns:
        Dict with sub-agent configuration
    """
    return {
        "name": "planner",
        "description": "Generate test plans from natural language goals. Provide the goal and target URL to get a structured test plan.",
        "system_prompt": _load_system_prompt(),
        "tools": [save_test_plan],
    }


# Standalone invocation function for testing
async def generate_test_plan(
    goal: str,
    url: str,
    run_id: str,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate a structured test plan from a natural language goal.

    This function can be used independently without the full Deep Agents orchestration.

    Args:
        goal: Natural language test goal/requirement
        url: Target URL for testing
        run_id: Test run ID for saving the plan
        context: Additional context (environment variables, etc.)

    Returns:
        Dict with plan_id, steps[], estimated_duration, risk_factors, success_criteria
    """
    from deepagents import create_deep_agent
    from app.core.agent_config import get_llm

    context = context or {}
    plan_id = str(uuid.uuid4())

    # Create a minimal agent for this specific planning task
    model = get_llm(temperature=0.3, max_tokens=4096)
    agent = create_deep_agent(
        model=model,
        tools=[save_test_plan],
        system_prompt=_load_system_prompt(),
        backend=None,  # No filesystem backend needed for standalone
    )

    # Build the planning prompt
    prompt = f"""Generate a test plan for the following requirement:

**Goal:** {goal}
**Target URL:** {url}
**Context:** {json.dumps(context, indent=2) if context else 'None'}
**Run ID:** {run_id}

Generate a comprehensive test plan and save it using the save_test_plan tool."""

    try:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        # Read the saved plan
        plan_path = f"/tmp/test_runs/{run_id}/test_plan.json"
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            # Ensure plan_id is set
            plan["plan_id"] = plan_id
            return plan
        except Exception as e:
            logger.warning("Failed to read saved plan: %s", e)
            # Return a fallback plan
            return {
                "plan_id": plan_id,
                "steps": [
                    {
                        "step_number": 1,
                        "description": f"Navigate to {url}",
                        "type": "navigation",
                        "verification": f"Page loads at {url}",
                        "confidence": 0.9,
                        "fallback_strategies": ["retry_navigation"],
                    }
                ],
                "estimated_duration": 60,
                "risk_factors": ["plan_generation_partial"],
                "success_criteria": ["test_completed"],
            }
    except Exception as e:
        logger.error("Planner agent failed: %s", e)
        return {
            "plan_id": plan_id,
            "error": str(e),
            "steps": [],
            "estimated_duration": 0,
        }


# Plan refinement function
async def refine_test_plan(
    goal: str,
    url: str,
    current_plan: Dict[str, Any],
    user_feedback: str,
    run_id: str,
    conversation_history: list[Dict[str, str]] | None = None,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Iteratively refine an existing test plan based on user feedback.

    Args:
        goal: Original test goal/requirement
        url: Target URL for testing
        current_plan: The existing plan dict with plan_id, steps[], etc.
        user_feedback: The latest user message with refinement instructions
        run_id: Test run ID for saving the refined plan
        conversation_history: List of prior conversation turns
        context: Additional context (environment variables, etc.)

    Returns:
        Dict with refined plan_id, steps[], estimated_duration, risk_factors, success_criteria
    """
    context = context or {}
    plan_id = str(uuid.uuid4())

    # Format conversation history
    history_lines = []
    for turn in conversation_history or []:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        history_lines.append(f"{role}: {content}")
    formatted_history = "\n".join(history_lines)

    # Create agent for refinement
    from app.core.agent_config import get_llm
    model = get_llm(temperature=0.3, max_tokens=4096)
    agent = create_deep_agent(
        model=model,
        tools=[save_test_plan],
        system_prompt=_load_system_prompt() + """

## Plan Refinement Mode

You are now refining an EXISTING test plan based on user feedback. Follow these guidelines:

1. Carefully review the current plan alongside the user's feedback
2. Preserve steps that the user has not objected to
3. Modify, replace, or remove steps that the user has specifically criticized
4. Add new steps only when the feedback clearly requests them
5. Update verification criteria, risk factors, and success criteria to match changes
6. If the user requests reordering, adjust step_number values accordingly
7. Explain what changed and why in a brief summary before the JSON block

Output the COMPLETE refined plan (not a diff) in the same JSON format.""",
        backend=None,
    )

    prompt = f"""Refine the existing test plan based on user feedback.

**Original Goal:** {goal}
**Target URL:** {url}
**Context:** {json.dumps(context, indent=2) if context else 'None'}

**Current Plan:**
```json
{json.dumps(current_plan, indent=2, ensure_ascii=False)}
```

**Conversation History:**
{formatted_history if formatted_history else 'No prior conversation.'}

**Latest User Feedback:**
{user_feedback}

Generate the complete refined plan and save it using the save_test_plan tool."""

    try:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        # Read the refined plan
        plan_path = f"/tmp/test_runs/{run_id}/test_plan.json"
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            plan["plan_id"] = plan_id
            return plan
        except Exception as e:
            logger.warning("Failed to read refined plan: %s", e)
            return current_plan  # Return original if refinement failed
    except Exception as e:
        logger.error("Plan refinement failed: %s", e)
        return current_plan  # Return original on error
