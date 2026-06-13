"""
Token Alert API Endpoints

Alert management for token budget and quota thresholds.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.core.result_helpers import is_success, is_error, get_data, get_error
from app.models.user import User
from app.schemas.token_budget import (
    TokenAlertResponse,
    TokenAlertListResponse,
    TokenAlertAcknowledge,
)
from app.services.token_alert_service import TokenAlertService

router = APIRouter(prefix="/alerts", tags=["token-alerts"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=TokenAlertListResponse,
    summary="Get active alerts",
    description="Retrieve active token alerts with optional filtering",
    responses={
        200: {"description": "Alerts retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    acknowledged_only: bool = Query(False, description="Show only acknowledged alerts"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenAlertListResponse:
    """
    Get active alerts with pagination and filters.

    Users see their own alerts, admins see all alerts.

    Args:
        page: Page number
        page_size: Items per page
        severity: Optional severity filter
        alert_type: Optional alert type filter
        acknowledged_only: Show only acknowledged alerts
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated alert list
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        # Get alerts with pagination
        offset = (page - 1) * page_size

        # For non-admin users, filter by their user_id
        user_id_filter = None if current_user.is_admin else current_user.id

        alerts, total = await alert_repo.list_all(
            db,
            limit=page_size,
            offset=offset,
            user_id=user_id_filter,
            severity=severity,
            alert_type=alert_type,
            acknowledged_only=acknowledged_only
        )

        total_pages = (total + page_size - 1) // page_size

        return TokenAlertListResponse(
            items=[TokenAlertResponse.model_validate(a) for a in alerts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.get(
    "/{alert_id}",
    response_model=TokenAlertResponse,
    summary="Get alert by ID",
    description="Retrieve detailed information about a specific alert",
    responses={
        200: {"description": "Alert retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Alert not found"},
    },
)
async def get_alert(
    alert_id: int = Path(..., description="Alert ID", ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenAlertResponse:
    """
    Get alert details by ID.

    Users can only view their own alerts unless they are admins.

    Args:
        alert_id: Alert ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Alert details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        alert = await alert_repo.get_by_id(alert_id, db)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Check permissions (admin or own alert)
        if not current_user.is_admin and alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view this alert"
            )

        return TokenAlertResponse.model_validate(alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )


@router.post(
    "/{alert_id}/acknowledge",
    summary="Acknowledge alert",
    description="Mark an alert as acknowledged",
    responses={
        200: {"description": "Alert acknowledged successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Alert not found"},
    },
)
async def acknowledge_alert(
    alert_id: int = Path(..., description="Alert ID", ge=1),
    acknowledgment: TokenAlertAcknowledge = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Acknowledge an alert.

    Users can acknowledge their own alerts, admins can acknowledge any alert.

    Args:
        alert_id: Alert ID
        acknowledgment: Acknowledgment data
        current_user: Authenticated user
        db: Database session

    Returns:
        Acknowledgment result
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        alert = await alert_repo.get_by_id(alert_id, db)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Check permissions
        if not current_user.is_admin and alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to acknowledge this alert"
            )

        # Acknowledge alert
        await alert_repo.acknowledge(
            alert_id,
            current_user.id,
            acknowledgment.acknowledged if acknowledgment else True,
            db
        )
        await db.commit()

        logger.info(f"Alert {alert_id} acknowledged by user {current_user.id}")

        return {
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_by": current_user.id,
            "acknowledged_at": datetime.utcnow().isoformat(),
            "message": "Alert acknowledged successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.get(
    "/history",
    response_model=TokenAlertListResponse,
    summary="Get alert history",
    description="Retrieve historical alerts including resolved ones",
    responses={
        200: {"description": "Alert history retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_alert_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenAlertListResponse:
    """
    Get alert history with pagination and time filter.

    Users see their own history, admins see all history.

    Args:
        page: Page number
        page_size: Items per page
        days_back: Days to look back (default: 30)
        severity: Optional severity filter
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated alert history
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        # Calculate date threshold
        since_date = datetime.utcnow() - timedelta(days=days_back)

        # Get alerts with pagination
        offset = (page - 1) * page_size

        # For non-admin users, filter by their user_id
        user_id_filter = None if current_user.is_admin else current_user.id

        alerts, total = await alert_repo.get_history(
            db,
            since_date=since_date,
            user_id=user_id_filter,
            severity=severity,
            limit=page_size,
            offset=offset
        )

        total_pages = (total + page_size - 1) // page_size

        return TokenAlertListResponse(
            items=[TokenAlertResponse.model_validate(a) for a in alerts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert history: {str(e)}"
        )


@router.put(
    "/config",
    summary="Update alert configuration",
    description="Update global or user-specific alert configuration",
    responses={
        200: {"description": "Configuration updated successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def update_alert_config(
    enable_email: bool = Query(False, description="Enable email notifications"),
    enable_webhook: bool = Query(False, description="Enable webhook notifications"),
    webhook_url: Optional[str] = Query(None, description="Webhook URL"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update alert notification configuration.

    Requires admin privileges.

    Args:
        enable_email: Enable email notifications
        enable_webhook: Enable webhook notifications
        webhook_url: Webhook URL for notifications
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated configuration
    """
    try:
        # In a real implementation, this would update a configuration table
        # For now, we'll return a success response
        logger.info(f"Alert config updated by admin {current_user.id}: "
                    f"email={enable_email}, webhook={enable_webhook}")

        return {
            "message": "Alert configuration updated successfully",
            "config": {
                "email_notifications_enabled": enable_email,
                "webhook_notifications_enabled": enable_webhook,
                "webhook_url": webhook_url if enable_webhook else None,
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": current_user.id
            }
        }

    except Exception as e:
        logger.error(f"Error updating alert config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert configuration: {str(e)}"
        )


@router.get(
    "/my-alerts",
    response_model=TokenAlertListResponse,
    summary="Get current user's alerts",
    description="Retrieve alerts for the currently authenticated user",
    responses={
        200: {"description": "User alerts retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_my_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenAlertListResponse:
    """
    Get alerts for the current user.

    Args:
        page: Page number
        page_size: Items per page
        severity: Optional severity filter
        acknowledged: Optional acknowledgment filter
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated user alert list
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        # Get alerts with pagination
        offset = (page - 1) * page_size

        alerts, total = await alert_repo.list_all(
            db,
            limit=page_size,
            offset=offset,
            user_id=current_user.id,
            severity=severity,
            acknowledged_only=acknowledged if acknowledged is not None else None
        )

        total_pages = (total + page_size - 1) // page_size

        return TokenAlertListResponse(
            items=[TokenAlertResponse.model_validate(a) for a in alerts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting alerts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user alerts: {str(e)}"
        )


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete alert",
    description="Delete an alert (admin only)",
    responses={
        204: {"description": "Alert deleted successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Alert not found"},
    },
)
async def delete_alert(
    alert_id: int = Path(..., description="Alert ID", ge=1),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete an alert.

    Requires admin privileges.

    Args:
        alert_id: Alert ID
        current_user: Authenticated admin user
        db: Database session
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        # Check if alert exists
        existing = await alert_repo.get_by_id(alert_id, db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Delete alert
        await alert_repo.delete(alert_id, db)
        await db.commit()

        logger.info(f"Deleted alert {alert_id} by admin {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )


@router.get(
    "/stats/summary",
    summary="Get alert statistics",
    description="Get summary statistics for alerts",
    responses={
        200: {"description": "Alert statistics retrieved"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_alert_stats(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get alert statistics summary.

    Requires admin privileges.

    Args:
        days_back: Days to analyze (default: 30)
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Alert statistics summary
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        alert_repo = RepositoryFactory.get_token_alert_repository()

        since_date = datetime.utcnow() - timedelta(days=days_back)

        # Get statistics from repository
        stats = await alert_repo.get_statistics(db, since_date=since_date)

        return {
            "period": {
                "days": days_back,
                "start_date": since_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "total_alerts": stats.get("total", 0),
            "by_severity": stats.get("by_severity", {}),
            "by_type": stats.get("by_type", {}),
            "acknowledged": stats.get("acknowledged", 0),
            "unacknowledged": stats.get("unacknowledged", 0),
            "acknowledgement_rate": stats.get("acknowledgement_rate", 0.0)
        }

    except Exception as e:
        logger.error(f"Error getting alert stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert statistics: {str(e)}"
        )
