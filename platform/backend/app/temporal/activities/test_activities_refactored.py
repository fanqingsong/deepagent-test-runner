"""
Refactored Test Execution Activities

Temporal activities for test execution logic using standardized interfaces.
These activities extend BaseActivity and follow the Liskov Substitution Principle.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.temporal.interfaces import (
    BaseActivity,
    ActivityInput,
    ActivityOutput,
    ActivityError,
)
from app.core.worker_db import run_with_session
from app.models.test_definition import TestDefinition
from temporalio import activity

logger = logging.getLogger(__name__)


# Input/Output Models for Activities


@dataclass
class PrepareTestInput(ActivityInput):
    """Input for prepare_test activity."""

    test_definition_id: str
    run_id: str
    environment: Dict[str, Any]


@dataclass
class PrepareTestOutput(ActivityOutput):
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
class BrowserAutomationInput(ActivityInput):
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
class BrowserAutomationOutput(ActivityOutput):
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
class SaveResultsInput(ActivityInput):
    """Input for save_results activity."""

    run_id: str
    results: Dict[str, Any]


@dataclass
class MarkRunFailedInput(ActivityInput):
    """Input for mark_run_failed activity."""

    run_id: str
    error_message: Optional[str] = None


# Activity Implementations


class PrepareTestActivity(BaseActivity[PrepareTestInput, PrepareTestOutput]):
    """
    Activity for preparing test execution.

    This activity:
    1. Loads the test definition from database
    2. Loads test steps (prioritizing AI-generated plan if available)
    3. Determines execution mode
    4. Returns prepared data for browser automation
    """

    async def validate_input(self, input_data: PrepareTestInput) -> bool:
        """Validate prepare_test input."""
        await super().validate_input(input_data)

        if not input_data.test_definition_id:
            raise ValueError("test_definition_id is required")
        if not input_data.run_id:
            raise ValueError("run_id is required")

        # Validate test_definition_id can be converted to int
        try:
            int(input_data.test_definition_id)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid test_definition_id '{input_data.test_definition_id}': {e}")

        return True

    async def execute_impl(self, input_data: PrepareTestInput) -> PrepareTestOutput:
        """Execute test preparation logic."""
        test_definition_id_str = input_data.test_definition_id
        run_id = input_data.run_id
        environment = input_data.environment or {}

        # Convert string test_definition_id to int for database operations
        test_definition_id = int(test_definition_id_str)

        self.get_logger().info(f"Preparing test {test_definition_id} for run {run_id}")

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


class BrowserAutomationActivity(BaseActivity[BrowserAutomationInput, BrowserAutomationOutput]):
    """
    Activity for executing browser automation using Playwright.

    This activity uses the ExecutionStrategyFactory to select the appropriate
    execution strategy based on execution_mode and script_status.
    """

    async def validate_input(self, input_data: BrowserAutomationInput) -> bool:
        """Validate browser automation input."""
        await super().validate_input(input_data)

        if not input_data.run_id:
            raise ValueError("run_id is required")
        if not input_data.test_definition_id:
            raise ValueError("test_definition_id is required")

        return True

    async def execute_impl(self, input_data: BrowserAutomationInput) -> BrowserAutomationOutput:
        """Execute browser automation logic."""
        from playwright.async_api import async_playwright
        from app.core.config import settings
        from app.temporal.strategies import (
            ExecutionContext,
            get_execution_strategy_factory,
        )

        start_time = int(datetime.utcnow().timestamp() * 1000)
        run_id = input_data.run_id

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            playwright_context = await browser.new_context()
            page = await playwright_context.new_page()

            try:
                page.set_default_timeout(settings.TEST_TIMEOUT)

                # Create execution context
                execution_context = ExecutionContext(
                    run_id=run_id,
                    test_definition_id=input_data.test_definition_id,
                    page=page,
                    url=input_data.url,
                    test_goal=input_data.test_goal,
                    test_steps=input_data.test_steps,
                    environment=input_data.environment,
                    mode=input_data.mode,
                    playwright_script=input_data.playwright_script,
                    script_status=input_data.script_status,
                )

                # Get strategy factory and execute
                factory = get_execution_strategy_factory()

                self.get_logger().info(
                    f"Executing test run {run_id} with execution_mode={input_data.execution_mode}, "
                    f"script_status={input_data.script_status}"
                )

                result = await factory.execute_with_strategy(
                    execution_mode=input_data.execution_mode,
                    context=execution_context,
                    script_status=input_data.script_status,
                )

                # Convert ExecutionResult to BrowserAutomationOutput
                return BrowserAutomationOutput(
                    run_id=result.run_id,
                    test_definition_id=result.test_definition_id,
                    status=result.status,
                    test_cases=result.test_cases,
                    error=result.error,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    total_duration=result.total_duration,
                    total_tests=result.total_tests,
                    passed=result.passed,
                    failed=result.failed,
                    skipped=result.skipped,
                )

            except ValueError as strategy_error:
                # No strategy found for this execution mode
                self.get_logger().error(f"Strategy selection failed for run {run_id}: {strategy_error}")
                end_time = int(datetime.utcnow().timestamp() * 1000)
                return BrowserAutomationOutput(
                    run_id=run_id,
                    test_definition_id=input_data.test_definition_id,
                    status="error",
                    test_cases=[],
                    error=str(strategy_error),
                    start_time=start_time,
                    end_time=end_time,
                    total_duration=end_time - start_time,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                )

            except Exception as e:
                self.get_logger().error(f"Browser automation failed for run {run_id}: {e}")
                end_time = int(datetime.utcnow().timestamp() * 1000)
                return BrowserAutomationOutput(
                    run_id=run_id,
                    test_definition_id=input_data.test_definition_id,
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


class SaveResultsActivity(BaseActivity[SaveResultsInput, None]):
    """
    Activity for saving test execution results to database.

    This activity wraps the ExecutionService.save_test_results method
    to persist test run results and individual test cases.
    """

    async def validate_input(self, input_data: SaveResultsInput) -> bool:
        """Validate save_results input."""
        await super().validate_input(input_data)

        if not input_data.run_id:
            raise ValueError("run_id is required")
        if not input_data.results:
            raise ValueError("results is required")

        return True

    async def execute_impl(self, input_data: SaveResultsInput) -> None:
        """Execute save results logic."""
        from app.services.execution_service import ExecutionService

        run_id = input_data.run_id
        results = input_data.results

        self.get_logger().info(f"Saving results for run {run_id}")

        async def _save(db: AsyncSession) -> None:
            svc = ExecutionService(db)
            await svc.save_test_results(run_id, results)

        await run_with_session(_save)
        self.get_logger().info(f"Saved results for run {run_id} with status {results.get('status')}")


class MarkRunFailedActivity(BaseActivity[MarkRunFailedInput, None]):
    """
    Activity for marking a test run as failed in the database.

    This activity wraps the ExecutionService.mark_run_failed method
    to handle failure scenarios.
    """

    async def validate_input(self, input_data: MarkRunFailedInput) -> bool:
        """Validate mark_run_failed input."""
        await super().validate_input(input_data)

        if not input_data.run_id:
            raise ValueError("run_id is required")

        return True

    async def execute_impl(self, input_data: MarkRunFailedInput) -> None:
        """Execute mark failed logic."""
        from app.services.execution_service import ExecutionService

        run_id = input_data.run_id
        error_message = input_data.error_message

        self.get_logger().info(f"Marking run {run_id} as failed")

        async def _mark_failed(db: AsyncSession) -> None:
            svc = ExecutionService(db)
            await svc.mark_run_failed(run_id, error_message)

        await run_with_session(_mark_failed)
        self.get_logger().info(f"Marked run {run_id} as failed")


# Temporal activity wrappers (maintaining backward compatibility)
# These wrap the new activity classes to maintain compatibility with existing workflows


@activity.defn
async def prepare_test(input: PrepareTestInput) -> PrepareTestOutput:
    """Temporal activity wrapper for PrepareTestActivity."""
    activity_instance = PrepareTestActivity()
    return await activity_instance.execute(input)


@activity.defn
async def run_browser_automation(input: BrowserAutomationInput) -> BrowserAutomationOutput:
    """Temporal activity wrapper for BrowserAutomationActivity."""
    activity_instance = BrowserAutomationActivity()
    return await activity_instance.execute(input)


@activity.defn
async def save_results(input: SaveResultsInput) -> None:
    """Temporal activity wrapper for SaveResultsActivity."""
    activity_instance = SaveResultsActivity()
    await activity_instance.execute(input)


@activity.defn
async def mark_run_failed(input: MarkRunFailedInput) -> None:
    """Temporal activity wrapper for MarkRunFailedActivity."""
    activity_instance = MarkRunFailedActivity()
    await activity_instance.execute(input)
