"""
Repository Interfaces Package

Abstract interfaces for repository implementations following SOLID principles.
"""

from app.repositories.interfaces.test_run_repository_interface import ITestRunRepository

__all__ = [
    "ITestRunRepository",
]
