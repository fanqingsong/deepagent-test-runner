"""
API Endpoint Modules

Exports all endpoint routers for centralized routing.
"""

from app.api.v1.endpoints import analytics
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import test_definitions
from app.api.v1.endpoints import test_steps
from app.api.v1.endpoints import test_versions
from app.api.v1.endpoints import schedules
from app.api.v1.endpoints import jobs
from app.api.v1.endpoints import test_suites
from app.api.v1.endpoints import test_generation
__all__ = [
    "analytics",
    "auth",
    "users",
    "test_definitions",
    "test_steps",
    "test_versions",
    "schedules",
    "jobs",
    "test_suites",
    "test_generation",
]
