"""
Execution Service with Result Types

Enhanced ExecutionService using standardized result wrapper types.
This demonstrates how to update services to use result types while maintaining backward compatibility.
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
from app.services.schedule_resolver import ScheduleResolver
from app.services.run_status_manager import RunStatusManager
from app.services.result_persister import ResultPersister
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

# Import new result types
from app.core.result_types import Result, Success, Error, Timeout
from app.core.service_result_types import (
    ServiceResult, ServiceSuccess, ServiceError,
    DatabaseError, NotFoundError, ConflictError,
    TestExecutionError, ErrorCode
)
from app.core.result_helpers import (
    service_success, service_error, not_found, conflict,
    database_error, test_execution_error, async_catch_exception,
    async_result_decorator
)

logger = logging.getLogger(__name__)


class ExecutionServiceWithResults:
    """
    Enhanced Execution Service using result wrapper types.

    This service demonstrates how to use result types while maintaining
    backward compatibility with existing code.

    Key improvements:
    - All methods return typed Result objects
    - Explicit error types and codes
    - Chainable operations
    - Better error handling
    - HTTP status mapping
    """

    def __init__(
        self,
        db_session=None,
        schedule_resolver: Optional[ScheduleResolver] = None,
        status_manager: Optional[RunStatusManager] = None,
        result_persister: Optional[ResultPersister] = None,
        test_run_repository: Optional[ITestRunRepository] = None
    ):
        """Initialize Execution Service with Results."""
        self.db = db_session
        self.schedule_resolver = schedule_resolver or ScheduleResolver()
        self.status_manager = status_manager
        self.result_persister = result_persister
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()

    # ========================================================================
    # NEW METHODS WITH RESULT TYPES
    # ========================================================================

    @async_result_decorator("Failed to resolve target tests", ErrorCode.BUSINESS_LOGIC_ERROR)
    async def resolve_target_tests_result(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> ServiceSuccess[List[int]]:
        """
        Resolve target test definition IDs with result type.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            ServiceSuccess with list of test definition IDs
            ServiceError if resolution fails
        """
        test_definition_ids = await self.schedule_resolver.resolve_schedule(schedule, db)

        if not test_definition_ids:
            return test_execution_error(
                message="No test definitions found for schedule",
                test_id=str(schedule.id),
                execution_stage="resolution",
                service_name="ExecutionService",
                operation_name="resolve_target_tests"
            )

        return service_success(
            data=test_definition_ids,
            service_name="ExecutionService",
            operation_name="resolve_target_tests"
        )

    @async_result_decorator("Failed to check execution limit", ErrorCode.DATABASE_ERROR)
    async def check_execution_limit_result(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> ServiceSuccess[bool]:
        """
        Check if execution is allowed with result type.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            ServiceSuccess with boolean indicating if execution allowed
        """
        # If concurrent execution is allowed, always return True
        if schedule.allow_concurrent:
            return service_success(
                data=True,
                service_name="ExecutionService",
                operation_name="check_execution_limit"
            )

        # TODO: Implement proper concurrency check
        return service_success(
            data=True,
            service_name="ExecutionService",
            operation_name="check_execution_limit"
        )

    def build_environment_result(
        self,
        schedule: Schedule,
        test_definition_environment: Optional[Dict[str, Any]] = None,
        config_env: Optional[Dict[str, Any]] = None,
    ) -> ServiceSuccess[Dict[str, Any]]:
        """
        Build execution environment with result type.

        Args:
            schedule: Schedule object
            test_definition_environment: Base environment from test definition
            config_env: Environment from RunConfig template

        Returns:
            ServiceSuccess with merged environment dictionary
        """
        try:
            base_env = test_definition_environment or {}
            config = config_env or {}
            overrides = schedule.environment_overrides or {}

            merged_env = {**base_env, **config, **overrides}

            return service_success(
                data=merged_env,
                service_name="ExecutionService",
                operation_name="build_environment",
                metadata={
                    "base_vars": len(base_env),
                    "config_vars": len(config),
                    "override_vars": len(overrides)
                }
            )
        except Exception as e:
            return service_error(
                message=f"Failed to build environment: {str(e)}",
                error_code=ErrorCode.OPERATION_FAILED,
                service_name="ExecutionService",
                operation_name="build_environment"
            )

    @async_result_decorator("Failed to create test run", ErrorCode.DATABASE_ERROR)
    async def create_test_run_result(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> ServiceSuccess[TestRun]:
        """
        Create test run with result type.

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs
            environment: Environment variables
            db: Database session
            schedule_id: Optional schedule ID

        Returns:
            ServiceSuccess with created TestRun object
            ServiceError if creation fails
        """
        if not test_definition_ids:
            return test_execution_error(
                message="Cannot create test run: no test definitions provided",
                test_id=run_id,
                execution_stage="creation",
                service_name="ExecutionService",
                operation_name="create_test_run"
            )

        # Use the first test_definition_id as the primary association
        primary_test_definition_id = test_definition_ids[0]

        # Create test run using repository
        start_time_ms = int(datetime.utcnow().timestamp() * 1000)
        test_run = await self.test_run_repository.create(
            run_id=run_id,
            test_definition_id=primary_test_definition_id,
            start_time_ms=start_time_ms,
            db_session=db
        )

        logger.info(f"Created test run {run_id} with {len(test_definition_ids)} test definitions")

        return service_success(
            data=test_run,
            service_name="ExecutionService",
            operation_name="create_test_run",
            metadata={
                "run_id": run_id,
                "test_count": len(test_definition_ids),
                "schedule_id": schedule_id
            }
        )

    @async_result_decorator("Failed to update run status", ErrorCode.DATABASE_ERROR)
    async def update_run_status_result(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> ServiceSuccess[TestRun]:
        """
        Update test run status with result type.

        Args:
            run_id: Run identifier
            status: New status
            start_time: Optional start time
            end_time: Optional end time
            error_message: Optional error message

        Returns:
            ServiceSuccess with updated TestRun
            ServiceError if update fails
        """
        if not self.status_manager:
            self.status_manager = RunStatusManager(self.db)

        try:
            test_run = await self.status_manager.update_run_status(
                run_id, status, start_time, end_time, error_message
            )

            return service_success(
                data=test_run,
                service_name="ExecutionService",
                operation_name="update_run_status",
                metadata={"status": status}
            )
        except ValueError as e:
            # Status transition error
            return test_execution_error(
                message=f"Invalid status transition: {str(e)}",
                test_id=run_id,
                execution_stage="status_update",
                service_name="ExecutionService",
                operation_name="update_run_status"
            )

    @async_result_decorator("Failed to save test results", ErrorCode.DATABASE_ERROR)
    async def save_test_results_result(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> ServiceSuccess[TestRun]:
        """
        Save test execution results with result type.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary

        Returns:
            ServiceSuccess with updated TestRun
            ServiceError if save fails
        """
        # Ensure result persister is initialized
        if not self.result_persister:
            self.result_persister = ResultPersister(self.db, self.test_run_repository)

        # Extract and validate required fields
        if not results:
            return test_execution_error(
                message="Cannot save empty results",
                test_id=run_id,
                execution_stage="save_results",
                service_name="ExecutionService",
                operation_name="save_test_results"
            )

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

        # Validate data consistency
        if total_tests != (passed_tests + failed_tests + skipped_tests):
            return test_execution_error(
                message=f"Test count mismatch: total={total_tests}, "
                       f"passed={passed_tests}, failed={failed_tests}, skipped={skipped_tests}",
                test_id=run_id,
                execution_stage="save_results",
                service_name="ExecutionService",
                operation_name="save_test_results"
            )

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
            db=self.db
        )

        return service_success(
            data=test_run,
            service_name="ExecutionService",
            operation_name="save_test_results",
            metadata={
                "run_id": run_id,
                "status": status,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests
            }
        )

    # ========================================================================
    # BACKWARD COMPATIBILITY METHODS
    # ========================================================================

    async def resolve_target_tests(self, schedule, db) -> List[int]:
        """
        Backward compatible method that extracts data from result.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            List of test definition IDs

        Raises:
            ValueError: If resolution fails
        """
        result = await self.resolve_target_tests_result(schedule, db)
        if result.is_error():
            raise ValueError(result.get_error_message())
        return result.get_data()

    async def check_execution_limit(self, schedule, db) -> bool:
        """Backward compatible method for checking execution limit."""
        result = await self.check_execution_limit_result(schedule, db)
        return result.get_data()

    def build_environment(
        self,
        schedule: Schedule,
        test_definition_environment: Optional[Dict[str, Any]] = None,
        config_env: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Backward compatible method for building environment."""
        result = self.build_environment_result(schedule, test_definition_environment, config_env)
        if result.is_error():
            raise ValueError(result.get_error_message())
        return result.get_data()

    async def create_test_run(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> TestRun:
        """Backward compatible method for creating test run."""
        result = await self.create_test_run_result(
            run_id, test_definition_ids, environment, db, schedule_id
        )
        if result.is_error():
            raise ValueError(result.get_error_message())
        return result.get_data()

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> TestRun:
        """Backward compatible method for updating run status."""
        result = await self.update_run_status_result(
            run_id, status, start_time, end_time, error_message
        )
        if result.is_error():
            raise ValueError(result.get_error_message())
        return result.get_data()

    async def save_test_results(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> TestRun:
        """Backward compatible method for saving test results."""
        result = await self.save_test_results_result(run_id, results)
        if result.is_error():
            raise ValueError(result.get_error_message())
        return result.get_data()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage_new_style():
    """Example showing how to use the new result-based methods."""

    async def execute_scheduled_test(schedule: Schedule, db: AsyncSession):
        service = ExecutionServiceWithResults(db_session=db)

        # Using new result-based methods
        test_ids_result = await service.resolve_target_tests_result(schedule, db)

        if test_ids_result.is_error():
            # Handle error with proper type
            logger.error(f"Failed to resolve tests: {test_ids_result.get_error_message()}")
            return None

        test_definition_ids = test_ids_result.get_data()

        # Chain operations
        limit_result = await service.check_execution_limit_result(schedule, db)

        if not limit_result.get_data():
            return test_execution_error(
                "Execution limit reached",
                service_name="ExecutionService"
            )

        # Create run with result
        env_result = service.build_environment_result(schedule)
        run_result = await service.create_test_run_result(
            run_id="test-123",
            test_definition_ids=test_definition_ids,
            environment=env_result.get_data(),
            db=db
        )

        return run_result


def example_usage_backward_compatible():
    """Example showing backward compatibility - existing code still works."""

    async def execute_scheduled_test(schedule: Schedule, db: AsyncSession):
        service = ExecutionServiceWithResults(db_session=db)

        # Old style still works - returns data directly
        test_definition_ids = await service.resolve_target_tests(schedule, db)

        # Can build environment
        environment = service.build_environment(schedule)

        # Create test run
        test_run = await service.create_test_run(
            run_id="test-123",
            test_definition_ids=test_definition_ids,
            environment=environment,
            db=db
        )

        return test_run


def example_migration_pattern():
    """Example showing gradual migration pattern."""

    async def execute_scheduled_test(schedule: Schedule, db: AsyncSession):
        service = ExecutionServiceWithResults(db_session=db)

        # Mix new and old styles during migration
        test_ids_result = await service.resolve_target_tests_result(schedule, db)

        # Extract data for compatibility with old code
        if test_ids_result.is_success():
            test_definition_ids = test_ids_result.get_data()
        else:
            # Handle error
            raise ValueError(test_ids_result.get_error_message())

        # Use old style for now
        environment = service.build_environment(schedule)

        # Eventually migrate to new style
        # environment_result = service.build_environment_result(schedule)
        # if environment_result.is_error():
        #     handle_error(environment_result)

        return test_definition_ids
