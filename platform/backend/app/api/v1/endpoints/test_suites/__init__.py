"""
Test Suites API Router

Combines CRUD, execution, and review endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.test_suites.suite_crud import router as crud_router
from app.api.v1.endpoints.test_suites.suite_runs import router as runs_router
from app.api.v1.endpoints.test_suites.suite_review import router as review_router

router = APIRouter()

# Include CRUD endpoints
router.include_router(crud_router)

# Include execution endpoints (with /runs prefix for clarity)
router.include_router(runs_router, prefix="/runs")

# Include review submission endpoint
router.include_router(review_router)
