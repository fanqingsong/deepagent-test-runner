"""
Unified API Router Configuration

Aggregates all API endpoint routers into a single unified router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    users,
    test_steps,
    test_versions,
    test_suites,
    test_generation,
    autonomous_planning,
    conversations,
    apps,
    app_permissions,
    tags,
    run_configs,
    reviews,
)

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users.router,
    tags=["users"]
)

api_router.include_router(
    test_steps.router,
    prefix="/test-steps",
    tags=["test-steps"]
)

api_router.include_router(
    test_versions.router,
    prefix="/test-versions",
    tags=["test-versions"]
)

api_router.include_router(
    test_suites.router,
    prefix="/test-suites",
    tags=["test-suites"]
)

api_router.include_router(
    test_generation.router,
    prefix="/test-generation",
    tags=["test-generation"]
)

api_router.include_router(
    autonomous_planning.router,
    prefix="/autonomous-planning",
    tags=["autonomous-planning"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"]
)

api_router.include_router(
    apps.router,
    prefix="/apps",
    tags=["apps"]
)

api_router.include_router(
    app_permissions.router,
    prefix="/apps",
    tags=["app-permissions"]
)

api_router.include_router(
    tags.router,
    prefix="/tags",
    tags=["tags"]
)

api_router.include_router(
    run_configs.router,
    prefix="/run-configs",
    tags=["run-configs"]
)

api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["reviews"]
)
