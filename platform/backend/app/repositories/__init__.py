"""
Repositories Package

Provides repository pattern implementation for database operations following
SOLID Dependency Inversion Principle.

Services depend on repository interfaces rather than concrete database implementations,
enabling testability and flexibility.
"""

from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

__all__ = [
    "RepositoryFactory",
    "ITestRunRepository",
]
