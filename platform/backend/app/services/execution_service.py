"""
Execution Service

Handles test execution logic for scheduled tasks with Result wrapper types.
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
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.core.metrics.metrics_decorators import track_timing, track_metrics, track_errors
from app.services.interfaces.execution_service_interface import IExecutionService

logger = logging.getLogger(__name__)


class ExecutionService(IExecutionService):
    """
    Service for managing test execution for scheduled tasks.

    Responsible for:
    - Managing run state
    - Checking execution limits
    - Building environment configurations
    - Creating and updating test runs
    - Saving test results
    """

    def __init__(
        self,
        db_session=None,
        schedule_resolver: Optional[ScheduleResolver] = None,
        status_manager: Optional[RunStatusManager] = None,
        result_persister: Optional[ResultPersister] = None,
        test_run_repository: Optional[ITestRunRepository] = None
    ):
        """
        Initialize Execution Service.

        Args:
            db_session: Async database session
            schedule_resolver: Optional ScheduleResolver instance (created if not provided)
            status_manager: Optional RunStatusManager instance (created if not provided)
            result_persister: Optional ResultPersister instance (created when db is available)
            test_run_repository: Optional ITestRunRepository instance (created if not provided)
        """
        self.db = db_session
        self.schedule_resolver = schedule_resolver or ScheduleResolver()
        self.status_manager = status_manager  # Will be set when db is available
        self.result_persister = result_persister  # Will be set when db is available
        self.test_run_repository = test_run_repository or RepositoryFactory.get_test_run_repository()

    # ==================== Result-based methods (v2) ====================

    async def resolve_target_tests_v2(self, schedule: Schedule, db: AsyncSession) -> ServiceSuccess[List[int]] | ServiceError:
        """
        Resolve target test definition IDs based on schedule type (Result-based version).

        Delegates to ScheduleResolver for actual resolution logic.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            ServiceSuccess[List[int]] with test definition IDs or ServiceError
        """
        try:
            test_ids = await self.schedule_resolver.resolve_schedule(schedule, db)
            return service_success(test_ids)
        except ValueError as e:
            logger.error(f"Failed to resolve target tests: {e}")
            return service_validation_error(f"Invalid schedule configuration: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error resolving target tests: {e}")
            return service_error(f"Failed to resolve target tests: {str(e)}", "RESOLVE_ERROR")

    @track_metrics("service.execution.create_test_run")
    async def create_test_run_v2(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Create a new test run record (Result-based version).

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs
            environment: Environment variables
            db: Database session
            schedule_id: Optional schedule ID if triggered by schedule

        Returns:
            ServiceSuccess[TestRun] with created test run or ServiceError
        """
        try:
            if not test_definition_ids:
                return service_validation_error("Test definition IDs cannot be empty")

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
            return service_success(test_run, metadata={
                "test_count": len(test_definition_ids),
                "schedule_id": schedule_id
            })

        except ValueError as e:
            logger.error(f"Validation error creating test run: {e}")
            return service_validation_error(f"Invalid input: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create test run: {e}")
            return service_error(f"Failed to create test run: {str(e)}", "CREATE_ERROR")

    async def update_run_status_v2(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Update test run status and timestamps (Result-based version).

        Delegates to RunStatusManager for actual status management.

        Args:
            run_id: Run identifier
            status: New status
            start_time: Optional start time
            end_time: Optional end time
            error_message: Optional error message for failed runs

        Returns:
            ServiceSuccess[TestRun] with updated test run or ServiceError
        """
        try:
            if not self.status_manager:
                self.status_manager = RunStatusManager(self.db)

            test_run = await self.status_manager.update_run_status(
                run_id, status, start_time, end_time, error_message
            )

            if not test_run:
                return service_not_found("TestRun", run_id)

            return service_success(test_run)

        except ValueError as e:
            logger.error(f"Invalid status transition for run {run_id}: {e}")
            return service_validation_error(f"Invalid status transition: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
            return service_error(f"Failed to update run status: {str(e)}", "UPDATE_ERROR")

    async def save_test_results_v2(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Save test execution results to database (Result-based version).

        Delegates to ResultPersister for actual persistence logic.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary

        Returns:
            ServiceSuccess[TestRun] with updated test run or ServiceError
        """
        try:
            if not results:
                return service_validation_error("Results cannot be empty")

            # Ensure result persister is initialized with repository
            if not self.result_persister:
                self.result_persister = ResultPersister(self.db, self.test_run_repository)

            # Extract and convert test_definition_id
            test_definition_id = results.get('test_definition_id')
            if test_definition_id and isinstance(test_definition_id, str):
                try:
                    test_definition_id = int(test_definition_id)
                except (ValueError, TypeError):
                    pass  # Keep as is if conversion fails

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
                db=self.db
            )

            return service_success(test_run, metadata={
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests
            })

        except ValueError as e:
            logger.error(f"Validation error saving test results: {e}")
            return service_validation_error(f"Invalid results data: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
            return service_error(f"Failed to save test results: {str(e)}", "SAVE_ERROR")

    # ==================== Legacy methods (maintained for backward compatibility) ====================

    async def resolve_target_tests(self, schedule, db) -> List[int]:
        """
        Resolve target test definition IDs based on schedule type.

        Delegates to ScheduleResolver for actual resolution logic.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            List of test definition IDs to execute

        Raises:
            ValueError: If schedule_type is unknown or required data is missing
        """
        return await self.schedule_resolver.resolve_schedule(schedule, db)

    async def check_execution_limit(self, schedule, db) -> bool:
        """
        Check if execution is allowed based on concurrency settings.

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            True if execution is allowed, False otherwise
        """
        # If concurrent execution is allowed, always return True
        if schedule.allow_concurrent:
            return True

        # TODO: Implement proper concurrency check without schedule_id in TestRun
        return True

    def build_environment(
        self,
        schedule: Schedule,
        test_definition_environment: Optional[Dict[str, Any]] = None,
        config_env: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build final execution environment by merging configurations.

        Merge order (later wins): test_definition < run_config < schedule overrides

        Args:
            schedule: Schedule object with environment_overrides
            test_definition_environment: Base environment from test definition (optional)
            config_env: Environment from RunConfig template (optional)

        Returns:
            Merged environment dictionary
        """
        base_env = test_definition_environment or {}
        config = config_env or {}
        overrides = schedule.environment_overrides or {}

        return {**base_env, **config, **overrides}

    async def create_test_run(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> TestRun:
        """
        Create a new test run record.

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs
            environment: Environment variables
            db: Database session
            schedule_id: Optional schedule ID if triggered by schedule

        Returns:
            Created TestRun object
        """
        # Use the first test_definition_id as the primary association
        # This allows the dashboard to display the test name
        primary_test_definition_id = test_definition_ids[0] if test_definition_ids else None

        # Create test run using repository
        start_time_ms = int(datetime.utcnow().timestamp() * 1000)
        test_run = await self.test_run_repository.create(
            run_id=run_id,
            test_definition_id=primary_test_definition_id,
            start_time_ms=start_time_ms,
            db_session=db
        )

        logger.info(f"Created test run {run_id} with {len(test_definition_ids)} test definitions")
        return test_run

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> TestRun:
        """
        Update test run status and timestamps.

        Delegates to RunStatusManager for actual status management.

        Args:
            run_id: Run identifier
            status: New status
            start_time: Optional start time
            end_time: Optional end time
            error_message: Optional error message for failed runs

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If status transition is invalid
        """
        if not self.status_manager:
            self.status_manager = RunStatusManager(self.db)

        return await self.status_manager.update_run_status(
            run_id, status, start_time, end_time, error_message
        )

    async def ensure_run_running(self, run_id: str) -> TestRun:
        """
        Mark a run as running, including retry after failure.

        Delegates to RunStatusManager for actual status management.

        Args:
            run_id: Run identifier

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If run cannot be started
        """
        if not self.status_manager:
            self.status_manager = RunStatusManager(self.db)

        return await self.status_manager.ensure_run_running(run_id)

    async def finalize_run_status_if_needed(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[TestRun]:
        """
        Apply terminal status when save_test_results did not already set it.

        Delegates to RunStatusManager for actual status management.

        Args:
            run_id: Run identifier
            status: Target terminal status
            error_message: Optional error message

        Returns:
            Updated TestRun object or None if not found
        """
        if not self.status_manager:
            self.status_manager = RunStatusManager(self.db)

        return await self.status_manager.finalize_run_status_if_needed(
            run_id, status, error_message
        )

    async def mark_run_failed(
        self,
        run_id: str,
        error_message: Optional[str] = None,
    ) -> Optional[TestRun]:
        """
        Mark a run as failed without invalid failed->failed transitions.

        Delegates to RunStatusManager for actual status management.

        Args:
            run_id: Run identifier
            error_message: Optional error message

        Returns:
            Updated TestRun object or None if not found
        """
        if not self.status_manager:
            self.status_manager = RunStatusManager(self.db)

        return await self.status_manager.mark_run_failed(run_id, error_message)

    async def save_test_results(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> TestRun:
        """
        Save test execution results to database.

        Delegates to ResultPersister for actual persistence logic.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary

        Returns:
            Updated TestRun object
        """
        # Ensure result persister is initialized with repository
        if not self.result_persister:
            self.result_persister = ResultPersister(self.db, self.test_run_repository)

        # Extract and convert test_definition_id
        test_definition_id = results.get('test_definition_id')
        if test_definition_id and isinstance(test_definition_id, str):
            try:
                test_definition_id = int(test_definition_id)
            except (ValueError, TypeError):
                pass  # Keep as is if conversion fails

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
        return await self.result_persister.save_test_results(
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
