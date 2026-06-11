"""
TestSuites API Endpoints

Test suite management for organizing and managing test definitions.
This file serves as a facade that imports from split sub-modules.
"""

from app.api.v1.endpoints.test_suites import router

__all__ = ["router"]
