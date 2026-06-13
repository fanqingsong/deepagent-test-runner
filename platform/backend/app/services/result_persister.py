"""
Result Persister Service

Handles persistence of test execution results following Single Responsibility Principle.
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_run import TestRun
from app.models.test_case import TestCase
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

if TYPE_CHECKING:
    pass  # Avoid circular imports

logger = logging.getLogger(__name__)


class ResultPersister:
    """
    Service for persisting test execution results.

    Responsible for:
    - Saving test run summaries
    - Persisting individual test case results
    - Duration calculations
    - Database transaction management
    """

    def __init__(self, db_session: AsyncSession, test_run_repository: Optional[ITestRunRepository] = None):
        """
        Initialize Result Persister.

        Args:
            db_session: Async database session
            test_run_repository: Optional ITestRunRepository instance (uses factory if not provided)
        """
        self.db = db_session
        if test_run_repository:
            self.test_run_repository = test_run_repository
        else:
            # Lazy import to avoid circular dependency
            from app.repositories.repository_factory import RepositoryFactory
            self.test_run_repository = RepositoryFactory.get_test_run_repository()

    async def save_test_results(
        self,
        run_id: str,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        skipped_tests: int,
        total_duration_ms: int,
        test_definition_id: Optional[int],
        status: str,
        error_message: Optional[str],
        start_time_ms: Optional[int],
        end_time_ms: Optional[int],
        test_results: List[Dict[str, Any]],
        db: AsyncSession
    ) -> TestRun:
        """
        Save test execution results to database.

        Handles both test run summary updates and individual test case persistence.

        Args:
            run_id: Run identifier
            total_tests: Total number of tests executed
            passed_tests: Number of passed tests
            failed_tests: Number of failed tests
            skipped_tests: Number of skipped tests
            total_duration_ms: Total execution duration in milliseconds
            test_definition_id: Test definition ID
            status: Test run status
            error_message: Optional error message
            start_time_ms: Start time in milliseconds
            end_time_ms: End time in milliseconds
            test_results: List of individual test case results
            db: Database session

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If test run not found
        """
        # Update test run using repository
        results_dict = {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'skipped': skipped_tests,
            'total_duration_ms': total_duration_ms,
            'status': status,
            'error_message': error_message,
            'start_time_ms': start_time_ms,
            'end_time_ms': end_time_ms,
            'test_definition_id': test_definition_id,
        }

        test_run = await self.test_run_repository.update_results(run_id, results_dict, db)

        # Persist individual test case results
        if test_results:
            await self._persist_test_cases(test_run, test_results, start_time_ms, end_time_ms)

        await db.commit()
        await db.refresh(test_run)

        logger.info(f"Saved results for test run {run_id}: {test_run.status}")
        return test_run

    async def _persist_test_cases(
        self,
        test_run: TestRun,
        test_results: List[Dict[str, Any]],
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None
    ) -> None:
        """
        Persist individual test case results.

        Args:
            test_run: TestRun object
            test_results: List of test case result dictionaries
            start_time_ms: Start time in milliseconds
            end_time_ms: End time in milliseconds
        """
        test_definition_id = test_run.test_definition_id
        if test_definition_id and isinstance(test_definition_id, str):
            try:
                test_definition_id = int(test_definition_id)
            except (ValueError, TypeError):
                pass  # Keep as is if conversion fails

        # Get timing information
        start_time = int(start_time_ms) if start_time_ms else 0
        end_time = int(end_time_ms) if end_time_ms else 0

        # Create test case records
        test_case_rows = [
            TestCase(
                run_id=test_run.id,
                test_definition_id=test_definition_id,
                test_id=f"{test_definition_id}_step_{idx + 1}",
                description=case_data.get('description', f"Step {idx + 1}"),
                status=case_data.get('status', 'unknown'),
                duration=int(case_data.get('duration', 0)),
                start_time=start_time,
                end_time=end_time,
                error_message=case_data.get('error'),
                screenshot_path=case_data.get('screenshot_path', ''),
            )
            for idx, case_data in enumerate(test_results)
        ]

        self.db.add_all(test_case_rows)
        logger.info("Saved %d test case rows for run %s", len(test_case_rows), test_run.run_id)
