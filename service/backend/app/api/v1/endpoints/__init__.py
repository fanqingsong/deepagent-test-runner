"""
API Endpoint Modules

Exports all endpoint routers for centralized routing.
"""

from app.api.v1.endpoints import analytics
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import test_steps
from app.api.v1.endpoints import test_versions
from app.api.v1.endpoints import test_suites
from app.api.v1.endpoints import test_generation
from app.api.v1.endpoints import app_permissions
from app.api.v1.endpoints import tags
from app.api.v1.endpoints import run_configs
from app.api.v1.endpoints import reviews
from app.api.v1.endpoints import test_stream
from app.api.v1.endpoints import chat_stream

__all__ = [
    "analytics",
    "auth",
    "users",
    "test_steps",
    "test_versions",
    "test_suites",
    "test_generation",
    "app_permissions",
    "tags",
    "run_configs",
    "reviews",
    "test_stream",
    "chat_stream",
]
