"""
Temporal Activity Interfaces

Standardized interfaces for Temporal activities following SOLID principles,
particularly the Liskov Substitution Principle.

This module provides:
- Base activity interface (IActivity)
- Base input/output classes
- Standard result types
- Activity factory for type-safe creation
"""

from .activity_interface import IActivity
from .activity_result_types import (
    ActivityResult,
    SuccessResult,
    ErrorResult,
    TimeoutResult,
    ValidationErrorResult,
)
from .base_activity import BaseActivity
from .activity_factory import ActivityFactory, get_activity_factory

__all__ = [
    "IActivity",
    "ActivityResult",
    "SuccessResult",
    "ErrorResult",
    "TimeoutResult",
    "ValidationErrorResult",
    "BaseActivity",
    "ActivityFactory",
    "get_activity_factory",
]
