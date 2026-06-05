"""
Deep Agents Test Runner — Unified test execution framework.

This module provides the complete AI-powered test execution system using
the Deep Agents framework from LangChain, including:

- **Orchestrator Agent**: Main coordinator for test execution
- **Sub-Agents**: Planner, Executor, Reviewer for specialized tasks
- **Standalone Planner**: For autonomous/conversation features
- **Script Generation**: Playwright script generation and execution
- **Tools**: Browser automation and test management tools
"""

from .config import create_orchestrator_agent, create_orchestrator_with_preset
from .subagents.planner import generate_test_plan, refine_test_plan
from .subagents.executor import execute_test_batch, set_executor_page
from .subagents.reviewer import review_test_results
from .planner_agent import generate_test_plan as agent_generate_test_plan
from .script_generator import generate_playwright_script
from .script_executor import execute_script
from .page_fetcher import fetch_page_context

# Playwright browser tools
from .playwright_tools import (
    PLAYWRIGHT_TOOLS,
    set_page,
    set_screenshot_dir,
    browser_navigate,
    browser_click,
    browser_fill,
    browser_screenshot,
    browser_get_text,
    browser_get_page_content,
    browser_wait_for,
    browser_press_key,
    browser_select_option,
    browser_evaluate,
    execute_playwright_script,
)

# Test management tools
from .test_tools import save_test_plan, get_test_results

__all__ = [
    # Orchestrator
    "create_orchestrator_agent",
    "create_orchestrator_with_preset",
    "execute_test_run",
    # Subagents (internal use)
    "generate_test_plan",
    "refine_test_plan",
    "execute_test_batch",
    "set_executor_page",
    "review_test_results",
    # Standalone planner (for autonomous/conversation features)
    "agent_generate_test_plan",
    # Script generation
    "generate_playwright_script",
    "execute_script",
    "fetch_page_context",
    # Playwright tools
    "PLAYWRIGHT_TOOLS",
    "set_page",
    "set_screenshot_dir",
    "browser_navigate",
    "browser_click",
    "browser_fill",
    "browser_screenshot",
    "browser_get_text",
    "browser_get_page_content",
    "browser_wait_for",
    "browser_press_key",
    "browser_select_option",
    "browser_evaluate",
    "execute_playwright_script",
    # Test tools
    "save_test_plan",
    "get_test_results",
]


async def execute_test_run(
    goal: str | None = None,
    url: str | None = None,
    test_steps: list[dict] | None = None,
    run_id: str = "default",
    mode: str = "full_pipeline",
    page: object | None = None,
) -> dict:
    """Execute a complete test run using Deep Agents.

    This is the main entry point for test execution. It orchestrates the entire
    workflow including planning (if needed), execution, and review.

    Args:
        goal: Natural language test goal (required for planning mode)
        url: Target URL for testing
        test_steps: Pre-defined test steps (for execute_only mode)
        run_id: Unique identifier for this test run
        mode: Execution mode - 'full_pipeline', 'execute_only', 'plan_and_execute'
        page: Playwright page instance (for executor sub-agent)

    Returns:
        Dict with final execution results including status, summary, and recommendations
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    # Create run directory
    run_dir = Path(f"/tmp/test_runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)

    # Set executor page if provided
    if page:
        set_executor_page(page)

    # Build the execution prompt based on mode
    if mode == "full_pipeline" and goal:
        prompt = f"""Execute a complete test pipeline:

**Goal:** {goal}
**Target URL:** {url}
**Run ID:** {run_id}

Follow the full_pipeline workflow:
1. Use write_todos to plan the execution
2. Delegate to planner to generate test plan
3. Execute all test steps via executor
4. Delegate to reviewer for quality analysis
5. Return final status and summary"""

    elif mode == "execute_only" and test_steps:
        # Save test steps to file for executor to read
        import json
        plan_path = run_dir / "test_plan.json"
        with open(plan_path, "w") as f:
            json.dump({"steps": test_steps}, f)

        prompt = f"""Execute the predefined test steps:

**Run ID:** {run_id}
**Mode:** execute_only

Read the test steps from /test_plan.json and execute them via the executor sub-agent.
After execution, delegate to reviewer for analysis."""

    elif mode == "plan_and_execute" and goal:
        prompt = f"""Generate plan and execute:

**Goal:** {goal}
**Target URL:** {url}
**Run ID:** {run_id}

Follow the plan_and_execute workflow:
1. Delegate to planner to generate test plan
2. Execute all test steps via executor
3. Return execution status (no review)"""

    else:
        return {
            "run_id": run_id,
            "status": "error",
            "error": f"Invalid mode or missing parameters for mode '{mode}'",
        }

    try:
        # Create orchestrator agent
        agent = create_orchestrator_agent(run_id=run_id)

        # Execute the workflow
        logger.info("Starting test run %s in mode %s", run_id, mode)
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        # Extract final status from result
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "content"):
                content = msg.content
                # Try to parse final JSON result
                if "{run_id" in content or '"status"' in content:
                    try:
                        import json
                        # Find JSON in the content
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            final_result = json.loads(content[start:end])
                            final_result["run_id"] = run_id
                            logger.info("Test run %s completed with status=%s", run_id, final_result.get("status"))
                            return final_result
                    except (json.JSONDecodeError, ValueError):
                        pass

        # Fallback if JSON parsing failed
        return {
            "run_id": run_id,
            "status": "completed",
            "summary": "Test execution completed",
        }

    except Exception as e:
        logger.error("Test run %s failed: %s", run_id, e)
        return {
            "run_id": run_id,
            "status": "error",
            "error": str(e),
        }
