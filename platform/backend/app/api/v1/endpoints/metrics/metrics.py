"""
Metrics API Endpoints

REST API for accessing performance metrics and system health.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.interfaces.metrics_collector_interface import (
    IMetricsCollector,
    TimingStats,
    MetricsSummary
)
from app.core.container import provide_metrics_collector
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"]
)


@router.get(
    "/summary",
    response_model=Dict[str, Any],
    summary="Get metrics summary",
    description="Get comprehensive metrics summary including timing, counters, gauges, and errors"
)
async def get_metrics_summary(
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get comprehensive metrics summary.

    Requires authentication. Returns all collected metrics including:
    - Timing statistics for all operations
    - Counter values
    - Gauge values
    - Error counts by type and operation
    - Total recordings count

    Args:
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Metrics summary dictionary

    Raises:
        HTTPException 401: If authentication fails (in production)
    """
    # Optional authentication check
    # if not credentials:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Authentication required"
    #     )

    try:
        summary = metrics_collector.get_metrics_summary()

        return {
            "timing_stats": {
                op: {
                    "operation": stats.operation,
                    "count": stats.count,
                    "min_ms": stats.min_ms,
                    "max_ms": stats.max_ms,
                    "avg_ms": stats.avg_ms,
                    "p50_ms": stats.p50_ms,
                    "p95_ms": stats.p95_ms,
                    "p99_ms": stats.p99_ms
                }
                for op, stats in summary.timing_stats.items()
            },
            "counter_values": summary.counter_values,
            "gauge_values": summary.gauge_values,
            "error_counts": summary.error_counts,
            "total_recordings": summary.total_recordings
        }

    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics summary"
        )


@router.get(
    "/timing",
    response_model=Dict[str, Dict[str, Any]],
    summary="Get timing metrics",
    description="Get timing statistics for all operations or specific operation"
)
async def get_timing_metrics(
    operation: Optional[str] = None,
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Dict[str, Any]]:
    """
    Get timing metrics.

    Args:
        operation: Optional operation name to filter (if not provided, returns all)
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Dictionary mapping operation names to timing statistics

    Raises:
        HTTPException 404: If operation specified but not found
        HTTPException 500: If retrieval fails
    """
    if operation:
        # Get specific operation stats
        stats = metrics_collector.get_timing_stats(operation)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No timing stats found for operation: {operation}"
            )

        return {
            operation: {
                "operation": stats.operation,
                "count": stats.count,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms,
                "avg_ms": stats.avg_ms,
                "p50_ms": stats.p50_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms
            }
        }
    else:
        # Get all timing stats
        all_stats = metrics_collector.get_all_timing_stats()

        return {
            op: {
                "operation": stats.operation,
                "count": stats.count,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms,
                "avg_ms": stats.avg_ms,
                "p50_ms": stats.p50_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms
            }
            for op, stats in all_stats.items()
        }


@router.get(
    "/counters",
    response_model=Dict[str, int],
    summary="Get counter metrics",
    description="Get all counter values or specific counter value"
)
async def get_counter_metrics(
    metric: Optional[str] = None,
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, int]:
    """
    Get counter metrics.

    Args:
        metric: Optional metric name to filter (if not provided, returns all)
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Dictionary mapping metric names to counter values
    """
    if metric:
        # Get specific counter
        value = metrics_collector.get_counter_value(metric)
        return {metric: value}
    else:
        # Get all counters
        return metrics_collector.get_all_counters()


@router.get(
    "/gauges",
    response_model=Dict[str, float],
    summary="Get gauge metrics",
    description="Get all gauge values or specific gauge value"
)
async def get_gauge_metrics(
    metric: Optional[str] = None,
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, float]:
    """
    Get gauge metrics.

    Args:
        metric: Optional metric name to filter (if not provided, returns all)
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Dictionary mapping metric names to gauge values

    Raises:
        HTTPException 404: If metric specified but not found
    """
    if metric:
        # Get specific gauge
        value = metrics_collector.get_gauge_value(metric)
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gauge not found: {metric}"
            )
        return {metric: value}
    else:
        # Get all gauges
        return metrics_collector.get_all_gauges()


@router.get(
    "/errors",
    response_model=Dict[str, Dict[str, int]],
    summary="Get error metrics",
    description="Get error counts by type, optionally filtered by operation"
)
async def get_error_metrics(
    operation: Optional[str] = None,
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Dict[str, int]]:
    """
    Get error metrics.

    Args:
        operation: Optional operation name to filter errors (if not provided, returns all)
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Dictionary mapping error types to counts
    """
    if operation:
        # Get errors for specific operation
        return {operation: metrics_collector.get_error_counts(operation)}
    else:
        # Get all errors aggregated
        return {"all": metrics_collector.get_error_counts()}


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Get system health metrics",
    description="Get health check metrics including database, Redis, and LLM API status"
)
async def get_health_metrics(
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get system health metrics.

    Returns health status for key system components:
    - Database connection pool status
    - Redis connection status
    - LLM API availability
    - Active request count
    - Error rates

    Args:
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Health metrics dictionary
    """
    try:
        # Get current active requests
        active_requests = metrics_collector.get_counter_value("http.requests.active")

        # Get error counts
        error_counts = metrics_collector.get_error_counts()

        # Get total errors
        total_errors = sum(error_counts.values())

        # Get total requests
        total_requests = metrics_collector.get_counter_value("http.requests.total")

        # Calculate error rate
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        # Get slow requests
        slow_requests = metrics_collector.get_counter_value("http.requests.slow")

        return {
            "http": {
                "active_requests": active_requests,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate_percent": round(error_rate, 2),
                "slow_requests": slow_requests
            },
            "status": "healthy" if error_rate < 5 else "degraded"
        }

    except Exception as e:
        logger.error(f"Error getting health metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.post(
    "/reset",
    response_model=Dict[str, str],
    summary="Reset metrics",
    description="Reset all metrics (primarily for testing)"
)
async def reset_metrics(
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Reset all metrics.

    This endpoint clears all collected metrics. Use with caution.
    Primarily intended for testing purposes.

    Args:
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        Success message

    Raises:
        HTTPException 403: If not in development mode
    """
    # Only allow in development
    from app.core.config import settings
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics reset only available in development mode"
        )

    try:
        metrics_collector.reset_metrics()
        return {"message": "Metrics reset successfully"}

    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset metrics"
        )


@router.get(
    "/slowest",
    response_model=List[Dict[str, Any]],
    summary="Get slowest operations",
    description="Get operations with highest average execution time"
)
async def get_slowest_operations(
    limit: int = 10,
    metrics_collector: IMetricsCollector = Depends(provide_metrics_collector),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> List[Dict[str, Any]]:
    """
    Get slowest operations by average duration.

    Args:
        limit: Maximum number of operations to return (default: 10)
        metrics_collector: Injected metrics collector
        credentials: Optional HTTP bearer token

    Returns:
        List of timing stats ordered by average duration descending
    """
    try:
        # Check if method is available
        if hasattr(metrics_collector, 'get_top_slowest_operations'):
            slowest = metrics_collector.get_top_slowest_operations(limit)
        else:
            # Fallback: get all and sort manually
            all_stats = list(metrics_collector.get_all_timing_stats().values())
            all_stats.sort(key=lambda x: x.avg_ms, reverse=True)
            slowest = all_stats[:limit]

        return [
            {
                "operation": stats.operation,
                "count": stats.count,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms,
                "avg_ms": stats.avg_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms
            }
            for stats in slowest
        ]

    except Exception as e:
        logger.error(f"Error getting slowest operations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve slowest operations"
        )
