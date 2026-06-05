"""
Deep Agents Browser Automation Activity

Temporal activity for executing tests using Deep Agents framework.
This activity provides an alternative to the LangGraph-based execution
and can be selected via the DEEPAGENTS_ENABLED feature flag.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from playwright.async_api import async_playwright, Page

from app.core.config import settings
from app.temporal.activities.test_activities import BrowserAutomationInput, BrowserAutomationOutput

logger = logging.getLogger(__name__)


@dataclass
class DeepAgentsAutomationInput:
    """Input for run_deepagents_automation activity."""

    run_id: str
    test_definition_id: str
    url: str | None
    test_goal: str | None
    test_steps: list[Dict[str, Any]]
    environment: Dict[str, Any]
    mode: str


async def execute_with_deepagents(
    input: DeepAgentsAutomationInput,
    page: Page,
) -> Dict[str, Any]:
    """Execute test using Deep Agents framework.

    Args:
        input: Execution parameters
        page: Playwright page instance

    Returns:
        Dict with execution results
    """
    from app.agents.deepagents_test_runner import (
        execute_test_run,
        set_executor_page,
    )

    run_id = input.run_id
    goal = input.test_goal
    url = input.url
    test_steps = input.test_steps
    mode = input.mode

    logger.info(f"DeepAgents: executing run {run_id} in mode {mode}")

    # Set the page for executor
    set_executor_page(page)

    # Execute test run
    result = await execute_test_run(
        goal=goal,
        url=url,
        test_steps=test_steps,
        run_id=run_id,
        mode=mode,
        page=page,
    )

    logger.info(f"DeepAgents: run {run_id} completed with status {result.get('status')}")
    return result


async def run_deepagents_automation(
    input: BrowserAutomationInput,
) -> BrowserAutomationOutput:
    """Execute browser automation using Deep Agents framework.

    This activity provides an alternative to the LangGraph-based execution.
    It uses the Deep Agents orchestrator with sub-agent delegation.

    Args:
        input: BrowserAutomationInput with all execution parameters

    Returns:
        BrowserAutomationOutput with execution results
    """
    run_id = input.run_id
    test_definition_id_str = input.test_definition_id
    test_url = input.url
    test_goal = input.test_goal
    test_steps = input.test_steps or []
    environment = input.environment or {}
    mode = input.mode or "execute_only"

    # Convert test_definition_id to int
    try:
        test_definition_id = int(test_definition_id_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid test_definition_id '{test_definition_id_str}': {e}")

    start_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    logger.info(f"DeepAgents: Starting browser automation for run {run_id} (mode={mode})")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS
            )
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
                        logger.info(f"DeepAgents: Initial navigation to {test_url} succeeded")
                    except Exception as e:
                        logger.warning(f"DeepAgents: Initial navigation failed: {e}")
                        navigated_url = page.url

                # Update environment with navigated URL
                environment["navigated_url"] = navigated_url

                # Create Deep Agents input
                deepagents_input = DeepAgentsAutomationInput(
                    run_id=run_id,
                    test_definition_id=test_definition_id,
                    url=test_url,
                    test_goal=test_goal,
                    test_steps=test_steps,
                    environment=environment,
                    mode=mode,
                )

                # Execute with Deep Agents
                result = await execute_with_deepagents(deepagents_input, page)

                logger.info(f"DeepAgents: Execution completed for run {run_id}")

            except Exception as e:
                logger.error(f"DeepAgents: Execution failed for run {run_id}: {e}")
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
        logger.error(f"DeepAgents: Failed to launch browser for run {run_id}: {e}")
        return BrowserAutomationOutput(
            run_id=run_id,
            test_definition_id=test_definition_id,
            status="error",
            test_cases=[],
            error=f"Failed to launch browser: {str(e)}",
            start_time=start_time,
            end_time=int(datetime.now(timezone.utc).timestamp() * 1000),
            total_duration=0,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
        )

    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    total_duration = end_time - start_time

    # Extract test case results
    test_cases = result.get("test_cases", [])

    # Calculate statistics
    total_tests = len(test_cases)
    passed = sum(1 for tc in test_cases if tc.get("status") == "passed")
    failed = sum(1 for tc in test_cases if tc.get("status") == "failed")
    skipped = sum(1 for tc in test_cases if tc.get("status") == "skipped")

    return BrowserAutomationOutput(
        run_id=run_id,
        test_definition_id=test_definition_id_str,
        status=result.get("status", "unknown"),
        test_cases=test_cases,
        error=result.get("error"),
        start_time=result.get("start_time", start_time),
        end_time=result.get("end_time", end_time),
        total_duration=result.get("total_duration", total_duration),
        total_tests=result.get("total_tests", total_tests),
        passed=result.get("passed", passed),
        failed=result.get("failed", failed),
        skipped=result.get("skipped", skipped),
    )
