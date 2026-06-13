"""
API Endpoint Modules

Exports all endpoint routers for centralized routing.
"""

from app.api.v1.endpoints import analytics
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import test_versions
from app.api.v1.endpoints import test_suites
from app.api.v1.endpoints import test_generation
from app.api.v1.endpoints import workspace_permissions
from app.api.v1.endpoints import workspaces
from app.api.v1.endpoints import tags
from app.api.v1.endpoints import run_configs
from app.api.v1.endpoints import reviews
from app.api.v1.endpoints import script_generation
from app.api.v1.endpoints import script_validation
from app.api.v1.endpoints import script_management
from app.api.v1.endpoints import health
from app.api.v1.endpoints import token

__all__ = [
    "analytics",
    "auth",
    "users",
    "test_versions",
    "test_suites",
    "test_generation",
    "workspace_permissions",
    "workspaces",
    "tags",
    "run_configs",
    "reviews",
    "script_generation",
    "script_validation",
    "script_management",
    "health",
    "token",
]
