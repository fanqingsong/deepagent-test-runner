"""
Metrics API Endpoints

Provides endpoints for accessing performance metrics and statistics.
"""

from .metrics import router as metrics_router

__all__ = ["metrics_router"]
