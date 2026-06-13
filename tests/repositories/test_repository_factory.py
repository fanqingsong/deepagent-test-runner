"""
Repository Factory Tests

Tests for the RepositoryFactory including singleton pattern,
custom repository injection, and reset functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository


class MockTestRunRepository(ITestRunRepository):
    """Mock repository for testing."""

    async def create(self, run_id, test_definition_id, start_time_ms, db_session):
        return Mock()

    async def get_by_id(self, run_id, db_session):
        return None

    async def get_by_pk(self, pk, db_session):
        return None

    async def update_status(self, run_id, status, db_session, start_time_ms=None, end_time_ms=None, error_message=None):
        return Mock()

    async def update_results(self, run_id, results, db_session):
        return Mock()

    async def get_by_test_definition_id(self, test_definition_id, db_session, limit=10, offset=0):
        return []

    async def get_pending_runs(self, db_session, limit=100):
        return []

    async def get_recent_runs(self, db_session, days=7, limit=100):
        return []

    async def count_by_status(self, status, db_session):
        return 0

    async def delete(self, run_id, db_session):
        return False

    async def get_all(self, db_session, limit=100, offset=0, status_filter=None):
        return []

    async def exists(self, run_id, db_session):
        return False

    async def get_stats_by_date_range(self, start_date, end_date, db_session):
        return {}


class TestRepositoryFactory:
    """Test suite for RepositoryFactory."""

    def test_singleton_pattern(self):
        """Test that get_test_run_repository returns singleton instance."""
        # Reset factory to ensure clean state
        RepositoryFactory.reset()

        # Get repository instance twice
        repo1 = RepositoryFactory.get_test_run_repository()
        repo2 = RepositoryFactory.get_test_run_repository()

        # Should be the same instance
        assert repo1 is repo2
        assert isinstance(repo1, ITestRunRepository)

    def test_reset_clears_singleton(self):
        """Test that reset clears singleton instances."""
        # Get repository instance
        repo1 = RepositoryFactory.get_test_run_repository()

        # Reset factory
        RepositoryFactory.reset()

        # Get new instance
        repo2 = RepositoryFactory.get_test_run_repository()

        # Should be different instances
        assert repo1 is not repo2

    def test_set_custom_repository(self):
        """Test setting a custom repository implementation."""
        # Reset factory
        RepositoryFactory.reset()

        # Create mock repository
        mock_repo = MockTestRunRepository()

        # Set custom repository
        RepositoryFactory.set_test_run_repository(mock_repo)

        # Get repository should return custom instance
        repo = RepositoryFactory.get_test_run_repository()
        assert repo is mock_repo
        assert isinstance(repo, MockTestRunRepository)

    def test_custom_repository_persists(self):
        """Test that custom repository persists across calls."""
        # Reset factory
        RepositoryFactory.reset()

        # Create and set mock repository
        mock_repo = MockTestRunRepository()
        RepositoryFactory.set_test_run_repository(mock_repo)

        # Get repository multiple times
        repo1 = RepositoryFactory.get_test_run_repository()
        repo2 = RepositoryFactory.get_test_run_repository()

        # Should be the same custom instance
        assert repo1 is mock_repo
        assert repo2 is mock_repo
        assert repo1 is repo2

    def test_reset_after_custom_repository(self):
        """Test that reset works after setting custom repository."""
        # Reset factory
        RepositoryFactory.reset()

        # Set custom repository
        mock_repo = MockTestRunRepository()
        RepositoryFactory.set_test_run_repository(mock_repo)

        # Verify custom repository is set
        repo1 = RepositoryFactory.get_test_run_repository()
        assert repo1 is mock_repo

        # Reset factory
        RepositoryFactory.reset()

        # Should get default repository now
        repo2 = RepositoryFactory.get_test_run_repository()
        assert repo2 is not mock_repo
        assert type(repo2).__name__ == "SQLAlchemyTestRunRepository"

    def test_multiple_reset_cycles(self):
        """Test multiple reset cycles."""
        for _ in range(3):
            # Get repository
            repo1 = RepositoryFactory.get_test_run_repository()

            # Reset
            RepositoryFactory.reset()

            # Get new repository
            repo2 = RepositoryFactory.get_test_run_repository()

            # Should be different instances
            assert repo1 is not repo2

            # Reset again
            RepositoryFactory.reset()
