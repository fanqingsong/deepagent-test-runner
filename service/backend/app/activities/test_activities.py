"""
Test Execution Activities

Temporal activities for test execution logic.
These activities wrap the existing execution service and agent logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.activities import get_default_retry_policy, get_long_running_retry_policy
from app.agents.test_runner.executor_agent import interpret_and_execute_batch
from app.core.worker_db import run_with_session
from app.temporal.database import get_worker_session
from app.models.test_definition import TestDefinition
from app.models.test_step import TestStep
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
    3. Determines execution mode (execute_only vs full_pipeline)
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

        # Prioritize AI-generated plan if available
        test_steps: List[Dict[str, Any]] = []

        if test_def.ai_generated_plan and test_def.plan_generation_status in ("approved", "generated"):
            logger.info(
                f"Using AI-generated plan for test {test_definition_id} (status: {test_def.plan_generation_status})"
            )
            try:
                import json

                plan_data = test_def.ai_generated_plan
                if isinstance(plan_data, str):
                    plan_data = json.loads(plan_data)

                ai_steps = plan_data.get("steps", [])
                for idx, step in enumerate(ai_steps):
                    test_steps.append({
                        "step_number": idx + 1,
                        "description": step.get("description", ""),
                    })

                logger.info(f"Loaded {len(test_steps)} steps from AI-generated plan")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse AI-generated plan: {e}. Falling back to traditional steps.")
                test_steps = []

        # Fall back to traditional test_steps if no AI plan
        if not test_steps:
            logger.info(f"Using traditional test_steps for test {test_definition_id}")
            steps_result = await db.execute(
                select(TestStep)
                .where(TestStep.test_definition_id == test_definition_id)
                .order_by(TestStep.step_number)
            )
            steps = steps_result.scalars().all()

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

            logger.info(f"Loaded {len(test_steps)} traditional steps")

        # Determine execution mode
        mode = "execute_only"
        if not test_steps and test_goal:
            mode = "full_pipeline"

        return PrepareTestOutput(
            test_definition_id=test_definition_id_str,  # Return string version
            run_id=run_id,
            url=test_url,
            test_goal=test_goal,
            test_steps=test_steps,
            environment=environment,
            mode=mode,
        )

    return await run_with_session(_load_test_data)


@activity.defn
async def run_browser_automation(input: BrowserAutomationInput) -> BrowserAutomationOutput:
    """
    Execute browser automation using Playwright and LangGraph agents.

    This activity:
    1. Launches Playwright browser
    2. Navigates to initial URL if provided
    3. Executes test steps via executor agent (or full pipeline if needed)
    4. Captures screenshots and results
    5. Returns execution results

    Args:
        input: BrowserAutomationInput with all execution parameters

    Returns:
        BrowserAutomationOutput with execution results
    """
    from playwright.async_api import async_playwright

    from app.core.config import settings
    from app.agents.test_runner.supervisor_graph import build_pipeline_graph

    run_id = input.run_id
    test_definition_id_str = input.test_definition_id
    test_url = input.url
    test_goal = input.test_goal
    test_steps = input.test_steps
    environment = input.environment or {}
    mode = input.mode

    # Convert string test_definition_id to int for database operations
    try:
        test_definition_id = int(test_definition_id_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid test_definition_id '{test_definition_id_str}': {e}")

    logger.info(f"Starting browser automation for run {run_id} (mode={mode})")

    start_time = int(datetime.now(timezone.utc).timestamp() * 1000)

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
                        logger.info(f"Initial navigation to {test_url} succeeded, final URL: {navigated_url}")
                    except Exception as e:
                        logger.warning(f"Initial navigation to {test_url} failed: {e}, continuing anyway")
                        navigated_url = page.url

                # Build and invoke supervisor graph
                graph = build_pipeline_graph()
                initial_state = {
                    "mode": mode,
                    "goal": test_goal,
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
                    f"Supervisor: invoking pipeline mode={mode} for run {run_id} ({len(test_steps or [])} steps)"
                )

                graph_result = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"page": page, "run_id": run_id}},
                )

                result = graph_result.get("final_result")
                if not result:
                    raise ValueError("Graph execution completed but no final_result was produced")

                logger.info(f"Supervisor: run {run_id} completed with status {result.get('status')}")

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
        logger.error(f"Failed to launch browser for run {run_id}: {e}")
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
        test_definition_id=test_definition_id_str,  # Return string version
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
