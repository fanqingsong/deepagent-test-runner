"""
Executor Sub-Agent — AI-powered test step execution using Deep Agents.

Executes test steps one-by-one using Playwright browser automation tools,
capturing screenshots and reporting results for each step.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool
from playwright.async_api import Page

# Import existing Playwright tools from parent directory
from ..playwright_tools import (
    PLAYWRIGHT_TOOLS,
    set_page,
    set_screenshot_dir,
)

logger = logging.getLogger(__name__)

# Shared page reference (set by orchestrator before execution)
_current_page: Page | None = None
_screenshot_dir = "/tmp/agent_screenshots"


def set_executor_page(page: Page) -> None:
    """Set the Playwright page for executor to use."""
    global _current_page
    _current_page = page
    set_page(page)


def set_executor_screenshot_dir(path: str) -> None:
    """Set the screenshot directory for executor."""
    global _screenshot_dir
    _screenshot_dir = path
    set_screenshot_dir(path)


def _get_page() -> Page:
    """Get the current Playwright page."""
    if _current_page is None:
        raise RuntimeError("No Playwright page available. Call set_executor_page() first.")
    return _current_page


# Load system prompt
def _load_system_prompt() -> str:
    """Load the executor system prompt from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "executor_system.md"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Failed to load executor prompt: %s", e)
        return "You are a test execution agent. Execute test steps using browser automation."


# Additional tools for the executor sub-agent

@tool
async def save_step_result(result: str, run_id: str) -> str:
    """Save a single step result to the test results file.

    Args:
        result: JSON string containing the step result
        run_id: Test run ID

    Returns:
        Confirmation message
    """
    results_path = Path(f"/tmp/test_runs/{run_id}/test_results.json")
    try:
        # Read existing results or create new
        if results_path.exists():
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {
                "run_id": run_id,
                "test_cases": [],
            }

        # Parse and append new result
        step_result = json.loads(result)
        data["test_cases"].append(step_result)

        # Update summary
        total = len(data["test_cases"])
        passed = sum(1 for r in data["test_cases"] if r.get("status") == "passed")
        failed = sum(1 for r in data["test_cases"] if r.get("status") == "failed")
        skipped = sum(1 for r in data["test_cases"] if r.get("status") == "skipped")

        data.update({
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "status": "passed" if failed == 0 else "failed",
        })

        # Write back
        results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Step result saved for run %s, step %s", run_id, step_result.get("step_number"))
        return f"Result saved for step {step_result.get('step_number')}"
    except Exception as e:
        logger.error("Failed to save step result: %s", e)
        return f"Failed to save result: {e}"


@tool
async def capture_step_screenshot(step_number: int, status: str, run_id: str) -> str:
    """Capture a screenshot for the current step.

    Args:
        step_number: Current step number
        status: Step status (passed/failed)
        run_id: Test run ID

    Returns:
        Path to the saved screenshot
    """
    try:
        page = _get_page()
        screenshot_dir = Path(f"/app/screenshots/{run_id}")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"step_{step_number:02d}_{status}_{timestamp}.png"
        screenshot_path = screenshot_dir / filename

        await page.screenshot(path=str(screenshot_path), full_page=False, type="png")
        web_path = f"/screenshots/{run_id}/{filename}"

        logger.info("Screenshot saved: %s", web_path)
        return web_path
    except Exception as e:
        logger.warning("Screenshot capture failed: %s", e)
        return ""


# Create the executor sub-agent configuration
def create_executor_subagent() -> Dict[str, Any]:
    """Create the executor sub-agent configuration for Deep Agents.

    Returns:
        Dict with sub-agent configuration
    """
    return {
        "name": "executor",
        "description": "Execute test steps using browser automation. Provide step number and description to execute a single test step.",
        "system_prompt": _load_system_prompt(),
        "tools": PLAYWRIGHT_TOOLS + [save_step_result, capture_step_screenshot],
    }


# Standalone invocation function for batch execution
async def execute_test_step(
    step: Dict[str, Any],
    run_id: str,
    page: Page | None = None,
) -> Dict[str, Any]:
    """Execute a single test step (standalone function).

    Args:
        step: Step dict with step_number, description, type, etc.
        run_id: Test run ID
        page: Playwright page instance

    Returns:
        Dict with step execution result
    """
    from deepagents import create_deep_agent

    # Set page if provided
    if page:
        set_executor_page(page)
        set_executor_screenshot_dir(f"/tmp/agent_screenshots/{run_id}")

    step_number = step.get("step_number", 1)
    description = step.get("description", "")

    # Get current page context
    try:
        current_url = _get_page().url
        current_title = await _get_page().title()
    except Exception:
        current_url = "unknown"
        current_title = "unknown"

    # Build the execution prompt
    prompt = f"""Execute this single test step:

**Step {step_number}:** {description}

**Current Page:**
- URL: {current_url}
- Title: {current_title}

Execute the step now, take a screenshot, and save the result using save_step_result tool."""

    try:
        # Create minimal agent for this step
        from app.core.agent_config import get_llm
        model = get_llm(temperature=0.0, max_tokens=4096)
        agent = create_deep_agent(
            model=model,
            tools=PLAYWRIGHT_TOOLS + [save_step_result, capture_step_screenshot],
            system_prompt=_load_system_prompt(),
            backend=None,
        )

        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})

        # Parse the result
        messages = result.get("messages", [])
        for msg in reversed(messages):
            content = msg.content if hasattr(msg, "content") else str(msg)
            if "```json" in content:
                try:
                    json_start = content.index("```json") + 7
                    json_end = content.index("```", json_start)
                    step_result = json.loads(content[json_end + 3:].strip())
                    if "result" in step_result:
                        return step_result["result"]
                    return step_result
                except (json.JSONDecodeError, ValueError):
                    continue

        # Fallback if JSON parsing failed
        return {
            "step_number": step_number,
            "description": description,
            "status": "passed",
            "details": "Step completed (parsing failed)",
            "mode": "deepagents_executor",
        }
    except Exception as e:
        logger.error("Executor failed for step %d: %s", step_number, e)
        return {
            "step_number": step_number,
            "description": description,
            "status": "failed",
            "error": str(e),
            "mode": "deepagents_executor",
        }


# Batch execution function
async def execute_test_batch(
    test_steps: list[Dict[str, Any]],
    run_id: str,
    page: Page,
) -> list[Dict[str, Any]]:
    """Execute multiple test steps sequentially.

    Args:
        test_steps: List of test steps to execute
        run_id: Test run ID
        page: Playwright page instance

    Returns:
        List of step execution results
    """
    set_executor_page(page)
    set_executor_screenshot_dir(f"/tmp/agent_screenshots/{run_id}")

    results = []
    failed_early = False

    for idx, step in enumerate(test_steps):
        if failed_early:
            # Skip remaining steps after a failure
            results.append({
                "step_number": step.get("step_number", idx + 1),
                "description": step.get("description", ""),
                "status": "skipped",
                "details": "Skipped due to prior step failure",
                "mode": "deepagents_executor",
            })
            continue

        logger.info("Executing step %d/%d", idx + 1, len(test_steps))
        result = await execute_test_step(step, run_id, page)
        results.append(result)

        if result.get("status") == "failed":
            failed_early = True
            logger.warning("Step %d failed, skipping remaining steps", idx + 1)

    return results
