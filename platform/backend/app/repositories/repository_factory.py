"""
Repository Factory

Factory for creating repository instances with dependency injection support.
Follows Factory Pattern for flexible repository instantiation.
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository
from app.repositories.test_run_repository import SQLAlchemyTestRunRepository
from app.repositories.interfaces.test_definition_repository_interface import ITestDefinitionRepository
from app.repositories.test_definition_repository import SQLAlchemyTestDefinitionRepository
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository
from app.repositories.schedule_repository import SQLAlchemyScheduleRepository
from app.repositories.interfaces.token_budget_repository_interface import ITokenBudgetRepository
from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
from app.repositories.interfaces.token_quota_repository_interface import ITokenQuotaRepository
from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository
from app.repositories.interfaces.token_alert_repository_interface import ITokenAlertRepository
from app.repositories.token_alert_repository import SQLAlchemyTokenAlertRepository
from app.repositories.interfaces.suite_run_repository_interface import ISuiteRunRepository
from app.repositories.suite_run_repository import SQLAlchemySuiteRunRepository

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """
    Factory for creating repository instances.

    Provides centralized repository creation with support for different
    implementations and database session management.
    """

    # Singleton instances
    _test_run_repository: Optional[ITestRunRepository] = None
    _test_definition_repository: Optional[ITestDefinitionRepository] = None
    _schedule_repository: Optional[IScheduleRepository] = None
    _token_budget_repository: Optional[ITokenBudgetRepository] = None
    _token_quota_repository: Optional[ITokenQuotaRepository] = None
    _token_alert_repository: Optional[ITokenAlertRepository] = None
    _suite_run_repository: Optional[ISuiteRunRepository] = None

    @classmethod
    def get_test_run_repository(cls) -> ITestRunRepository:
        """
        Get or create the TestRun repository instance.

        Returns:
            ITestRunRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_test_run_repository()
            >>> run = await repo.get_by_id("test-123", db_session)
        """
        if cls._test_run_repository is None:
            logger.info("Creating SQLAlchemyTestRunRepository instance")
            cls._test_run_repository = SQLAlchemyTestRunRepository()

        return cls._test_run_repository

    @classmethod
    def get_test_definition_repository(cls) -> ITestDefinitionRepository:
        """
        Get or create the TestDefinition repository instance.

        Returns:
            ITestDefinitionRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_test_definition_repository()
            >>> definition = await repo.get_by_id(123, db_session)
        """
        if cls._test_definition_repository is None:
            logger.info("Creating SQLAlchemyTestDefinitionRepository instance")
            cls._test_definition_repository = SQLAlchemyTestDefinitionRepository()

        return cls._test_definition_repository

    @classmethod
    def get_schedule_repository(cls) -> IScheduleRepository:
        """
        Get or create the Schedule repository instance.

        Returns:
            IScheduleRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_schedule_repository()
            >>> schedule = await repo.get_by_id(123, db_session)
        """
        if cls._schedule_repository is None:
            logger.info("Creating SQLAlchemyScheduleRepository instance")
            cls._schedule_repository = SQLAlchemyScheduleRepository()

        return cls._schedule_repository

    @classmethod
    def get_suite_run_repository(cls) -> ISuiteRunRepository:
        """
        Get or create the SuiteRun repository instance.

        Returns:
            ISuiteRunRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_suite_run_repository()
            >>> run = await repo.get_by_id(123, db_session)
        """
        if cls._suite_run_repository is None:
            logger.info("Creating SQLAlchemySuiteRunRepository instance")
            cls._suite_run_repository = SQLAlchemySuiteRunRepository()

        return cls._suite_run_repository

    @classmethod
    def reset(cls) -> None:
        """
        Reset all repository instances.

        Primarily useful for testing to ensure clean state between tests.

        Example:
            >>> RepositoryFactory.reset()
            >>> # Now new repository instances will be created on next access
        """
        cls._test_run_repository = None
        cls._test_definition_repository = None
        cls._schedule_repository = None
        cls._token_budget_repository = None
        cls._token_quota_repository = None
        cls._token_alert_repository = None
        cls._suite_run_repository = None
        logger.debug("Repository factory reset")

    @classmethod
    def set_test_run_repository(cls, repository: ITestRunRepository) -> None:
        """
        Set a custom TestRun repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ITestRunRepository implementation

        Example:
            >>> mock_repo = MockTestRunRepository()
            >>> RepositoryFactory.set_test_run_repository(mock_repo)
        """
        cls._test_run_repository = repository
        logger.info(f"Set custom TestRun repository: {type(repository).__name__}")

    @classmethod
    def set_test_definition_repository(cls, repository: ITestDefinitionRepository) -> None:
        """
        Set a custom TestDefinition repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ITestDefinitionRepository implementation

        Example:
            >>> mock_repo = MockTestDefinitionRepository()
            >>> RepositoryFactory.set_test_definition_repository(mock_repo)
        """
        cls._test_definition_repository = repository
        logger.info(f"Set custom TestDefinition repository: {type(repository).__name__}")

    @classmethod
    def set_schedule_repository(cls, repository: IScheduleRepository) -> None:
        """
        Set a custom Schedule repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom IScheduleRepository implementation

        Example:
            >>> mock_repo = MockScheduleRepository()
            >>> RepositoryFactory.set_schedule_repository(mock_repo)
        """
        cls._schedule_repository = repository
        logger.info(f"Set custom Schedule repository: {type(repository).__name__}")

    @classmethod
    def set_suite_run_repository(cls, repository: ISuiteRunRepository) -> None:
        """
        Set a custom SuiteRun repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ISuiteRunRepository implementation

        Example:
            >>> mock_repo = MockSuiteRunRepository()
            >>> RepositoryFactory.set_suite_run_repository(mock_repo)
        """
        cls._suite_run_repository = repository
        logger.info(f"Set custom SuiteRun repository: {type(repository).__name__}")

    @classmethod
    def get_token_budget_repository(cls) -> ITokenBudgetRepository:
        """
        Get or create the TokenBudget repository instance.

        Returns:
            ITokenBudgetRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_token_budget_repository()
            >>> budget = await repo.get_by_id(123, db_session)
        """
        if cls._token_budget_repository is None:
            logger.info("Creating SQLAlchemyTokenBudgetRepository instance")
            cls._token_budget_repository = SQLAlchemyTokenBudgetRepository()

        return cls._token_budget_repository

    @classmethod
    def get_token_quota_repository(cls) -> ITokenQuotaRepository:
        """
        Get or create the TokenQuota repository instance.

        Returns:
            ITokenQuotaRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_token_quota_repository()
            >>> quota = await repo.get_by_id(123, db_session)
        """
        if cls._token_quota_repository is None:
            logger.info("Creating SQLAlchemyTokenQuotaRepository instance")
            cls._token_quota_repository = SQLAlchemyTokenQuotaRepository()

        return cls._token_quota_repository

    @classmethod
    def get_token_alert_repository(cls) -> ITokenAlertRepository:
        """
        Get or create the TokenAlert repository instance.

        Returns:
            ITokenAlertRepository implementation instance

        Example:
            >>> repo = RepositoryFactory.get_token_alert_repository()
            >>> alert = await repo.get_by_id(123, db_session)
        """
        if cls._token_alert_repository is None:
            logger.info("Creating SQLAlchemyTokenAlertRepository instance")
            cls._token_alert_repository = SQLAlchemyTokenAlertRepository()

        return cls._token_alert_repository

    @classmethod
    def set_token_budget_repository(cls, repository: ITokenBudgetRepository) -> None:
        """
        Set a custom TokenBudget repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ITokenBudgetRepository implementation

        Example:
            >>> mock_repo = MockTokenBudgetRepository()
            >>> RepositoryFactory.set_token_budget_repository(mock_repo)
        """
        cls._token_budget_repository = repository
        logger.info(f"Set custom TokenBudget repository: {type(repository).__name__}")

    @classmethod
    def set_token_quota_repository(cls, repository: ITokenQuotaRepository) -> None:
        """
        Set a custom TokenQuota repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ITokenQuotaRepository implementation

        Example:
            >>> mock_repo = MockTokenQuotaRepository()
            >>> RepositoryFactory.set_token_quota_repository(mock_repo)
        """
        cls._token_quota_repository = repository
        logger.info(f"Set custom TokenQuota repository: {type(repository).__name__}")

    @classmethod
    def set_token_alert_repository(cls, repository: ITokenAlertRepository) -> None:
        """
        Set a custom TokenAlert repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ITokenAlertRepository implementation

        Example:
            >>> mock_repo = MockTokenAlertRepository()
            >>> RepositoryFactory.set_token_alert_repository(mock_repo)
        """
        cls._token_alert_repository = repository
        logger.info(f"Set custom TokenAlert repository: {type(repository).__name__}")

    @classmethod
    def set_suite_run_repository(cls, repository: ISuiteRunRepository) -> None:
        """
        Set a custom SuiteRun repository implementation.

        Useful for testing with mock repositories or alternative implementations.

        Args:
            repository: Custom ISuiteRunRepository implementation

        Example:
            >>> mock_repo = MockSuiteRunRepository()
            >>> RepositoryFactory.set_suite_run_repository(mock_repo)
        """
        cls._suite_run_repository = repository
        logger.info(f"Set custom SuiteRun repository: {type(repository).__name__}")
