"""
Unified API Router Configuration

Aggregates all API endpoint routers into a single unified router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_chat,
    analytics,
    suite_permissions,
    suite_versions,
    workspace_permissions,
    workspaces,
    auth,
    charts,
    data_analysis,
    llm_usage,
    reviews,
    run_configs,
    script_generation,
    tags,
    test_generation,
    test_suites,
    test_versions,
    users,
    voice,
    weather,
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
    test_versions.router,
    prefix="/test-versions",
    tags=["test-versions"]
)

api_router.include_router(
    suite_versions.router,
    prefix="/suite-versions",
    tags=["suite-versions"]
)

api_router.include_router(
    suite_permissions.router,
    prefix="/suite-permissions",
    tags=["suite-permissions"]
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
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

api_router.include_router(
    data_analysis.router,
    prefix="/data-analysis",
    tags=["data-analysis"]
)

api_router.include_router(
    workspaces.router,
    prefix="/test-workspaces",
    tags=["workspaces"]
)

api_router.include_router(
    workspace_permissions.router,
    prefix="/test-workspaces",
    tags=["workspace-permissions"]
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

api_router.include_router(
    llm_usage.router,
    prefix="/llm-usage",
    tags=["llm-usage"]
)

api_router.include_router(
    charts.router,
    tags=["charts"]
)

api_router.include_router(
    voice.router,
    prefix="/voice",
    tags=["voice"],
)

api_router.include_router(
    admin_chat.router,
    prefix="/admin/chat",
    tags=["admin-chat"],
)

api_router.include_router(
    script_generation.router,
    prefix="/scripts",
    tags=["script-generation"],
)

api_router.include_router(
    weather.router,
    prefix="/weather",
    tags=["weather"],
)
