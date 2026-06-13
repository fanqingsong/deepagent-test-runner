"""
Execution Service with Token Integration

Enhanced execution service that integrates token checking and tracking
into test execution workflows.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.test_definition import TestDefinition
from app.core.simple_result_types import (
    service_success, service_error, service_not_found,
    service_validation_error, ServiceSuccess, ServiceError
)
from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.services.token_integration_service import TokenIntegrationService
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.core.metrics.metrics_decorators import track_timing, track_metrics, track_errors

logger = logging.getLogger(__name__)


class ExecutionServiceWithTokens:
    """
    Enhanced execution service with token management integration.

    This service extends the base ExecutionService with:
    - Token availability checking before execution
    - Token usage tracking after execution
    - Token-aware error handling
    - Token metadata in test results

    Responsibilities:
    - All base ExecutionService responsibilities
    - Token checking before test execution
    - Token tracking during execution
    - Token error handling and reporting
    """

    def __init__(
        self,
        db_session=None,
        schedule_resolver: Optional[ScheduleResolver] = None,
        status_manager: Optional[RunStatusManager] = None,
        result_persister: Optional[ResultPersister] = None,
        test_run_repository: Optional[ITestRunRepository] = None,
        token_service: Optional[TokenIntegrationService] = None
    ):
        """
        Initialize Execution Service with Token Integration.

        Args:
            db_session: Async database session
            schedule_resolver: Optional ScheduleResolver instance
            status_manager: Optional RunStatusManager instance
            result_persister: Optional ResultPersister instance
            test_run_repository: Optional ITestRunRepository instance
            token_service: Optional TokenIntegrationService instance
        """
        self.db = db_session
        self.schedule_resolver = schedule_resolver or ScheduleResolver()
        self.status_manager = status_manager
        self.result_persister = result_persister
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()
        self.token_service = token_service or TokenIntegrationService()

    # ==================== Token-Enhanced Methods ====================

    @track_metrics("service.execution.create_test_run_with_token_check")
    async def create_test_run_with_token_check(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None,
        check_tokens: bool = True,
        scope_type: str = "test"
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Create test run with token availability checking.

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs
            environment: Environment variables
            db: Database session
            schedule_id: Optional schedule ID
            check_tokens: Whether to check token availability
            scope_type: Token scope type

        Returns:
            ServiceSuccess[TestRun] with created test run and token check result or ServiceError
        """
        try:
            if not test_definition_ids:
                return service_validation_error("Test definition IDs cannot be empty")

            # Use the first test_definition_id as the primary association
            primary_test_definition_id = test_definition_ids[0]

            # Check token availability if requested
            token_check_result = None
            if check_tokens:
                try:
                    # Load test definition for estimation
                    def_result = await db.execute(
                        select(TestDefinition).where(
                            TestDefinition.id == primary_test_definition_id
                        )
                    )
                    test_def = def_result.scalar_one_or_none()

                    if test_def:
                        # Estimate tokens based on test definition
                        playwright_script = getattr(test_def, "playwright_script", None)
                        prompt_text = playwright_script[:1000] if playwright_script else "Test execution"

                        token_check_result = await self.token_service.check_before_llm_call(
                            scope_type=scope_type,
                            scope_id=primary_test_definition_id,
                            prompt=prompt_text,
                            model="glm-4-plus",
                            max_tokens=4096,
                            db=db,
                            enforcement_mode="soft"
                        )

                        # Check if blocked
                        if not token_check_result.get("allowed", True):
                            enforcement_action = token_check_result.get("enforcement_action", "warning")
                            if enforcement_action == "blocked":
                                return service_error(
                                    "Token budget exceeded for test execution",
                                    error_code="TOKEN_BUDGET_EXCEEDED",
                                    details={
                                        "test_definition_id": primary_test_definition_id,
                                        "token_check_result": token_check_result
                                    }
                                )

                            logger.warning(
                                f"Token budget exceeded for test {primary_test_definition_id}, "
                                f"proceeding with warning (soft enforcement)"
                            )

                except Exception as e:
                    logger.error(f"Token check failed: {e}")
                    # Continue anyway - don't block on check failure

            # Create test run using repository
            start_time_ms = int(datetime.utcnow().timestamp() * 1000)
            test_run = await self.test_run_repository.create(
                run_id=run_id,
                test_definition_id=primary_test_definition_id,
                start_time_ms=start_time_ms,
                db_session=db
            )

            logger.info(
                f"Created test run {run_id} with {len(test_definition_ids)} test definitions "
                f"(token_check: {'passed' if token_check_result and token_check_result.get('allowed') else 'skipped'})"
            )

            return service_success(
                test_run,
                metadata={
                    "test_count": len(test_definition_ids),
                    "schedule_id": schedule_id,
                    "token_check_result": token_check_result
                }
            )

        except ValueError as e:
            logger.error(f"Validation error creating test run: {e}")
            return service_validation_error(f"Invalid input: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create test run: {e}")
            return service_error(f"Failed to create test run: {str(e)}", "CREATE_ERROR")

    @track_metrics("service.execution.save_test_results_with_token_tracking")
    async def save_test_results_with_token_tracking(
        self,
        run_id: str,
        results: Dict[str, Any],
        db: AsyncSession,
        track_tokens: bool = True,
        scope_type: str = "test"
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Save test results with token usage tracking.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary
            db: Database session
            track_tokens: Whether to track token usage
            scope_type: Token scope type

        Returns:
            ServiceSuccess[TestRun] with updated test run or ServiceError
        """
        try:
            if not results:
                return service_validation_error("Results cannot be empty")

            # Track token usage if requested
            token_tracking_result = None
            if track_tokens:
                try:
                    # Extract token usage from results
                    tokens_used = results.get("tokens_used", 0)

                    # Get test_definition_id from results
                    test_definition_id = results.get('test_definition_id')
                    if test_definition_id and isinstance(test_definition_id, str):
                        try:
                            test_definition_id = int(test_definition_id)
                        except (ValueError, TypeError):
                            pass

                    if tokens_used > 0 and test_definition_id:
                        token_tracking_result = await self.token_service.track_after_llm_call(
                            scope_type=scope_type,
                            scope_id=test_definition_id,
                            tokens_used=tokens_used,
                            db=db,
                            metadata={
                                "operation": "test_execution",
                                "test_run_id": run_id,
                                "status": results.get("status", "unknown")
                            }
                        )

                        logger.info(
                            f"Tracked {tokens_used} tokens for test run {run_id} "
                            f"(test: {test_definition_id})"
                        )

                except Exception as e:
                    logger.error(f"Token tracking failed: {e}")
                    # Don't fail save operation on tracking errors

            # Add token tracking result to results
            if token_tracking_result:
                results["token_tracking"] = token_tracking_result

            # Save test results using base method
            if not self.result_persister:
                self.result_persister = ResultPersister(db, self.test_run_repository)

            # Extract and convert test_definition_id
            test_definition_id = results.get('test_definition_id')
            if test_definition_id and isinstance(test_definition_id, str):
                try:
                    test_definition_id = int(test_definition_id)
                except (ValueError, TypeError):
                    pass

            # Extract all fields for ResultPersister
            total_tests = results.get('total_tests', 0)
            passed_tests = results.get('passed', 0)
            failed_tests = results.get('failed', 0)
            skipped_tests = results.get('skipped', 0)
            total_duration_ms = results.get('total_duration')
            status = results.get('status', 'unknown')
            error_message = results.get('error')
            start_time_ms = results.get('start_time')
            end_time_ms = results.get('end_time')
            test_cases_data = results.get('test_cases', [])

            # Delegate to ResultPersister
            test_run = await self.result_persister.save_test_results(
                run_id=run_id,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                total_duration_ms=total_duration_ms,
                test_definition_id=test_definition_id,
                status=status,
                error_message=error_message,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                test_results=test_cases_data,
                db=db
            )

            return service_success(
                test_run,
                metadata={
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "skipped": skipped_tests,
                    "token_tracking": token_tracking_result
                }
            )

        except ValueError as e:
            logger.error(f"Validation error saving test results: {e}")
            return service_validation_error(f"Invalid results data: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
            return service_error(f"Failed to save test results: {str(e)}", "SAVE_ERROR")

    @track_metrics("service.execution.check_execution_token_availability")
    async def check_execution_token_availability(
        self,
        test_definition_id: int,
        db: AsyncSession,
        scope_type: str = "test",
        model: str = "glm-4-plus",
        max_tokens: int = 4096
    ) -> ServiceSuccess[Dict[str, Any]] | ServiceError:
        """
        Check token availability for test execution.

        Args:
            test_definition_id: Test definition ID
            db: Database session
            scope_type: Token scope type
            model: Model name for estimation
            max_tokens: Max tokens for estimation

        Returns:
            ServiceSuccess with token availability check result or ServiceError
        """
        try:
            # Load test definition for estimation
            def_result = await db.execute(
                select(TestDefinition).where(TestDefinition.id == test_definition_id)
            )
            test_def = def_result.scalar_one_or_none()

            if not test_def:
                return service_not_found("TestDefinition", str(test_definition_id))

            # Get script for estimation
            playwright_script = getattr(test_def, "playwright_script", None)
            prompt_text = playwright_script[:1000] if playwright_script else "Test execution"

            # Check availability
            check_result = await self.token_service.check_before_llm_call(
                scope_type=scope_type,
                scope_id=test_definition_id,
                prompt=prompt_text,
                model=model,
                max_tokens=max_tokens,
                db=db,
                enforcement_mode="soft"
            )

            return service_success(check_result)

        except Exception as e:
            logger.error(f"Failed to check token availability: {e}")
            return service_error(f"Failed to check token availability: {str(e)}", "TOKEN_CHECK_ERROR")

    @track_metrics("service.execution.track_execution_token_usage")
    async def track_execution_token_usage(
        self,
        test_definition_id: int,
        run_id: str,
        tokens_used: int,
        db: AsyncSession,
        scope_type: str = "test",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceSuccess[Dict[str, Any]] | ServiceError:
        """
        Track token usage for test execution.

        Args:
            test_definition_id: Test definition ID
            run_id: Test run ID
            tokens_used: Number of tokens used
            db: Database session
            scope_type: Token scope type
            metadata: Additional metadata

        Returns:
            ServiceSuccess with tracking result or ServiceError
        """
        try:
            if metadata is None:
                metadata = {}

            metadata.update({
                "operation": "test_execution",
                "test_run_id": run_id
            })

            tracking_result = await self.token_service.track_after_llm_call(
                scope_type=scope_type,
                scope_id=test_definition_id,
                tokens_used=tokens_used,
                db=db,
                metadata=metadata
            )

            return service_success(tracking_result)

        except Exception as e:
            logger.error(f"Failed to track token usage: {e}")
            return service_error(f"Failed to track token usage: {str(e)}", "TOKEN_TRACK_ERROR")

    @track_metrics("service.execution.handle_token_limit_error")
    async def handle_token_limit_error(
        self,
        run_id: str,
        test_definition_id: int,
        token_error: Dict[str, Any],
        db: AsyncSession
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Handle token limit errors during execution.

        Args:
            run_id: Test run ID
            test_definition_id: Test definition ID
            token_error: Token error details
            db: Database session

        Returns:
            ServiceSuccess with updated test run or ServiceError
        """
        try:
            # Mark run as failed with token error
            if not self.status_manager:
                self.status_manager = RunStatusManager(db)

            error_message = f"Token limit exceeded: {token_error.get('message', 'Unknown error')}"

            test_run = await self.status_manager.mark_run_failed(run_id, error_message)

            logger.warning(
                f"Test run {run_id} marked as failed due to token limits: {error_message}"
            )

            return service_success(
                test_run,
                metadata={
                    "token_error": token_error,
                    "error_type": "token_limit_exceeded"
                }
            )

        except Exception as e:
            logger.error(f"Failed to handle token limit error: {e}")
            return service_error(f"Failed to handle token limit error: {str(e)}", "TOKEN_ERROR_HANDLER_FAILED")

    # ==================== Helper Methods ====================

    def create_token_metadata(
        self,
        operation: str,
        test_definition_id: Optional[int] = None,
        test_run_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create metadata dictionary for token tracking.

        Args:
            operation: Operation type
            test_definition_id: Optional test definition ID
            test_run_id: Optional test run ID
            **kwargs: Additional metadata

        Returns:
            Metadata dictionary
        """
        return self.token_service.create_token_metadata(
            operation=operation,
            test_definition_id=test_definition_id,
            test_run_id=test_run_id,
            **kwargs
        )

    async def get_workflow_token_status(
        self,
        scope_type: str,
        scope_id: int,
        db: AsyncSession
    ) -> ServiceSuccess[Dict[str, Any]] | ServiceError:
        """
        Get current token status for a workflow scope.

        Args:
            scope_type: Scope type
            scope_id: Scope ID
            db: Database session

        Returns:
            ServiceSuccess with token status or ServiceError
        """
        try:
            status = await self.token_service.get_workflow_token_status(
                scope_type=scope_type,
                scope_id=scope_id,
                db=db
            )

            return service_success(status)

        except Exception as e:
            logger.error(f"Failed to get token status: {e}")
            return service_error(f"Failed to get token status: {str(e)}", "TOKEN_STATUS_ERROR")
