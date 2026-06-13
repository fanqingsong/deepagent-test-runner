"""
Test Execution Activities with Token Integration

Enhanced Temporal activities that integrate token checking and tracking
into the test execution workflow.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.temporal.activities import get_default_retry_policy, get_long_running_retry_policy
from app.core.worker_db import run_with_session
from app.temporal.database import get_worker_session
from app.models.test_definition import TestDefinition
from app.services.execution_service import ExecutionService
from app.services.token_integration_service import TokenIntegrationService
from app.services.token_budget_service import TokenBudgetService
from app.core.result_helpers import service_success, service_error
from temporalio import activity

logger = logging.getLogger(__name__)


# Enhanced Input/Output Models with Token Information


@dataclass
class PrepareTestInput:
    """Input for prepare_test activity."""
    test_definition_id: str
    run_id: str
    environment: Dict[str, Any]
    check_tokens: bool = True  # Whether to check token availability
    scope_type: str = "test"  # Token scope type


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
    token_check_result: Optional[Dict[str, Any]] = None  # Token availability check result


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
    track_tokens: bool = True  # Whether to track token usage
    scope_type: str = "test"  # Token scope type


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
    tokens_used: Optional[int] = None  # Token usage information
    token_tracking_result: Optional[Dict[str, Any]] = None  # Token tracking details


@dataclass
class SaveResultsInput:
    """Input for save_results activity."""
    run_id: str
    results: Dict[str, Any]
    track_tokens: bool = True  # Whether to track token usage in results


@dataclass
class MarkRunFailedInput:
    """Input for mark_run_failed activity."""
    run_id: str
    error_message: Optional[str] = None
    token_error: Optional[Dict[str, Any]] = None  # Token-related error if applicable


# Activity Implementations with Token Integration


@activity.defn
async def prepare_test_with_tokens(input: PrepareTestInput) -> PrepareTestOutput:
    """
    Prepare test execution with token availability checking.

    This activity:
    1. Loads the test definition from database
    2. Checks token availability if requested
    3. Loads test steps and execution mode
    4. Returns prepared data with token check results

    Args:
        input: PrepareTestInput with test_definition_id, run_id, environment, token options

    Returns:
        PrepareTestOutput with all data needed for execution including token check result
    """
    test_definition_id_str = input.test_definition_id
    run_id = input.run_id
    environment = input.environment or {}
    scope_type = input.scope_type

    # Convert string test_definition_id to int for database operations
    try:
        test_definition_id = int(test_definition_id_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid test_definition_id '{test_definition_id_str}': {e}")

    logger.info(f"Preparing test {test_definition_id} for run {run_id}")

    token_check_result = None
    token_blocked = False

    async def _load_test_data(db: AsyncSession) -> PrepareTestOutput:
        nonlocal token_check_result, token_blocked

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

        # Check token availability if requested
        if input.check_tokens and playwright_script and script_status == "approved":
            try:
                token_service = TokenIntegrationService()

                # Estimate tokens for script execution
                # Use a rough estimate based on script length
                estimated_tokens = len(playwright_script) // 4  # Rough estimate

                check_result = await token_service.check_before_llm_call(
                    scope_type=scope_type,
                    scope_id=test_definition_id,
                    prompt=playwright_script[:1000],  # Use first 1000 chars for estimation
                    model="glm-4-plus",
                    max_tokens=4096,
                    db=db,
                    enforcement_mode="soft"
                )

                token_check_result = check_result

                if not check_result.get("allowed", True):
                    token_blocked = True
                    logger.warning(
                        f"Token budget check failed for test {test_definition_id}: "
                        f"{check_result.get('error', 'Token budget exceeded')}"
                    )

            except Exception as e:
                logger.error(f"Token check failed: {e}")
                # Continue anyway - don't block execution on check failure

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
            token_check_result=token_check_result,
        )

    result = await run_with_session(_load_test_data)

    # If tokens blocked and enforcement is hard, we should handle this
    if token_blocked:
        logger.warning(
            f"Test {test_definition_id} execution blocked due to token limits (soft enforcement, proceeding)"
        )

    return result


@activity.defn
async def run_browser_automation_with_tokens(input: BrowserAutomationInput) -> BrowserAutomationOutput:
    """
    Execute browser automation with token tracking.

    This activity:
    1. Executes Playwright script using appropriate strategy
    2. Tracks token usage if requested
    3. Returns results with token information

    Args:
        input: BrowserAutomationInput with execution parameters and token tracking options

    Returns:
        BrowserAutomationOutput with execution results and token usage information
    """
    start_time = int(datetime.utcnow().timestamp() * 1000)
    run_id = input.run_id

    from playwright.async_api import async_playwright
    from app.core.config import settings
    from app.temporal.strategies import (
        ExecutionContext,
        get_execution_strategy_factory,
    )

    token_tracking_result = None
    tokens_used = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
        playwright_context = await browser.new_context()
        page = await playwright_context.new_page()

        try:
            page.set_default_timeout(settings.TEST_TIMEOUT)

            # Create execution context
            execution_context = ExecutionContext(
                run_id=run_id,
                test_definition_id=input.test_definition_id,
                page=page,
                url=input.url,
                test_goal=input.test_goal,
                test_steps=input.test_steps,
                environment=input.environment,
                mode=input.mode,
                playwright_script=input.playwright_script,
                script_status=input.script_status,
            )

            # Get strategy factory and execute
            factory = get_execution_strategy_factory()

            logger.info(
                f"Executing test run {run_id} with execution_mode={input.execution_mode}, "
                f"script_status={input.script_status}"
            )

            result = await factory.execute_with_strategy(
                execution_mode=input.execution_mode,
                context=execution_context,
                script_status=input.script_status,
            )

            # Track token usage if requested
            if input.track_tokens:
                try:
                    # Get database session for tracking
                    async def _track_tokens(db: AsyncSession):
                        token_service = TokenIntegrationService()

                        # Estimate tokens used based on script execution
                        # In a real implementation, this would come from LLM callbacks
                        estimated_tokens = 0
                        if input.playwright_script:
                            # Rough estimate based on script complexity
                            estimated_tokens = len(input.playwright_script) // 4

                        if estimated_tokens > 0:
                            tracking_result = await token_service.track_after_llm_call(
                                scope_type=input.scope_type,
                                scope_id=int(input.test_definition_id) if input.test_definition_id.isdigit() else None,
                                tokens_used=estimated_tokens,
                                db=db,
                                metadata={
                                    "operation": "test_execution",
                                    "test_run_id": run_id,
                                    "execution_mode": input.execution_mode
                                }
                            )
                            return tracking_result
                        return None

                    token_tracking_result = await run_with_session(_track_tokens)

                except Exception as e:
                    logger.error(f"Token tracking failed: {e}")
                    # Don't fail the activity on tracking errors

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
                tokens_used=tokens_used,
                token_tracking_result=token_tracking_result,
            )

        except ValueError as strategy_error:
            # No strategy found for this execution mode
            logger.error(f"Strategy selection failed for run {run_id}: {strategy_error}")
            end_time = int(datetime.utcnow().timestamp() * 1000)
            return BrowserAutomationOutput(
                run_id=run_id,
                test_definition_id=input.test_definition_id,
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
                tokens_used=0,
                token_tracking_result=token_tracking_result,
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
                tokens_used=0,
                token_tracking_result=token_tracking_result,
            )

        finally:
            await browser.close()


@activity.defn
async def save_results_with_tokens(input: SaveResultsInput) -> None:
    """
    Save test execution results with token information to database.

    This activity:
    1. Saves test results including token usage
    2. Ensures token information is persisted for analytics

    Args:
        input: SaveResultsInput with run_id and results dict including token data
    """
    run_id = input.run_id
    results = input.results

    logger.info(f"Saving results for run {run_id}")

    async def _save(db: AsyncSession) -> None:
        svc = ExecutionService(db)

        # Add token information to results if not already present
        if input.track_tokens and "token_usage" not in results:
            # Extract token info from results if available
            token_info = {
                "tokens_used": results.get("tokens_used"),
                "token_tracking_result": results.get("token_tracking_result"),
                "timestamp": datetime.utcnow().isoformat()
            }
            results["token_usage"] = token_info

        await svc.save_test_results(run_id, results)

    await run_with_session(_save)
    logger.info(f"Saved results for run {run_id} with status {results.get('status')}")


@activity.defn
async def mark_run_failed_with_tokens(input: MarkRunFailedInput) -> None:
    """
    Mark a test run as failed in the database with token error information.

    This activity:
    1. Marks run as failed
    2. Includes token-related error information if applicable

    Args:
        input: MarkRunFailedInput with run_id and optional error/token_error
    """
    run_id = input.run_id
    error_message = input.error_message
    token_error = input.token_error

    logger.info(f"Marking run {run_id} as failed")

    async def _mark_failed(db: AsyncSession) -> None:
        svc = ExecutionService(db)

        # Combine error messages
        full_error = error_message or ""
        if token_error:
            token_msg = token_error.get("message", "Token error")
            if full_error:
                full_error += f" | Token: {token_msg}"
            else:
                full_error = token_msg

        await svc.mark_run_failed(run_id, full_error)

    await run_with_session(_mark_failed)
    logger.info(f"Marked run {run_id} as failed")


# Helper functions for workflow integration


async def check_test_execution_tokens(
    test_definition_id: int,
    run_id: str,
    db: AsyncSession,
    scope_type: str = "test"
) -> Dict[str, Any]:
    """
    Check token availability for test execution.

    Helper function for workflows to check tokens before execution.

    Args:
        test_definition_id: Test definition ID
        run_id: Test run ID
        db: Database session
        scope_type: Token scope type

    Returns:
        Token check result dictionary
    """
    try:
        token_service = TokenIntegrationService()

        # Load test definition to get script for estimation
        def_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = def_result.scalar_one_or_none()

        if not test_def:
            return {
                "allowed": True,
                "reason": "Test definition not found, skipping token check"
            }

        playwright_script = getattr(test_def, "playwright_script", None)
        if not playwright_script:
            return {
                "allowed": True,
                "reason": "No script found, skipping token check"
            }

        # Check token availability
        check_result = await token_service.check_before_llm_call(
            scope_type=scope_type,
            scope_id=test_definition_id,
            prompt=playwright_script[:1000],
            model="glm-4-plus",
            max_tokens=4096,
            db=db,
            enforcement_mode="soft"
        )

        return check_result

    except Exception as e:
        logger.error(f"Token check failed for test {test_definition_id}: {e}")
        return {
            "allowed": True,
            "reason": f"Token check failed: {str(e)}"
        }


async def track_test_execution_tokens(
    test_definition_id: int,
    run_id: str,
    execution_result: Dict[str, Any],
    db: AsyncSession,
    scope_type: str = "test"
) -> Dict[str, Any]:
    """
    Track token usage after test execution.

    Helper function for workflows to track tokens after execution.

    Args:
        test_definition_id: Test definition ID
        run_id: Test run ID
        execution_result: Execution result with token usage information
        db: Database session
        scope_type: Token scope type

    Returns:
        Token tracking result dictionary
    """
    try:
        token_service = TokenIntegrationService()

        # Extract tokens used from execution result
        tokens_used = execution_result.get("tokens_used", 0)

        if tokens_used <= 0:
            return {
                "tracked": False,
                "reason": "No token usage information available"
            }

        # Track token usage
        tracking_result = await token_service.track_after_llm_call(
            scope_type=scope_type,
            scope_id=test_definition_id,
            tokens_used=tokens_used,
            db=db,
            metadata={
                "operation": "test_execution",
                "test_run_id": run_id,
                "status": execution_result.get("status")
            }
        )

        return tracking_result

    except Exception as e:
        logger.error(f"Token tracking failed for test {test_definition_id}: {e}")
        return {
            "tracked": False,
            "error": str(e)
        }
