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

from app.temporal.activities import get_default_retry_policy, get_long_running_retry_policy
from app.core.langfuse_callback import langfuse_handler
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
    execution_mode: str = "nl_steps"
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
    execution_mode: str = "nl_steps"
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

        # Script mode fields
        execution_mode = getattr(test_def, "execution_mode", "nl_steps")
        playwright_script = getattr(test_def, "playwright_script", None)
        script_status = getattr(test_def, "script_status", None)

        return PrepareTestOutput(
            test_definition_id=test_definition_id_str,
            run_id=run_id,
            url=test_url,
            test_goal=test_goal,
            test_steps=test_steps,
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
    Execute browser automation using Playwright and Deep Agents framework.

    This activity delegates to the Deep Agents implementation for all test execution.

    Args:
        input: BrowserAutomationInput with all execution parameters

    Returns:
        BrowserAutomationOutput with execution results
    """
    logger.info(f"Using Deep Agents for run {input.run_id}")
    from app.temporal.activities.deepagents_activities import run_deepagents_automation
    return await run_deepagents_automation(input)


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
