"""
Execution Service Interface

Defines the contract for test execution services.
Following the Dependency Inversion Principle - high-level modules should not depend on low-level modules,
but both should depend on abstractions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.core.simple_result_types import ServiceSuccess, ServiceError


class IExecutionService(ABC):
    """
    Interface for test execution services.

    This interface defines the contract for services that manage test execution,
    ensuring that all implementations follow the same behavior and can be
    interchanged without affecting the system (Liskov Substitution Principle).

    Implementations must handle:
    - Resolving target tests from schedules
    - Creating and managing test runs
    - Updating run status
    - Saving test results
    """

    @abstractmethod
    async def resolve_target_tests_v2(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> ServiceSuccess[List[int]] | ServiceError:
        """
        Resolve target test definition IDs based on schedule type.

        Args:
            schedule: Schedule object containing test execution configuration
            db: Database session for data access

        Returns:
            ServiceSuccess containing list of test definition IDs to execute
            or ServiceError if resolution fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    @abstractmethod
    async def create_test_run_v2(
        self,
        run_id: str,
        test_definition_ids: List[int],
        environment: Dict[str, Any],
        db: AsyncSession,
        schedule_id: Optional[int] = None
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Create a new test run record.

        Args:
            run_id: Unique run identifier
            test_definition_ids: List of test definition IDs to execute
            environment: Environment variables for test execution
            db: Database session for persistence
            schedule_id: Optional schedule ID if triggered by schedule

        Returns:
            ServiceSuccess containing created TestRun object
            or ServiceError if creation fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    @abstractmethod
    async def update_run_status_v2(
        self,
        run_id: str,
        status: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Update test run status and timestamps.

        Args:
            run_id: Run identifier
            status: New status value
            start_time: Optional start time
            end_time: Optional end time
            error_message: Optional error message for failed runs

        Returns:
            ServiceSuccess containing updated TestRun object
            or ServiceError if update fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    @abstractmethod
    async def save_test_results_v2(
        self,
        run_id: str,
        results: Dict[str, Any]
    ) -> ServiceSuccess[TestRun] | ServiceError:
        """
        Save test execution results to database.

        Args:
            run_id: Run identifier
            results: Test execution results dictionary containing:
                - total_tests: Total number of tests
                - passed: Number of passed tests
                - failed: Number of failed tests
                - skipped: Number of skipped tests
                - total_duration: Execution duration
                - status: Final run status
                - error: Optional error message
                - test_cases: List of individual test case results

        Returns:
            ServiceSuccess containing updated TestRun object
            or ServiceError if save fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    # Legacy methods for backward compatibility

    @abstractmethod
    async def resolve_target_tests(
        self,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[int]:
        """
        Resolve target test definition IDs (legacy version).

        Args:
            schedule: Schedule object
            db: Database session

        Returns:
            List of test definition IDs

        Raises:
            ValueError: If schedule_type is unknown or required data is missing
        """
        pass

    @abstractmethod
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
            test_definition_environment: Base environment from test definition
            config_env: Environment from RunConfig template

        Returns:
            Merged environment dictionary
        """
        pass
