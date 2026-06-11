"""
Reviews API Endpoints — Admin approval workflow for tests, suites, and versions.

Split into focused modules:
- review_pending: Pending review listings
- review_test_versions: Test version approval/rejection/publishing
- review_test_suites: Test suite and suite version approval/rejection/publishing
"""

from fastapi import APIRouter

from .review_pending import router as pending_router
from .review_test_versions import router as test_versions_router
from .review_test_suites import router as test_suites_router

# Create main router and include sub-routers with appropriate prefixes
router = APIRouter()

# Include pending review routes
router.include_router(pending_router, prefix="/pending", tags=["pending"])

# Include test version review routes
router.include_router(test_versions_router, prefix="/versions", tags=["test-versions"])

# Include test suite review routes
router.include_router(test_suites_router, prefix="/suites", tags=["test-suites"])

__all__ = ["router"]
