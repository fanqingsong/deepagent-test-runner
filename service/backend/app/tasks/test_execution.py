"""
Test Execution Tasks

Celery tasks for executing AI-powered tests using natural language.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from celery import Task
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services import get_claude_interpreter, get_execution_service


def create_service_token():
    """Create a JWT token for service-to-service communication"""
    data = {
        "sub": "1",  # Admin user ID
        "username": "admin",
        "is_admin": True,
        "type": "service"
    }
    expire = timedelta(hours=24)
    to_encode = data.copy()
    expire_time = datetime.utcnow() + expire
    to_encode.update({"exp": expire_time})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


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
    # Update test run status to running
    try:
        async def update_status():
            async_engine = create_async_engine(settings.DATABASE_URL)
            async_session_maker = sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session_maker() as db:
                from app.services.execution_service import ExecutionService
                execution_service = ExecutionService(db)
                await execution_service.update_run_status(run_id, "running")
                await async_engine.dispose()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(update_status())
        finally:
            loop.close()
    except Exception as e:
        # Log but don't fail the task
        print(f"Warning: Failed to update test run status: {str(e)}")

    # Run async test execution in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_test_async(test_definition_id, run_id, environment or {})
        )

        # Update final status
        try:
            async def update_final_status():
                async_engine = create_async_engine(settings.DATABASE_URL)
                async_session_maker = sessionmaker(
                    async_engine, class_=AsyncSession, expire_on_commit=False
                )

                async with async_session_maker() as db:
                    from app.services.execution_service import ExecutionService
                    execution_service = ExecutionService(db)
                    # Map "error" status to "failed" for valid status transition
                    final_status = result.get("status", "failed")
                    if final_status == "error":
                        final_status = "failed"
                    # Extract error message if present
                    error_msg = result.get("error", "Test execution failed")
                    await execution_service.update_run_status(run_id, final_status, error_message=error_msg)
                    await async_engine.dispose()

            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            try:
                loop2.run_until_complete(update_final_status())
            finally:
                loop2.close()
        except Exception as e:
            print(f"Warning: Failed to update final test run status: {str(e)}")

        return result
    except Exception as e:
        # Update status to failed on error
        try:
            async def update_error_status():
                async_engine = create_async_engine(settings.DATABASE_URL)
                async_session_maker = sessionmaker(
                    async_engine, class_=AsyncSession, expire_on_commit=False
                )

                async with async_session_maker() as db:
                    from app.services.execution_service import ExecutionService
                    execution_service = ExecutionService(db)
                    await execution_service.update_run_status(run_id, "failed")
                    await async_engine.dispose()

            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            try:
                loop2.run_until_complete(update_error_status())
            finally:
                loop2.close()
        except Exception as e2:
            print(f"Warning: Failed to update error status: {str(e2)}")

        # Re-raise exception for Celery retry logic
        raise
    finally:
        loop.close()


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
    import httpx

    # Generate service token for API authentication
    service_token = create_service_token()
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json"
    }

    # Fetch test definition from test-case-service API
    async with httpx.AsyncClient() as client:
        try:
            # First, get all test definitions and find the one with matching ID
            response = await client.get(
                "http://backend:8001/api/v1/test-definitions/",
                headers=headers,
                timeout=10.0
            )
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to fetch test definitions: HTTP {response.status_code}",
                    "run_id": run_id
                }

            data = response.json()
            test_def_data = None
            test_url = None

            # Find the test definition with matching numeric ID
            for item in data.get("items", []):
                if item.get("id") == test_definition_id:
                    test_def_data = item
                    test_url = item.get("url")
                    break

            if not test_def_data:
                return {
                    "status": "error",
                    "error": f"Test definition with ID {test_definition_id} not found",
                    "run_id": run_id
                }

            # Fetch test steps using the numeric ID
            response = await client.get(
                f"http://backend:8001/api/v1/test-steps/test-definition/{test_definition_id}",
                headers=headers,
                timeout=10.0
            )
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to fetch test steps: HTTP {response.status_code}",
                    "run_id": run_id
                }
            test_steps_data = response.json()

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to connect to test-case-service: {str(e)}",
                "run_id": run_id
            }

    # Convert to simplified AI-friendly format
    test_steps = []
    for step_data in test_steps_data:
        # Use the description field for AI interpretation
        description = step_data.get("description", "")

        # If no description, try to construct from technical fields (backward compatibility)
        if not description:
            step_type = step_data.get("type", "unknown")
            params = step_data.get("params", {})
            description = f"{step_type}"
            if params.get("selector"):
                description += f" selector '{params['selector']}'"
            if params.get("value"):
                description += f" with value '{params['value']}'"
            if params.get("url"):
                description += f" to '{params['url']}'"

        test_steps.append({
            "step_number": step_data.get("step_number", 0),
            "description": description
        })

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
                print(f"Executing {len(test_steps)} test steps in a single Claude Code session")
                test_results = await _execute_all_steps_with_ai(page, test_steps, environment)

                print(f"Test execution completed. Total steps: {len(test_results)}, Passed: {sum(1 for r in test_results if r['status'] == 'passed')}")

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

    # Save results to database if this is a scheduled run
    # We need to use async engine for this
    print(f"Preparing to save results for run_id: {run_id}, status: {result.get('status')}")
    try:
        async_engine = create_async_engine(settings.DATABASE_URL)
        async_session_maker = sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session_maker() as db:
            # Initialize service with db session and save results
            from app.services.execution_service import ExecutionService
            execution_service = ExecutionService(db)
            print(f"Calling save_test_results for run_id: {run_id}")
            await execution_service.save_test_results(run_id, result)
            print(f"Successfully saved results for run_id: {run_id}")
            await async_engine.dispose()
    except Exception as e:
        # Log but don't fail the task if database update fails
        print(f"Warning: Failed to save test results to database: {str(e)}")
        import traceback
        traceback.print_exc()

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