"""
Graph Nodes — node functions for the LangGraph supervisor pipeline.

Each node is an async function that reads from SupervisorState, calls a
sub-agent (planner/executor/reviewer), and returns a state update dict.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from app.agents.test_runner.planner_agent import generate_test_plan
from app.agents.test_runner.executor_agent import interpret_and_execute_batch
from app.agents.test_runner.reviewer_agent import review_test_results
from app.agents.test_runner.supervisor_state import SupervisorState
from app.agents.test_runner.playwright_tools import set_page, set_screenshot_dir
from app.agents.test_runner.page_fetcher import fetch_page_context
from app.agents.test_runner.script_generator import generate_playwright_script
from app.agents.test_runner.script_executor import execute_script

logger = logging.getLogger(__name__)

# Screenshot base directory (same as test_execution.py)
SCREENSHOT_BASE_DIR = Path("/app/screenshots")


async def _capture_step_screenshot(page, run_id, step_number, description="", status="passed"):
    """Capture screenshot for a test step."""
    try:
        step_num = step_number if step_number is not None else 0
        run_dir = SCREENSHOT_BASE_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        safe_desc = description[:30].replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"step_{step_num:02d}_{status}_{safe_desc}_{timestamp}.png"
        screenshot_path = run_dir / filename
        await page.screenshot(path=str(screenshot_path), full_page=False, type="png")
        web_path = f"/screenshots/{run_id}/{filename}"
        return web_path
    except Exception as e:
        logger.warning("Screenshot capture failed for step %s: %s", step_number, e)
        return ""


async def planner_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate a test plan from the goal and target URL."""
    goal = state.get("goal", "")
    target_url = state.get("target_url", "")
    environment = state.get("environment", {})

    logger.info("Supervisor: planner_node starting for goal: %s", goal[:100])

    try:
        plan = await generate_test_plan(
            goal=goal,
            url=target_url,
            context=environment,
        )
        test_steps = plan.get("steps", [])

        logger.info(
            "Supervisor: planner_node generated %d steps", len(test_steps)
        )

        return {
            "plan": plan,
            "test_steps": test_steps,
            "plan_error": None,
            "current_phase": "executing",
        }
    except Exception as e:
        logger.error("Supervisor: planner_node failed: %s", e, exc_info=True)
        return {
            "plan": None,
            "plan_error": str(e),
            "current_phase": "error",
            "failed_phase": "planner_node",
        }


async def executor_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Execute test steps using the Playwright browser automation agent."""
    test_steps = state.get("test_steps") or []
    run_id = state.get("run_id", "default")
    environment = state.get("environment", {})

    # Get Playwright page from config (set by Temporal activity)
    configurable = config.get("configurable", {})
    page = configurable.get("page")

    if not page:
        return {
            "step_results": [],
            "execution_error": "No Playwright page provided via config",
            "current_phase": "error",
            "failed_phase": "executor_node",
        }

    if not test_steps:
        return {
            "step_results": [],
            "execution_error": "No test steps to execute",
            "current_phase": "error",
            "failed_phase": "executor_node",
        }

    logger.info(
        "Supervisor: executor_node starting %d steps for run %s",
        len(test_steps),
        run_id,
    )

    try:
        set_page(page)
        set_screenshot_dir(f"/tmp/agent_screenshots/{run_id}")

        context = dict(environment)
        try:
            context.setdefault("url", page.url)
            context.setdefault("title", await page.title())
        except Exception:
            context.setdefault("url", "unknown")
            context.setdefault("title", "unknown")
        context["run_id"] = run_id

        step_results = await interpret_and_execute_batch(
            page=page,
            test_steps=test_steps,
            context=context,
        )

        # Screenshots are now captured per-step inside the executor agent
        for idx, result in enumerate(step_results):
            if "duration" not in result or not result["duration"]:
                result["duration"] = 0
            if "screenshot_path" not in result or not result["screenshot_path"]:
                step_number = result.get("step_number", idx + 1)
                step_status = result.get("status", "failed")
                step_description = result.get("description", "")
                result["screenshot_path"] = await _capture_step_screenshot(
                    page, run_id, step_number, step_description, step_status
                )

        passed = sum(1 for r in step_results if r.get("status") == "passed")
        logger.info(
            "Supervisor: executor_node completed %d steps, %d passed",
            len(step_results),
            passed,
        )

        return {
            "step_results": step_results,
            "execution_error": None,
            "current_phase": "reviewing",
        }
    except Exception as e:
        logger.error(
            "Supervisor: executor_node failed: %s", e, exc_info=True
        )
        return {
            "step_results": [],
            "execution_error": str(e),
            "current_phase": "error",
            "failed_phase": "executor_node",
        }


async def reviewer_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Analyze test results and generate a quality report."""
    run_id = state.get("run_id", "")
    step_results = state.get("step_results")

    logger.info("Supervisor: reviewer_node starting for run %s", run_id)

    try:
        review = await review_test_results(
            run_id=run_id,
            test_results=step_results,
        )

        quality_score = review.get("summary", {}).get("quality_score", "N/A")
        logger.info(
            "Supervisor: reviewer_node completed, quality_score=%s",
            quality_score,
        )

        return {
            "review": review,
            "review_error": None,
            "current_phase": "done",
        }
    except Exception as e:
        # Reviewer failure is non-fatal
        logger.warning("Supervisor: reviewer_node failed (non-fatal): %s", e)
        return {
            "review": None,
            "review_error": str(e),
            "current_phase": "done",
        }


async def error_handler_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Handle errors — log and prepare for result building."""
    phase = state.get("current_phase", "error")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    plan_error = state.get("plan_error")
    execution_error = state.get("execution_error")

    error_msg = plan_error or execution_error or "Unknown error"
    logger.error(
        "Supervisor: error_handler_node phase=%s retry=%d/%d error=%s",
        phase,
        retry_count,
        max_retries,
        error_msg,
    )

    if retry_count < max_retries:
        return {
            "retry_count": retry_count + 1,
            "plan_error": None,
            "execution_error": None,
            "current_phase": "retrying",
            "failed_phase": state.get("failed_phase"),
        }

    return {
        "current_phase": "error",
        "failed_phase": None,
    }


async def result_builder_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Build the final result dict from state for DB storage."""
    step_results = state.get("step_results") or []
    run_id = state.get("run_id", "")
    test_definition_id = state.get("test_definition_id")
    review = state.get("review")
    plan_error = state.get("plan_error")
    execution_error = state.get("execution_error")

    now_ms = datetime.now(timezone.utc).timestamp() * 1000

    # If there was a critical error with no results
    if not step_results and (plan_error or execution_error):
        error_msg = execution_error or plan_error or "Unknown error"
        final_result = {
            "run_id": run_id,
            "test_definition_id": test_definition_id,
            "start_time": now_ms,
            "end_time": now_ms,
            "total_duration": 0,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "status": "error",
            "error": error_msg,
            "test_cases": [],
            "review": review,
        }
        return {"final_result": final_result, "current_phase": "done"}

    # Build result from step_results
    passed = sum(1 for r in step_results if r.get("status") == "passed")
    failed = sum(1 for r in step_results if r.get("status") == "failed")
    skipped = sum(1 for r in step_results if r.get("status") == "skipped")
    total = len(step_results)

    total_duration = sum(r.get("duration", 0) for r in step_results)

    final_result = {
        "run_id": run_id,
        "test_definition_id": test_definition_id,
        "start_time": now_ms - total_duration if total_duration else now_ms,
        "end_time": now_ms,
        "total_duration": total_duration,
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "status": (
            "passed"
            if failed == 0 and not plan_error and not execution_error
            else "failed"
        ),
        "test_cases": step_results,
        "review": review,
    }

    logger.info(
        "Supervisor: result_builder_node status=%s passed=%d failed=%d",
        final_result["status"],
        passed,
        failed,
    )

    return {"final_result": final_result, "current_phase": "done"}


# --- Script generation pipeline nodes ---


async def page_fetcher_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Fetch target page DOM for script generation context."""
    target_url = state.get("target_url", "")
    run_id = state.get("run_id", "script-gen")

    configurable = config.get("configurable", {})
    page = configurable.get("page")

    if not page or not target_url:
        return {
            "page_context": None,
            "script_status": "failed",
            "script_error": "No page or target URL for page fetching",
        }

    logger.info("Supervisor: page_fetcher_node fetching %s", target_url)

    try:
        page_context = await fetch_page_context(page, target_url)
        return {
            "page_context": page_context,
            "script_status": "generating",
            "script_error": None,
        }
    except Exception as e:
        logger.error("Supervisor: page_fetcher_node failed: %s", e)
        return {
            "page_context": None,
            "script_status": "failed",
            "script_error": f"Page fetch failed: {e}",
        }


async def script_generator_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Generate or fix a Playwright script via LLM."""
    goal = state.get("goal", "")
    target_url = state.get("target_url", "")
    page_context_data = state.get("page_context") or {}
    page_context_text = page_context_data.get("context_text", "")
    script_error = state.get("script_error")
    previous_script = state.get("playwright_script")
    attempt = state.get("script_attempt", 0)
    run_id = state.get("run_id", "script-gen")

    logger.info("Supervisor: script_generator_node attempt=%d", attempt + 1)

    try:
        result = await generate_playwright_script(
            goal=goal,
            url=target_url,
            page_context=page_context_text,
            previous_error=script_error,
            previous_script=previous_script,
            run_id=run_id,
        )

        script = result.get("script")
        error = result.get("error")

        if not script:
            return {
                "playwright_script": None,
                "script_status": "failed",
                "script_error": error,
            }

        return {
            "playwright_script": script,
            "script_status": "validating",
            "script_error": None,
            "script_attempt": attempt + 1,
        }
    except Exception as e:
        logger.error("Supervisor: script_generator_node failed: %s", e)
        return {
            "playwright_script": None,
            "script_status": "failed",
            "script_error": str(e),
        }


async def script_executor_node(
    state: SupervisorState, config: RunnableConfig
) -> Dict[str, Any]:
    """Execute the generated Playwright script."""
    script = state.get("playwright_script")
    run_id = state.get("run_id", "script-gen")

    configurable = config.get("configurable", {})
    page = configurable.get("page")

    if not script or not page:
        return {
            "step_results": [],
            "execution_error": "No script or page available",
            "script_status": "failed",
        }

    logger.info("Supervisor: script_executor_node running script (%d chars)", len(script))

    try:
        result = await execute_script(script, page, timeout=60)
        status = result.get("status", "failed")
        error = result.get("error")
        step_results = result.get("step_results", [])

        if not step_results and status == "passed":
            step_results = [{"step_number": 1, "description": "Script execution", "status": "passed"}]
        elif not step_results and error:
            step_results = [{"step_number": 1, "description": "Script execution", "status": "failed", "error": error}]

        try:
            screenshot_path = await _capture_step_screenshot(
                page, run_id, 1, "script_result", status
            )
            for sr in step_results:
                if not sr.get("screenshot_path"):
                    sr["screenshot_path"] = screenshot_path
        except Exception:
            pass

        return {
            "step_results": step_results,
            "execution_error": error if status != "passed" else None,
            "script_status": "validated" if status == "passed" else "failed",
            "script_error": error if status != "passed" else None,
        }
    except Exception as e:
        logger.error("Supervisor: script_executor_node failed: %s", e)
        return {
            "step_results": [],
            "execution_error": str(e),
            "script_status": "failed",
            "script_error": str(e),
        }
