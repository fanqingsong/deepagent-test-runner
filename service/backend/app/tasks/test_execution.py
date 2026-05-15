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

    try:
        run_async(lambda: _update_run_status(run_id, "running"))
    except Exception as e:
        logger.warning("Failed to set run %s to running: %s", run_id, e)

    try:
        result = run_async(
            lambda: _execute_test_async(test_definition_id, run_id, environment)
        )
        try:
            final_status = result.get("status", "failed")
            if final_status == "error":
                final_status = "failed"
            error_msg = result.get("error")
            run_async(
                lambda: _update_run_status(
                    run_id, final_status, error_message=error_msg
                )
            )
        except Exception as e:
            logger.warning("Failed to update final status for run %s: %s", run_id, e)
        return result
    except Exception:
        try:
            run_async(lambda: _update_run_status(run_id, "failed"))
        except Exception as e2:
            logger.warning("Failed to set failed status for run %s: %s", run_id, e2)
        raise


async def _update_run_status(
    run_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    async def _op(db: AsyncSession) -> None:
        svc = ExecutionService(db)
        await svc.update_run_status(run_id, status, error_message=error_message)

    await run_with_session(_op)


async def _load_test_from_db(
    test_definition_id: int,
) -> Tuple[Optional[TestDefinition], List[Dict[str, Any]]]:
    """Load test definition and steps directly from PostgreSQL."""

    async def _op(db: AsyncSession):
        def_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = def_result.scalar_one_or_none()
        if not test_def:
            return None, []

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
                test_results = await _execute_all_steps_with_ai(page, test_steps, environment)
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
    environment: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Execute ALL test steps in a single Claude Code session (matches CLI architecture).

    This is the NEW method that replaces the old per-step approach.

    Args:
        page: Playwright page
        test_steps: List of test steps with natural language descriptions
        environment: Environment variables

    Returns:
        List of step execution results
    """
    step_start = datetime.now(timezone.utc).timestamp() * 1000

    if not test_steps:
        return []

    try:
        # Use Claude AI to interpret and execute ALL steps in a single session
        context = {
            "environment": environment
        }

        results = await get_claude_interpreter().interpret_and_execute_batch(
            page,
            test_steps,
            context
        )

        # Add duration to each result
        step_end = datetime.utcnow().timestamp() * 1000
        total_duration = step_end - step_start

        # Distribute total duration evenly across steps (or could track per-step timing)
        duration_per_step = total_duration // len(results) if results else total_duration

        for result in results:
            if "duration" not in result:
                result["duration"] = duration_per_step

        return results

    except Exception as e:
        # On exception, mark all steps as failed
        step_end = datetime.utcnow().timestamp() * 1000
        return [{
            "step_number": step.get("step_number", idx + 1),
            "description": step.get("description", ""),
            "status": "failed",
            "error": f"Batch execution failed: {str(e)}",
            "duration": step_end - step_start
        } for idx, step in enumerate(test_steps)]


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


async def _interpret_and_execute(
    page: Page,
    description: str,
    environment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Interpret natural language description and execute using Playwright.

    This is a simplified rule-based interpreter. In production, this would use
    Claude Code SDK or similar AI service for true natural language understanding.

    Args:
        page: Playwright page
        description: Natural language description of the action
        environment: Environment variables

    Returns:
        dict: Execution result with success status and details
    """
    desc_lower = description.lower()

    try:
        # Navigate actions
        if "navigate" in desc_lower or "go to" in desc_lower:
            # Extract URL from description
            url = _extract_url(description)
            if url:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                return {"success": True, "details": f"Navigated to {url}"}
            else:
                return {"success": False, "error": "Could not extract URL from description"}

        # Click actions
        elif "click" in desc_lower:
            # Try to find element by text content, attribute, or common patterns
            selector = _extract_selector(description)
            if selector:
                await page.click(selector)
                await page.wait_for_load_state("networkidle")
                return {"success": True, "details": f"Clicked {selector}"}
            else:
                return {"success": False, "error": "Could not determine element to click"}

        # Fill/Type actions
        elif "enter" in desc_lower or "fill" in desc_lower or "type" in desc_lower or "input" in desc_lower:
            result = _extract_fill_details(description)
            if result:
                selector, value = result
                await page.fill(selector, value)
                return {"success": True, "details": f"Filled {selector} with '{value}'"}
            else:
                return {"success": False, "error": "Could not determine field and value for fill action"}

        # Wait actions
        elif "wait" in desc_lower:
            # Extract wait time or selector
            if "second" in desc_lower or "sec" in desc_lower:
                # Wait for specific time
                import re
                time_match = re.search(r'(\d+)\s*(?:second|sec)', desc_lower)
                if time_match:
                    wait_time = int(time_match.group(1)) * 1000
                    await page.wait_for_timeout(wait_time)
                    return {"success": True, "details": f"Waited {wait_time}ms"}

            # Wait for element
            selector = _extract_selector(description)
            if selector:
                await page.wait_for_selector(selector)
                return {"success": True, "details": f"Waited for {selector}"}

            # Default wait
            await page.wait_for_timeout(1000)
            return {"success": True, "details": "Waited 1 second"}

        # Screenshot actions
        elif "screenshot" in desc_lower:
            screenshot_dir = Path(settings.SCREENSHOT_DIR)
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            screenshot_path = screenshot_dir / f"screenshot_{timestamp}.png"

            await page.screenshot(path=str(screenshot_path))
            return {"success": True, "details": f"Screenshot saved to {screenshot_path}"}

        # Verify/Assert actions
        elif "verify" in desc_lower or "assert" in desc_lower or "check" in desc_lower:
            # Simple verification - check if page contains text or element exists
            selector = _extract_selector(description)
            if selector:
                await page.wait_for_selector(selector, timeout=5000)
                return {"success": True, "details": f"Verified {selector} exists"}
            else:
                # Check for text content
                text = _extract_text(description)
                if text:
                    await page.wait_for_selector(f"text={text}", timeout=5000)
                    return {"success": True, "details": f"Verified text '{text}' is present"}
                else:
                    return {"success": False, "error": "Could not determine what to verify"}

        # Default: try to interpret as general action
        else:
            # For now, return success with a note that this step needs AI interpretation
            return {
                "success": True,
                "details": f"AI interpretation needed for: {description}. "
                          f"Currently using placeholder - integrate Claude Code SDK for true AI execution."
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _extract_url(description: str) -> str:
    """Extract URL from natural language description."""
    import re

    # Look for http/https URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, description)
    if urls:
        return urls[0]

    # Look for domain patterns
    domain_pattern = r'(?:navigate to|go to)\s+([^\s,\.]+\.[^\s,\.]+)'
    domains = re.findall(domain_pattern, description, re.IGNORECASE)
    if domains:
        domain = domains[0]
        # Add https:// if not present
        if not domain.startswith('http'):
            domain = 'https://' + domain
        return domain

    return None


def _extract_selector(description: str) -> str:
    """Extract CSS selector from natural language description."""
    import re

    # Common button/link patterns
    if "button" in description.lower():
        # Extract button text
        button_match = re.search(r'(?:button|btn)[s]?\s+["\']?([^"\']+)["\']?', description, re.IGNORECASE)
        if button_match:
            button_text = button_match.group(1).strip()
            return f"button:has-text('{button_text}')"

    if "link" in description.lower():
        # Extract link text
        link_match = re.search(r'link\s+["\']?([^"\']+)["\']?', description, re.IGNORECASE)
        if link_match:
            link_text = link_match.group(1).strip()
            return f"a:has-text('{link_text}')"

    # Look for quoted text (could be element text)
    text_match = re.search(r'["\']([^"\']+)["\']', description)
    if text_match:
        return f"text={text_match.group(1)}"

    # Look for common selectors
    if "submit" in description.lower():
        return "button[type='submit']"
    if "login" in description.lower():
        return "button:has-text('Login'), input[type='submit']"

    return None


def _extract_fill_details(description: str) -> tuple:
    """Extract selector and value for fill actions."""
    import re

    # Pattern: "Enter <value> in/into <field>" or "Fill <field> with <value>"
    fill_patterns = [
        r'(?:enter|type|input)\s+(.+?)\s+(?:in|into)\s+(.+?)(?:\.|$)',
        r'(?:fill)\s+(.+?)\s+(?:with)\s+(.+?)(?:\.|$)',
    ]

    for pattern in fill_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            value = match.group(1).strip().strip('"\'')
            field = match.group(2).strip().strip('"\'')

            # Convert field description to selector
            if "email" in field.lower():
                return "input[type='email'], input[name*='email'], input[id*='email']", value
            elif "password" in field.lower():
                return "input[type='password']", value
            elif "username" in field.lower() or "user name" in field.lower():
                return "input[name*='user'], input[id*='user']", value
            else:
                # Try to find by placeholder or label
                return f"input[placeholder*='{field}'], input[aria-label*='{field}']", value

    return None


def _extract_text(description: str) -> str:
    """Extract text content from description."""
    import re

    # Look for quoted text
    text_match = re.search(r'["\']([^"\']+)["\']', description)
    if text_match:
        return text_match.group(1)

    # Look for "text <something>" patterns
    text_match = re.search(r'text\s+["\']?([^"\']+)["\']?', description, re.IGNORECASE)
    if text_match:
        return text_match.group(1)

    return None