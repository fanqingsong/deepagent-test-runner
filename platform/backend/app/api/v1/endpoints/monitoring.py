"""
Monitoring API Endpoints

Provides system health monitoring status, alerts, and reports.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.monitoring_service import MonitoringService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()
monitoring_service = MonitoringService()


@router.get("/status")
async def get_monitoring_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current monitoring status.

    Returns the latest monitoring snapshot with:
    - Overall system status (normal/warning/critical)
    - Last check time
    - Active alerts count
    - System metrics
    - Report summary

    Requires authentication.
    """
    monitoring_service.db = db
    status = await monitoring_service.get_current_status()
    return status


@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Only return unacknowledged alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity (warning/critical)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alerts with optional filters.

    Returns alert history with the ability to filter by:
    - Active (unacknowledged) status
    - Alert type
    - Severity level

    Requires authentication.
    """
    monitoring_service.db = db

    if active_only:
        alerts = await monitoring_service.get_active_alerts(limit=limit)
    else:
        alerts = await monitoring_service.get_alert_history(
            alert_type=alert_type,
            severity=severity,
            acknowledged=None if not active_only else False,
            limit=limit
        )

    return {
        "alerts": alerts,
        "count": len(alerts)
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge an alert.

    Marks the alert as acknowledged by the current user.
    Requires authentication.

    Args:
        alert_id: The ID of the alert to acknowledge

    Returns:
        Updated alert data
    """
    monitoring_service.db = db

    result = await monitoring_service.acknowledge_alert(
        alert_id=alert_id,
        user_id=current_user.id
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return result


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an alert as resolved.

    Requires authentication.

    Args:
        alert_id: The ID of the alert to resolve

    Returns:
        Updated alert data
    """
    monitoring_service.db = db

    result = await monitoring_service.resolve_alert(alert_id=alert_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return result


@router.get("/reports")
async def get_monitoring_reports(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to include (max 7 days)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of reports to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring reports (snapshots) from the specified time range.

    Returns historical monitoring snapshots showing:
    - System status over time
    - Metrics trends
    - Alerts generated at each check

    Requires authentication.
    """
    monitoring_service.db = db
    reports = await monitoring_service.get_monitoring_reports(hours=hours, limit=limit)

    return {
        "reports": reports,
        "count": len(reports),
        "hours": hours
    }


@router.get("/statistics")
async def get_alert_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to include (max 7 days)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert statistics for the specified time range.

    Returns aggregated alert statistics:
    - Total alerts
    - By severity (critical/warning)
    - By alert type

    Requires authentication.
    """
    monitoring_service.db = db
    stats = await monitoring_service.get_alert_statistics(hours=hours)

    return stats


@router.get("/configurations")
async def get_alert_configurations(
    enabled_only: bool = Query(False, description="Only return enabled configurations"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert configurations.

    Returns user-defined alert rules that can be:
    - Enabled/disabled
    - Filtered by enabled status

    Requires authentication. Admin-only in future.
    """
    monitoring_service.db = db
    configs = await monitoring_service.get_alert_configurations(enabled_only=enabled_only)

    return {
        "configurations": configs,
        "count": len(configs)
    }


@router.post("/schedule/start")
async def start_monitoring_schedule(
    check_interval_seconds: int = Query(300, ge=60, le=3600, description="Check interval in seconds"),
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range for metrics in hours"),
    current_user: User = Depends(get_current_user)
):
    """
    Start the Monitoring Agent schedule.

    Creates a Temporal Schedule that runs the monitoring workflow
    periodically to collect system health metrics and detect issues.

    Requires admin privileges.

    Args:
        check_interval_seconds: How often to run monitoring checks (default: 300s = 5 minutes)
        time_range_hours: Time window for metrics collection (default: 24 hours)

    Returns:
        dict: Schedule creation result
    """
    # Check admin privileges
    if not (current_user.is_admin or current_user.has_role("admin")):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from app.temporal.client import start_monitoring_schedule

    try:
        result = await start_monitoring_schedule(
            check_interval_seconds=check_interval_seconds,
            time_range_hours=time_range_hours,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring schedule: {str(e)}")


@router.post("/schedule/stop")
async def stop_monitoring_schedule(
    current_user: User = Depends(get_current_user)
):
    """
    Stop the Monitoring Agent schedule.

    Requires admin privileges.

    Returns:
        dict: Schedule deletion result
    """
    # Check admin privileges
    if not (current_user.is_admin or current_user.has_role("admin")):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from app.temporal.client import stop_monitoring_schedule

    try:
        result = await stop_monitoring_schedule()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring schedule: {str(e)}")


@router.get("/schedule/status")
async def get_schedule_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of the Monitoring Agent schedule.

    Returns:
        dict: Schedule status information
    """
    from app.temporal.client import get_monitoring_schedule_status

    try:
        result = await get_monitoring_schedule_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule status: {str(e)}")
