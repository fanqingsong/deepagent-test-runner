"""
Test Execution Activities

Temporal activities for test execution logic.
These activities wrap the existing execution service and agent logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.temporal.activities import get_default_retry_policy, get_long_running_retry_policy
from app.core.langfuse_callback import langfuse_handler
from app.core.worker_db import run_with_session
from app.temporal.database import get_worker_session
from app.models.test_definition import TestDefinition
from app.services.execution_service import ExecutionService
from temporalio import activity

logger = logging.getLogger(__name__)


async def get_db_session():
    """Get a database session for Temporal activities."""
    # For Temporal activities, use the worker session
    async for session in get_worker_session():
        yield session


# Input/Output Models for Activities


@dataclass
class PrepareTestInput:
    """Input for prepare_test activity."""

    test_definition_id: str
    run_id: str
    environment: Dict[str, Any]


@dataclass
class PrepareTestOutput:
    """Output from prepare_test activity."""

    test_definition_id: str
    run_id: str
    url: Optional[str]
    test_goal: Optional[str]
    test_steps: List[Dict[str, Any]]
    environment: Dict[str, Any]
    mode: str
    execution_mode: str = "script"
    playwright_script: Optional[str] = None
    script_status: Optional[str] = None


@dataclass
class BrowserAutomationInput:
    """Input for run_browser_automation activity."""

    run_id: str
    test_definition_id: str
    url: Optional[str]
    test_goal: Optional[str]
    test_steps: List[Dict[str, Any]]
    environment: Dict[str, Any]
    mode: str
    execution_mode: str = "script"
    playwright_script: Optional[str] = None
    script_status: Optional[str] = None


@dataclass
class BrowserAutomationOutput:
    """Output from run_browser_automation activity."""

    run_id: str
    test_definition_id: str
    status: str
    test_cases: List[Dict[str, Any]]
    error: Optional[str]
    start_time: int
    end_time: int
    total_duration: int
    total_tests: int
    passed: int
    failed: int
    skipped: int


@dataclass
class SaveResultsInput:
    """Input for save_results activity."""

    run_id: str
    results: Dict[str, Any]


@dataclass
class MarkRunFailedInput:
    """Input for mark_run_failed activity."""

    run_id: str
    error_message: Optional[str]


# Activity Implementations


@activity.defn
async def prepare_test(input: PrepareTestInput) -> PrepareTestOutput:
    """
    Prepare test execution by loading test definition and steps from database.

    This activity:
    1. Loads the test definition from database
    2. Loads test steps (prioritizing AI-generated plan if available)
    3. Determines execution mode
    4. Returns prepared data for browser automation

    Args:
        input: PrepareTestInput with test_definition_id, run_id, environment

    Returns:
        PrepareTestOutput with all data needed for execution
    """
    test_definition_id_str = input.test_definition_id
    run_id = input.run_id
    environment = input.environment or {}

    # Convert string test_definition_id to int for database operations
    try:
        test_definition_id = int(test_definition_id_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid test_definition_id '{test_definition_id_str}': {e}")

    logger.info(f"Preparing test {test_definition_id} for run {run_id}")

    async def _load_test_data(db: AsyncSession) -> PrepareTestOutput:
        # Load test definition
        def_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = def_result.scalar_one_or_none()

        if not test_def:
            raise ValueError(f"Test definition {test_definition_id} not found")

        test_url = test_def.url
        test_goal = getattr(test_def, "test_goal", None)

        mode = "execute_only"
        execution_mode = getattr(test_def, "execution_mode", "script")
        playwright_script = getattr(test_def, "playwright_script", None)
        script_status = getattr(test_def, "script_status", None)

        return PrepareTestOutput(
            test_definition_id=test_definition_id_str,
            run_id=run_id,
            url=test_url,
            test_goal=test_goal,
            test_steps=[],
            environment=environment,
            mode=mode,
            execution_mode=execution_mode,
            playwright_script=playwright_script,
            script_status=script_status,
        )

    return await run_with_session(_load_test_data)


@activity.defn
async def run_browser_automation(input: BrowserAutomationInput) -> BrowserAutomationOutput:
    """
    Execute browser automation using Playwright.

    Args:
        input: BrowserAutomationInput with all execution parameters

    Returns:
        BrowserAutomationOutput with execution results
    """
    start_time = int(datetime.utcnow().timestamp() * 1000)
    run_id = input.run_id

    from playwright.async_api import async_playwright
    from app.core.config import settings

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            page.set_default_timeout(settings.TEST_TIMEOUT)

            if input.url:
                await page.goto(input.url, wait_until="domcontentloaded", timeout=30000)

            if input.execution_mode == "script" and input.playwright_script and input.script_status == "approved":
                from app.agents.deepagents_test_runner.lib import execute_script
                exec_result = await execute_script(input.playwright_script, page, timeout=120)

                end_time = int(datetime.utcnow().timestamp() * 1000)
                return BrowserAutomationOutput(
                    run_id=run_id,
                    test_definition_id=input.test_definition_id,
                    status=exec_result.get("status", "failed"),
                    test_cases=exec_result.get("step_results", []),
                    error=exec_result.get("error"),
                    start_time=start_time,
                    end_time=end_time,
                    total_duration=end_time - start_time,
                    total_tests=1,
                    passed=1 if exec_result.get("status") == "passed" else 0,
                    failed=1 if exec_result.get("status") != "passed" else 0,
                    skipped=0,
                )

            end_time = int(datetime.utcnow().timestamp() * 1000)
            return BrowserAutomationOutput(
                run_id=run_id,
                test_definition_id=input.test_definition_id,
                status="error",
                test_cases=[],
                error="No approved script found for execution",
                start_time=start_time,
                end_time=end_time,
                total_duration=end_time - start_time,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
            )

        except Exception as e:
            logger.error(f"Browser automation failed for run {run_id}: {e}")
            end_time = int(datetime.utcnow().timestamp() * 1000)
            return BrowserAutomationOutput(
                run_id=run_id,
                test_definition_id=input.test_definition_id,
                status="error",
                test_cases=[],
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                total_duration=end_time - start_time,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
            )
        finally:
            await browser.close()


@activity.defn
async def save_results(input: SaveResultsInput) -> None:
    """
    Save test execution results to database.

    This activity wraps the ExecutionService.save_test_results method
    to persist test run results and individual test cases.

    Args:
        input: SaveResultsInput with run_id and results dict
    """
    run_id = input.run_id
    results = input.results

    logger.info(f"Saving results for run {run_id}")

    async def _save(db: AsyncSession) -> None:
        svc = ExecutionService(db)
        await svc.save_test_results(run_id, results)

    await run_with_session(_save)
    logger.info(f"Saved results for run {run_id} with status {results.get('status')}")


@activity.defn
async def mark_run_failed(input: MarkRunFailedInput) -> None:
    """
    Mark a test run as failed in the database.

    This activity wraps the ExecutionService.mark_run_failed method
    to handle failure scenarios.

    Args:
        input: MarkRunFailedInput with run_id and optional error_message
    """
    run_id = input.run_id
    error_message = input.error_message

    logger.info(f"Marking run {run_id} as failed")

    async def _mark_failed(db: AsyncSession) -> None:
        svc = ExecutionService(db)
        await svc.mark_run_failed(run_id, error_message)

    await run_with_session(_mark_failed)
    logger.info(f"Marked run {run_id} as failed")
