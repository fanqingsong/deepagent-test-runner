"""
Test Execution Tasks

Celery tasks for executing AI-powered tests using natural language.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page, async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.worker_db import run_async, run_with_session
from app.models.test_definition import TestDefinition
from app.models.test_step import TestStep
from app.agents.supervisor_graph import build_pipeline_graph
from app.services.execution_service import ExecutionService

logger = logging.getLogger(__name__)

# Screenshot directory configuration
SCREENSHOT_BASE_DIR = Path("/app/screenshots")
SCREENSHOT_BASE_DIR.mkdir(parents=True, exist_ok=True)


async def capture_step_screenshot(
    page: Page,
    run_id: str,
    step_number: int,
    description: str = "",
    status: str = "passed"
) -> str:
    """
    Capture screenshot for a test step.

    Args:
        page: Playwright page instance
        run_id: Test run ID
        step_number: Step number (can be None)
        description: Step description for filename
        status: Step status (passed/failed)

    Returns:
        str: Relative path to screenshot file
    """
    try:
        # Handle None step_number
        step_num = step_number if step_number is not None else 0

        # Create directory for this run
        run_dir = SCREENSHOT_BASE_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with step info and status
        safe_desc = description[:30].replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"step_{step_num:02d}_{status}_{safe_desc}_{timestamp}.png"
        screenshot_path = run_dir / filename

        # Take screenshot
        await page.screenshot(
            path=str(screenshot_path),
            full_page=False,  # Only capture viewport for faster performance
            type="png"
        )

        # Return relative path for web access
        web_path = f"/screenshots/{run_id}/{filename}"
        logger.info("Screenshot saved: %s", web_path)
        return web_path

    except Exception as e:
        logger.error("Failed to capture screenshot for step %s: %s", step_number, str(e))
        return ""


def create_execution_log(
    step_number: int,
    description: str,
    action: str,
    details: str = "",
    status: str = "info"
) -> Dict[str, Any]:
    """
    Create structured execution log entry.

    Args:
        step_number: Step number
        description: Step description
        action: Action performed (e.g., "navigate", "click", "fill")
        details: Additional details
        status: Log status (info, success, warning, error)

    Returns:
        dict: Structured log entry
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step_number": step_number,
        "description": description[:100],  # Truncate long descriptions
        "action": action,
        "details": details[:500],  # Limit detail length
        "status": status
    }


async def verify_step_result(
    page: Page,
    step_description: str,
    execution_details: str
) -> Dict[str, Any]:
    """
    Verify step execution result and provide detailed feedback.

    Args:
        page: Playwright page instance
        step_description: Original step description
        execution_details: Details from AI execution

    Returns:
        dict: Verification results with assertions
    """
    assertions = []

    try:
        # Get current page state
        current_url = page.url
        page_title = await page.title()

        # Basic verification assertions
        assertions.append({
            "type": "page_loaded",
            "expected": "page successfully loaded",
            "actual": f"current URL: {current_url}",
            "passed": True,
            "evidence": f"Page title: {page_title}"
        })

        # Check for common error indicators
        error_keywords = ["error", "failed", "exception", "not found", "404", "500"]
        page_content = await page.content()

        for keyword in error_keywords:
            if keyword.lower() in page_content.lower():
                assertions.append({
                    "type": "error_detection",
                    "expected": f"no '{keyword}' on page",
                    "actual": f"found '{keyword}' in page content",
                    "passed": False,
                    "evidence": f"Keyword '{keyword}' detected in page"
                })

        # Check if navigation occurred (for navigation steps)
        if "navigate" in step_description.lower() or "go to" in step_description.lower():
            target_url = execution_details
            if target_url and target_url in current_url:
                assertions.append({
                    "type": "navigation_verification",
                    "expected": f"navigate to {target_url}",
                    "actual": f"successfully navigated to {current_url}",
                    "passed": True,
                    "evidence": "URL match confirmed"
                })

        return {
            "verification_passed": all(a["passed"] for a in assertions),
            "assertions": assertions,
            "page_state": {
                "url": current_url,
                "title": page_title
            }
        }

    except Exception as e:
        return {
            "verification_passed": False,
            "assertions": [{
                "type": "verification_error",
                "expected": "successful page state verification",
                "actual": f"verification failed: {str(e)}",
                "passed": False,
                "evidence": str(e)
            }],
            "page_state": {"url": "unknown", "title": "unknown"}
        }


@celery_app.task(bind=True, name="app.tasks.test_execution.execute_test",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def execute_test(self, test_definition_id: int, run_id: str, environment: Dict[str, Any] = None):
    """
    Execute a test definition using AI-powered natural language processing.

    Args:
        test_definition_id: Test definition internal ID
        run_id: Unique run identifier
        environment: Environment variables for the test

    Returns:
        dict: Test execution results
    """
    environment = environment or {}
    return run_async(
        lambda: _run_execute_test_task(test_definition_id, run_id, environment)
    )


async def _run_execute_test_task(
    test_definition_id: int,
    run_id: str,
    environment: Dict[str, Any],
) -> Dict[str, Any]:
    """Single async entrypoint for a Celery test task (one event loop per task)."""
    await _ensure_run_running(run_id)
    try:
        result = await _execute_test_async(test_definition_id, run_id, environment)
        await _finalize_run_status(run_id, result)
        return result
    except Exception as exc:
        await _mark_run_failed(run_id, str(exc))
        raise


async def _ensure_run_running(run_id: str) -> None:
    async def _op(db: AsyncSession) -> None:
        await ExecutionService(db).ensure_run_running(run_id)

    await run_with_session(_op)


async def _finalize_run_status(run_id: str, result: Dict[str, Any]) -> None:
    status = result.get("status", "failed")
    error_msg = result.get("error")

    async def _op(db: AsyncSession) -> None:
        await ExecutionService(db).finalize_run_status_if_needed(
            run_id, status, error_message=error_msg
        )

    await run_with_session(_op)


async def _mark_run_failed(run_id: str, error_message: Optional[str] = None) -> None:
    async def _op(db: AsyncSession) -> None:
        await ExecutionService(db).mark_run_failed(run_id, error_message=error_message)

    await run_with_session(_op)


async def _load_test_from_db(
    test_definition_id: int,
) -> Tuple[Optional[TestDefinition], List[Dict[str, Any]]]:
    """Load test definition and steps directly from PostgreSQL.

    Prioritizes AI-generated plans over traditional test_steps if available.
    """

    async def _op(db: AsyncSession):
        def_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = def_result.scalar_one_or_none()
        if not test_def:
            return None, []

        # Prioritize AI-generated plan if available (approved or generated)
        if test_def.ai_generated_plan and test_def.plan_generation_status in ("approved", "generated"):
            logger.info(
                "Using AI-generated plan for test definition %d (status: %s)",
                test_definition_id,
                test_def.plan_generation_status
            )
            # Parse AI-generated plan into test_steps format
            test_steps: List[Dict[str, Any]] = []
            try:
                # Assuming ai_generated_plan is a JSON string or dict with steps
                import json
                plan_data = test_def.ai_generated_plan
                if isinstance(plan_data, str):
                    plan_data = json.loads(plan_data)

                # Extract steps from AI plan
                ai_steps = plan_data.get("steps", [])
                for idx, step in enumerate(ai_steps):
                    test_steps.append({
                        "step_number": idx + 1,
                        "description": step.get("description", ""),
                    })

                logger.info(
                    "Loaded %d steps from AI-generated plan for test definition %d",
                    len(test_steps),
                    test_definition_id
                )
                return test_def, test_steps
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
                logger.warning(
                    "Failed to parse AI-generated plan for test definition %d: %s. Falling back to traditional steps.",
                    test_definition_id,
                    str(e)
                )
                # Fall through to traditional steps below

        # Use traditional test_steps
        logger.info(
            "Using traditional test_steps for test definition %d",
            test_definition_id
        )
        steps_result = await db.execute(
            select(TestStep)
            .where(TestStep.test_definition_id == test_definition_id)
            .order_by(TestStep.step_number)
        )
        steps = steps_result.scalars().all()
        test_steps: List[Dict[str, Any]] = []
        for step in steps:
            description = (step.description or "").strip()
            if not description:
                description = step.type
                params = step.params or {}
                if params.get("selector"):
                    description += f" selector '{params['selector']}'"
                if params.get("value"):
                    description += f" with value '{params['value']}'"
                if params.get("url"):
                    description += f" to '{params['url']}'"
            test_steps.append({
                "step_number": step.step_number,
                "description": description,
            })

        logger.info(
            "Loaded %d traditional steps for test definition %d",
            len(test_steps),
            test_definition_id
        )
        return test_def, test_steps

    return await run_with_session(_op)


async def _execute_test_async(
    test_definition_id: int,
    run_id: str,
    environment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Async implementation of AI-powered test execution.

    Uses the LangGraph supervisor pipeline to orchestrate sub-agents.

    Args:
        test_definition_id: Test definition internal ID
        run_id: Unique run identifier
        environment: Environment variables

    Returns:
        dict: Test execution results
    """
    test_def, test_steps = await _load_test_from_db(test_definition_id)
    if not test_def:
        return {
            "status": "error",
            "error": f"Test definition with ID {test_definition_id} not found",
            "run_id": run_id,
        }

    test_url = test_def.url

    # Determine pipeline mode
    mode = "execute_only"
    if not test_steps and getattr(test_def, "test_goal", None):
        mode = "full_pipeline"

    if mode == "execute_only" and not test_steps:
        return {
            "status": "error",
            "error": f"No test steps found for test definition {test_definition_id}",
            "run_id": run_id
        }

    # Execute test via supervisor graph
    start_time = datetime.now(timezone.utc).timestamp() * 1000

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                page.set_default_timeout(settings.TEST_TIMEOUT)

                # Navigate to initial URL if provided
                navigated_url = None
                if test_url:
                    try:
                        await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
                        navigated_url = page.url
                        logger.info("Initial navigation to %s succeeded, final URL: %s", test_url, navigated_url)
                    except Exception as e:
                        logger.warning("Initial navigation to %s failed: %s, continuing anyway", test_url, e)
                        navigated_url = page.url

                # Build and invoke supervisor graph
                graph = build_pipeline_graph()
                initial_state = {
                    "mode": mode,
                    "goal": getattr(test_def, "test_goal", None),
                    "target_url": test_url,
                    "test_definition_id": test_definition_id,
                    "run_id": run_id,
                    "environment": {**environment, "navigated_url": navigated_url},
                    "test_steps": test_steps if test_steps else None,
                    "retry_count": 0,
                    "max_retries": 1,
                    "current_phase": "init",
                    "messages": [],
                }

                logger.info(
                    "Supervisor: invoking pipeline mode=%s for run %s (%d steps)",
                    mode, run_id, len(test_steps or []),
                )

                graph_result = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"page": page, "run_id": run_id}},
                )

                result = graph_result.get("final_result")
                if not result:
                    # Fallback: build result from state
                    result = _build_result_from_state(graph_result, test_definition_id, run_id, start_time)

                logger.info(
                    "Supervisor: run %s completed with status %s",
                    run_id, result.get("status"),
                )

            except Exception as e:
                result = {
                    "run_id": run_id,
                    "test_definition_id": test_definition_id,
                    "status": "error",
                    "error": str(e),
                    "test_cases": [],
                }

            finally:
                await browser.close()

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to launch browser: {str(e)}",
            "run_id": run_id
        }

    # Save results to database
    try:
        async def _save(db: AsyncSession) -> None:
            svc = ExecutionService(db)
            await svc.save_test_results(run_id, result)

        await run_with_session(_save)
        logger.info("Saved results for run %s with status %s", run_id, result.get("status"))
    except Exception as e:
        logger.warning("Failed to save test results for run %s: %s", run_id, e, exc_info=True)

    return result


def _build_result_from_state(
    state: Dict[str, Any],
    test_definition_id: int,
    run_id: str,
    start_time: float,
) -> Dict[str, Any]:
    """Build a result dict from supervisor state when result_builder didn't run."""
    step_results = state.get("step_results") or []
    now_ms = datetime.now(timezone.utc).timestamp() * 1000

    passed = sum(1 for r in step_results if r.get("status") == "passed")
    failed = sum(1 for r in step_results if r.get("status") == "failed")

    return {
        "run_id": run_id,
        "test_definition_id": test_definition_id,
        "start_time": start_time,
        "end_time": now_ms,
        "total_duration": now_ms - start_time,
        "total_tests": len(step_results),
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "status": "passed" if failed == 0 else "failed",
        "test_cases": step_results,
        "review": state.get("review"),
    }


