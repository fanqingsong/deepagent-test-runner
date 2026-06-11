"""
Reviews API Endpoints — Admin approval workflow for tests, suites, and versions.

Refactored into focused modules:
- review_pending: Pending review listings
- review_test_versions: Test version approval/rejection/publishing
- review_test_suites: Test suite and suite version approval/rejection/publishing
"""

# Re-export the router from the reviews package
from app.api.v1.endpoints.reviews import router

__all__ = ["router"]
