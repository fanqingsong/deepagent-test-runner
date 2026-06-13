"""
Health Check API Endpoints

Provides endpoints for checking system health and component status.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
import logging

from app.services.health_check_service import health_check_service
from app.core.health_check_types import (
    HealthCheckResult,
    ComponentHealth,
    HealthCheckConfig,
    HealthStatus,
)
from app.health.checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    LLMHealthChecker,
    TemporalHealthChecker,
    FileSystemHealthChecker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get(
    "",
    summary="Simple health check",
    description="Returns 200 if system is operational, 503 if critical components are down"
)
async def health_check():
    """
    Simple health check endpoint.

    Returns HTTP 200 if system is operational (all critical components healthy),
    or HTTP 503 if any critical component is down.
    """
    try:
        result = await health_check_service.check_critical_only()

        # Determine HTTP status based on health status
        if result.status == HealthStatus.HEALTHY:
            return {
                "status": "healthy",
                "timestamp": result.timestamp.isoformat(),
            }
        elif result.status == HealthStatus.DEGRADED:
            # Degraded but operational
            return {
                "status": "degraded",
                "timestamp": result.timestamp.isoformat(),
                "details": result.details,
            }
        else:
            # Critical components down
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "unhealthy",
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details,
                }
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/detailed",
    summary="Detailed health check",
    description="Returns detailed health status for all components",
    response_model=HealthCheckResult
)
async def detailed_health_check(
    critical_only: bool = Query(False, description="Only check critical components"),
    parallel: bool = Query(True, description="Execute checks in parallel"),
    timeout: float = Query(5.0, description="Timeout for each check in seconds"),
    skip_cache: bool = Query(False, description="Skip cache and force new checks"),
):
    """
    Detailed health check endpoint.

    Returns comprehensive health status for all system components,
    including response times, metadata, and overall system health.
    """
    try:
        # Clear cache if requested
        if skip_cache:
            health_check_service.clear_cache()

        # Create configuration
        config = HealthCheckConfig(
            timeout_seconds=timeout,
            parallel_execution=parallel,
            critical_only=critical_only,
            include_non_critical=not critical_only,
        )

        result = await health_check_service.check_health(config)

        return result

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detailed health check failed: {str(e)}"
        )


@router.get(
    "/{component}",
    summary="Check specific component",
    description="Returns health status for a specific component",
    response_model=ComponentHealth
)
async def check_component(component: str):
    """
    Check health of a specific component.

    Valid components:
    - database: PostgreSQL database
    - redis: Redis cache
    - llm: LLM API
    - temporal: Temporal server
    - filesystem: File system and disk space
    """
    try:
        result = await health_check_service.check_component(component)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Component health check failed for {component}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Component health check failed: {str(e)}"
        )


@router.get(
    "/critical",
    summary="Check critical components only",
    description="Returns health status for critical components only",
    response_model=HealthCheckResult
)
async def check_critical(
    skip_cache: bool = Query(False, description="Skip cache and force new checks")
):
    """
    Check only critical components (database, redis, filesystem).

    Returns quickly by focusing on components required for system operation.
    """
    try:
        if skip_cache:
            health_check_service.clear_cache()

        result = await health_check_service.check_critical_only()

        return result

    except Exception as e:
        logger.error(f"Critical health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical health check failed: {str(e)}"
        )


@router.get(
    "/summary",
    summary="Health check summary",
    description="Returns a summary of current health status"
)
async def health_summary():
    """
    Get a summary of the current health status.

    Returns a quick overview without detailed component information.
    """
    try:
        summary = health_check_service.get_status_summary()

        # Determine HTTP status
        if summary.get("status") == "healthy":
            status_code = status.HTTP_200_OK
        elif summary.get("status") == "degraded":
            status_code = status.HTTP_200_OK  # Still operational
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return summary

    except Exception as e:
        logger.error(f"Health summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health summary failed: {str(e)}"
        )


@router.get(
    "/history",
    summary="Health check history",
    description="Returns historical health check data"
)
async def health_history(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of history entries")
):
    """
    Get historical health check data.

    Returns recent health check results for trending and analysis.
    """
    try:
        history = health_check_service.get_history(limit=limit)

        return {
            "total_entries": len(history),
            "entries": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "status": entry.status.value,
                    "response_time_ms": entry.response_time_ms,
                    "component_count": entry.component_count,
                    "unhealthy_count": entry.unhealthy_count,
                }
                for entry in history
            ],
        }

    except Exception as e:
        logger.error(f"Health history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health history failed: {str(e)}"
        )


@router.post(
    "/cache/clear",
    summary="Clear health check cache",
    description="Clears the health check result cache"
)
async def clear_health_cache():
    """
    Clear the health check cache.

    Forces new health checks on the next request.
    """
    try:
        health_check_service.clear_cache()

        return {
            "message": "Health check cache cleared successfully",
        }

    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache clear failed: {str(e)}"
        )
