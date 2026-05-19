"""
Unified API Router Configuration

Aggregates all API endpoint routers from both test-case-service and
scheduler-service into a single unified router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    users,
    test_definitions,
    test_steps,
    test_versions,
    schedules,
    jobs,
    test_suites,
    test_generation,
    sso_config,
    autonomous_planning,
    conversations,
)

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# User management endpoints (note: users.router already has prefix="/users")
api_router.include_router(
    users.router,
    tags=["users"]
)

# SSO configuration endpoints
api_router.include_router(
    sso_config.router,
    prefix="/sso",
    tags=["sso-config"]
)

# Test case management endpoints
api_router.include_router(
    test_definitions.router,
    prefix="/test-definitions",
    tags=["test-definitions"]
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

# Scheduling and execution endpoints
api_router.include_router(
    schedules.router,
    prefix="/schedules",
    tags=["schedules"]
)

api_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["jobs"]
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

# AI-powered autonomous planning endpoints
api_router.include_router(
    autonomous_planning.router,
    prefix="/autonomous-planning",
    tags=["autonomous-planning"]
)

# Analytics and dashboard endpoints
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

# Human-in-the-loop conversation endpoints
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"]
)
