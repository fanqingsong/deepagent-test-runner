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
from app.services import get_claude_interpreter
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
        logger.info(f"Screenshot saved: {web_path}")
        return web_path

    except Exception as e:
        logger.error(f"Failed to capture screenshot for step {step_number}: {str(e)}")
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

        # Prioritize AI-generated plan if available and approved
        if test_def.ai_generated_plan and test_def.plan_generation_status == "approved":
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
            except Exception as e:
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

    if not test_steps:
        return {
            "status": "error",
            "error": f"No test steps found for test definition {test_definition_id}",
            "run_id": run_id
        }

    # Execute test using AI interpretation
    start_time = datetime.now(timezone.utc).timestamp() * 1000  # milliseconds
    test_results = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Set default timeout
                page.set_default_timeout(settings.TEST_TIMEOUT)

                # Navigate to initial URL if provided
                if test_url:
                    try:
                        await page.goto(test_url)
                        await page.wait_for_load_state("networkidle")
                    except Exception as e:
                        return {
                            "status": "error",
                            "error": f"Failed to navigate to initial URL {test_url}: {str(e)}",
                            "run_id": run_id
                        }

                # Execute ALL steps in a single Claude Code session (matches CLI architecture)
                logger.info(
                    "Executing %d test steps in a single Claude session for run %s",
                    len(test_steps),
                    run_id,
                )
                test_results = await _execute_all_steps_with_ai(page, test_steps, environment, run_id)
                logger.info(
                    "Run %s finished: %d steps, %d passed",
                    run_id,
                    len(test_results),
                    sum(1 for r in test_results if r.get("status") == "passed"),
                )

            except Exception as e:
                test_results.append({
                    "step_number": 0,
                    "status": "error",
                    "error": str(e)
                })

            finally:
                await browser.close()

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to launch browser: {str(e)}",
            "run_id": run_id
        }

    end_time = datetime.now(timezone.utc).timestamp() * 1000  # milliseconds
    total_duration = end_time - start_time

    # Calculate summary
    passed = sum(1 for r in test_results if r["status"] == "passed")
    failed = sum(1 for r in test_results if r["status"] == "failed")
    total = len(test_results)

    result = {
        "run_id": run_id,
        "test_definition_id": test_definition_id,
        "start_time": start_time,
        "end_time": end_time,
        "total_duration": total_duration,
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "status": "passed" if failed == 0 else "failed",
        "test_cases": test_results
    }

    try:
        async def _save(db: AsyncSession) -> None:
            svc = ExecutionService(db)
            await svc.save_test_results(run_id, result)

        await run_with_session(_save)
        logger.info("Saved results for run %s with status %s", run_id, result.get("status"))
    except Exception as e:
        logger.warning("Failed to save test results for run %s: %s", run_id, e, exc_info=True)

    return result


async def _execute_all_steps_with_ai(
    page: Page,
    test_steps: List[Dict[str, Any]],
    environment: Dict[str, Any],
    run_id: str
) -> List[Dict[str, Any]]:
    """
    Execute ALL test steps in a single Claude Code session (matches CLI architecture).

    This is the NEW method that replaces the old per-step approach.

    Enhanced with screenshot capture, detailed logging, and verification.

    Args:
        page: Playwright page
        test_steps: List of test steps with natural language descriptions
        environment: Environment variables
        run_id: Test run ID for screenshot organization

    Returns:
        List of step execution results with screenshots and logs
    """
    step_start = datetime.now(timezone.utc).timestamp() * 1000

    if not test_steps:
        return []

    execution_logs = []

    try:
        # Log test execution start
        execution_logs.append(create_execution_log(
            0, "Test Batch", "start_execution",
            f"Starting {len(test_steps)} test steps", "info"
        ))

        # Use Claude AI to interpret and execute ALL steps in a single session
        context = {
            "environment": environment
        }

        results = await get_claude_interpreter().interpret_and_execute_batch(
            page,
            test_steps,
            context
        )

        # Enhance each result with screenshots and verification
        step_end = datetime.utcnow().timestamp() * 1000
        total_duration = step_end - step_start
        duration_per_step = total_duration // len(results) if results else total_duration

        for idx, result in enumerate(results):
            step_number = result.get("step_number", idx + 1)
            step_status = result.get("status", "failed")
            step_description = result.get("description", "")
            step_details = result.get("details", "")

            # Add duration if not present
            if "duration" not in result:
                result["duration"] = duration_per_step

            # Capture screenshot for this step
            try:
                screenshot_path = await capture_step_screenshot(
                    page,
                    run_id,
                    step_number,
                    step_description,
                    step_status
                )
                result["screenshot_path"] = screenshot_path
            except Exception as screenshot_error:
                logger.warning(f"Screenshot capture failed for step {step_number}: {screenshot_error}")
                result["screenshot_path"] = ""

            # Verify step result and add assertions
            try:
                verification = await verify_step_result(
                    page,
                    step_description,
                    step_details
                )
                result["verification"] = verification
                result["assertions_passed"] = verification["verification_passed"]

                # Add verification to execution log
                execution_logs.append(create_execution_log(
                    step_number,
                    step_description,
                    "verify_result",
                    f"Verification: {verification['verification_passed']}, "
                    f"Assertions: {len(verification['assertions'])}",
                    "success" if verification["verification_passed"] else "warning"
                ))
            except Exception as verify_error:
                logger.warning(f"Verification failed for step {step_number}: {verify_error}")
                result["verification"] = None
                result["assertions_passed"] = None

            # Add detailed execution log
            execution_logs.append(create_execution_log(
                step_number,
                step_description,
                "step_completed",
                f"Status: {step_status}, Details: {step_details[:200]}",
                "success" if step_status == "passed" else "error"
            ))

        # Add execution logs to the last result for storage
        if results:
            results[-1]["execution_logs"] = execution_logs

        return results

    except Exception as e:
        # Log the exception
        execution_logs.append(create_execution_log(
            0, "Test Batch", "execution_failed",
            f"Batch execution failed: {str(e)}", "error"
        ))

        # On exception, mark all steps as failed with error screenshots
        step_end = datetime.utcnow().timestamp() * 1000

        failed_results = []
        for idx, step in enumerate(test_steps):
            step_number = step.get("step_number", idx + 1)
            step_description = step.get("description", "")

            # Try to capture error screenshot
            error_screenshot = ""
            try:
                error_screenshot = await capture_step_screenshot(
                    page,
                    run_id,
                    step_number,
                    step_description,
                    "failed"
                )
            except:
                pass

            failed_results.append({
                "step_number": step_number,
                "description": step_description,
                "status": "failed",
                "error": f"Batch execution failed: {str(e)}",
                "duration": step_end - step_start,
                "screenshot_path": error_screenshot,
                "verification": None,
                "assertions_passed": False
            })

        # Add execution logs even for failed results
        if failed_results:
            failed_results[-1]["execution_logs"] = execution_logs

        return failed_results


async def _execute_step_with_ai(
    page: Page,
    step: Dict[str, Any],
    environment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a single test step using AI interpretation of natural language.

    DEPRECATED: Use _execute_all_steps_with_ai instead for better token efficiency.
    This method is kept for backward compatibility.

    Args:
        page: Playwright page
        step: Test step dict with natural language description
        environment: Environment variables

    Returns:
        dict: Step execution result
    """
    step_start = datetime.now(timezone.utc).timestamp() * 1000

    description = step.get("description", "").strip()

    if not description:
        return {
            "step_number": step.get("step_number", 0),
            "description": "Empty step description",
            "status": "failed",
            "error": "Empty step description",
            "duration": datetime.utcnow().timestamp() * 1000 - step_start
        }

    try:
        # Use Claude AI to interpret and execute the natural language step
        context = {
            "step_number": step.get("step_number", 0),
            "environment": environment
        }

        result = await get_claude_interpreter().interpret_and_execute(page, description, context)

        return {
            "step_number": step.get("step_number", 0),
            "description": description,
            "status": "passed" if result.get("success") else "failed",
            "details": result.get("details", description),
            "error": result.get("error"),
            "duration": datetime.utcnow().timestamp() * 1000 - step_start
        }

    except Exception as e:
        return {
            "step_number": step.get("step_number", 0),
            "description": description,
            "status": "failed",
            "error": str(e),
            "duration": datetime.utcnow().timestamp() * 1000 - step_start
        }