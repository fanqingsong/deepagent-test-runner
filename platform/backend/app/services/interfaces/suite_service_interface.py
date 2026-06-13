"""
Suite Service Interface

Defines the contract for test suite execution services.
Following the Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.models.suite_run import SuiteRun
from app.core.simple_result_types import ServiceSuccess, ServiceError


class ISuiteService(ABC):
    """
    Interface for suite execution services.

    This interface defines the contract for services that manage
    test suite execution, including creating suite runs, resolving
    entries, and orchestrating execution.
    """

    # ==================== Result-based methods (v2) ====================

    @abstractmethod
    def resolve_suite_entries_v2(self, suite: TestSuite) -> ServiceSuccess[List[Dict[str, Any]]] | ServiceError:
        """
        Build ordered entry list from suite_entries, dynamic rules, or fallback to test_definition_ids.

        Args:
            suite: TestSuite object

        Returns:
            ServiceSuccess with list of entry dictionaries or ServiceError
        """
        pass

    @abstractmethod
    async def resolve_dynamic_suite_v2(self, suite: TestSuite) -> ServiceSuccess[List[Dict[str, Any]]] | ServiceError:
        """
        Resolve a dynamic suite by querying test definitions matching tag rules.

        Args:
            suite: TestSuite object

        Returns:
            ServiceSuccess with list of entry dictionaries or ServiceError
        """
        pass

    @abstractmethod
    async def create_suite_run_v2(
        self,
        suite_id: int,
        triggered_by: str = "manual",
        environment_overrides: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
    ) -> ServiceSuccess[SuiteRun] | ServiceError:
        """
        Create a SuiteRun with SuiteRunEntry rows from suite config.

        Args:
            suite_id: Test suite ID
            triggered_by: Trigger source (manual, schedule, etc.)
            environment_overrides: Optional environment variable overrides
            db: Optional database session (if service initialized without db)

        Returns:
            ServiceSuccess[SuiteRun] with created suite run or ServiceError
        """
        pass

    @abstractmethod
    async def get_suite_run_with_entries_v2(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None
    ) -> ServiceSuccess[SuiteRun] | ServiceError:
        """
        Get a suite run by run_id with all entries loaded.

        Args:
            run_id: Suite run identifier
            db: Optional database session (if service initialized without db)

        Returns:
            ServiceSuccess[SuiteRun] with suite run and entries or ServiceError
        """
        pass

    @abstractmethod
    async def cancel_suite_run_v2(
        self,
        suite_run_id: int,
        db: Optional[AsyncSession] = None
    ) -> ServiceSuccess[SuiteRun] | ServiceError:
        """
        Cancel a running suite run, marking remaining entries as skipped.

        Args:
            suite_run_id: Suite run database ID
            db: Optional database session (if service initialized without db)

        Returns:
            ServiceSuccess[SuiteRun] with cancelled suite run or ServiceError
        """
        pass

    # ==================== Legacy methods (maintained for backward compatibility) ====================

    @abstractmethod
    def resolve_suite_entries(self, suite: TestSuite) -> List[Dict[str, Any]]:
        """
        Build ordered entry list from suite_entries, dynamic rules, or fallback to test_definition_ids.

        Args:
            suite: TestSuite object

        Returns:
            List of entry dictionaries
        """
        pass

    @abstractmethod
    async def resolve_dynamic_suite(self, suite: TestSuite) -> List[Dict[str, Any]]:
        """
        Resolve a dynamic suite by querying test definitions matching tag rules.

        Args:
            suite: TestSuite object

        Returns:
            List of entry dictionaries
        """
        pass

    @abstractmethod
    async def resolve_tag_filter(self, tag_filter: str) -> List[int]:
        """
        Resolve a single tag filter to test definition IDs.

        Args:
            tag_filter: Tag to filter by

        Returns:
            List of test definition IDs
        """
        pass

    @abstractmethod
    async def create_suite_run(
        self,
        suite_id: int,
        triggered_by: str = "manual",
        environment_overrides: Optional[Dict[str, Any]] = None,
    ) -> SuiteRun:
        """
        Create a SuiteRun with SuiteRunEntry rows from suite config.

        Args:
            suite_id: Test suite ID
            triggered_by: Trigger source
            environment_overrides: Optional environment variable overrides

        Returns:
            Created SuiteRun object

        Raises:
            ValueError: If suite not found or has no entries
        """
        pass

    @abstractmethod
    async def execute_suite(self, suite_run_id: int) -> Dict[str, Any]:
        """
        Orchestrate execution of a suite run.

        Args:
            suite_run_id: Suite run database ID

        Returns:
            Dictionary with execution results

        Raises:
            ValueError: If suite run not found
        """
        pass

    @abstractmethod
    async def cancel_suite_run(self, suite_run_id: int) -> SuiteRun:
        """
        Cancel a running suite run, marking remaining entries as skipped.

        Args:
            suite_run_id: Suite run database ID

        Returns:
            Cancelled SuiteRun object

        Raises:
            ValueError: If suite run not found or in invalid state
        """
        pass

    @abstractmethod
    async def list_suite_runs(
        self, suite_id: int, skip: int = 0, limit: int = 50
    ) -> List[SuiteRun]:
        """
        List runs for a suite, newest first.

        Args:
            suite_id: Test suite ID
            skip: Number of runs to skip
            limit: Maximum number of runs to return

        Returns:
            List of SuiteRun objects
        """
        pass

    @abstractmethod
    async def get_suite_run_with_entries(self, run_id: str) -> Optional[SuiteRun]:
        """
        Get a suite run by run_id with all entries loaded.

        Args:
            run_id: Suite run identifier

        Returns:
            SuiteRun object with entries or None if not found
        """
        pass
