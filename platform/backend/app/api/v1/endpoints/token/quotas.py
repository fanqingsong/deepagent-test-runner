"""
Token Quota API Endpoints

User-specific token quota management and tracking.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.core.result_helpers import is_success, is_error, get_data, get_error
from app.models.user import User
from app.schemas.token_budget import (
    TokenQuotaCreate,
    TokenQuotaUpdate,
    TokenQuotaResponse,
    TokenQuotaListResponse,
)
from app.services.token_quota_service import TokenQuotaService

router = APIRouter(prefix="/quotas", tags=["token-quotas"])
logger = logging.getLogger(__name__)


@router.get(
    "/my-quota",
    response_model=TokenQuotaResponse,
    summary="Get current user's quota",
    description="Retrieve the token quota for the currently authenticated user",
    responses={
        200: {"description": "Quota retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Quota not found for user"},
    },
)
async def get_my_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaResponse:
    """
    Get the current user's token quota.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        User's token quota details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Get quota for current user
        quota = await quota_repo.get_by_user(current_user.id, db)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quota found for current user"
            )

        return TokenQuotaResponse.model_validate(quota)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota: {str(e)}"
        )


@router.get(
    "/{quota_id}",
    response_model=TokenQuotaResponse,
    summary="Get quota by ID",
    description="Retrieve detailed information about a specific token quota",
    responses={
        200: {"description": "Quota retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Quota not found"},
    },
)
async def get_quota(
    quota_id: int = Path(..., description="Quota ID", ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaResponse:
    """
    Get quota details by ID.

    Users can only view their own quotas unless they are admins.

    Args:
        quota_id: Quota ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Quota details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        quota = await quota_repo.get_by_id(quota_id, db)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )

        # Check permissions (admin or own quota)
        if not current_user.is_admin and quota.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view this quota"
            )

        return TokenQuotaResponse.model_validate(quota)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota {quota_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota: {str(e)}"
        )


@router.post(
    "",
    response_model=TokenQuotaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a token quota",
    description="Create a new token quota for a user",
    responses={
        201: {"description": "Quota created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Insufficient permissions"},
        422: {"description": "Validation error"},
    },
)
async def create_quota(
    quota_data: TokenQuotaCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaResponse:
    """
    Create a new token quota.

    Requires admin privileges.

    Args:
        quota_data: Quota creation data
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Created quota details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Check if user already has a quota
        existing = await quota_repo.get_by_user(quota_data.user_id, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {quota_data.user_id} already has a quota"
            )

        # Create quota
        quota = await quota_repo.create(quota_data.model_dump(), db)
        await db.commit()
        await db.refresh(quota)

        logger.info(f"Created quota {quota.id} for user {quota_data.user_id} by admin {current_user.id}")
        return TokenQuotaResponse.model_validate(quota)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create quota: {str(e)}"
        )


@router.put(
    "/{quota_id}",
    response_model=TokenQuotaResponse,
    summary="Update quota",
    description="Update an existing token quota configuration",
    responses={
        200: {"description": "Quota updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Quota not found"},
    },
)
async def update_quota(
    quota_id: int = Path(..., description="Quota ID", ge=1),
    quota_data: TokenQuotaUpdate = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaResponse:
    """
    Update quota configuration.

    Requires admin privileges.

    Args:
        quota_id: Quota ID
        quota_data: Update data
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated quota details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Check if quota exists
        existing = await quota_repo.get_by_id(quota_id, db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )

        # Update quota
        update_data = {k: v for k, v in quota_data.model_dump().items() if v is not None}
        updated = await quota_repo.update(quota_id, update_data, db)
        await db.commit()
        await db.refresh(updated)

        logger.info(f"Updated quota {quota_id} by admin {current_user.id}")
        return TokenQuotaResponse.model_validate(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quota {quota_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update quota: {str(e)}"
        )


@router.post(
    "/{quota_id}/reset",
    summary="Reset quota",
    description="Reset quota usage counters and start new period",
    responses={
        200: {"description": "Quota reset successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Quota not found"},
    },
)
async def reset_quota(
    quota_id: int = Path(..., description="Quota ID", ge=1),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset quota period and usage.

    Requires admin privileges.

    Args:
        quota_id: Quota ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Reset result with updated quota
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Check if quota exists
        quota = await quota_repo.get_by_id(quota_id, db)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )

        # Reset quota
        result = await quota_repo.reset_period(quota_id, db)
        await db.commit()
        await db.refresh(result)

        logger.info(f"Reset quota {quota_id} by admin {current_user.id}")

        return {
            "quota_id": result.id,
            "user_id": result.user_id,
            "message": "Quota reset successfully",
            "used_tokens": result.used_tokens,
            "remaining_tokens": result.remaining_tokens,
            "last_reset_at": result.last_reset_at.isoformat() if result.last_reset_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting quota {quota_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset quota: {str(e)}"
        )


@router.get(
    "/user/{user_id}",
    response_model=TokenQuotaResponse,
    summary="Get user's quota",
    description="Retrieve the token quota for a specific user",
    responses={
        200: {"description": "Quota retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Quota not found for user"},
    },
)
async def get_user_quota(
    user_id: int = Path(..., description="User ID", ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaResponse:
    """
    Get quota for a specific user.

    Users can view their own quota, admins can view any quota.

    Args:
        user_id: User ID
        current_user: Authenticated user
        db: Database session

    Returns:
        User's quota details
    """
    try:
        # Check permissions
        if not current_user.is_admin and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view this user's quota"
            )

        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        quota = await quota_repo.get_by_user(user_id, db)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quota found for user {user_id}"
            )

        return TokenQuotaResponse.model_validate(quota)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user quota: {str(e)}"
        )


@router.get(
    "",
    response_model=TokenQuotaListResponse,
    summary="List all quotas",
    description="List all token quotas with pagination (admin only)",
    responses={
        200: {"description": "Quotas retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def list_quotas(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenQuotaListResponse:
    """
    List all quotas with pagination and filters.

    Requires admin privileges.

    Args:
        page: Page number
        page_size: Items per page
        status_filter: Optional status filter
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Paginated quota list
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Get quotas with pagination
        offset = (page - 1) * page_size

        quotas, total = await quota_repo.list_all(
            db,
            limit=page_size,
            offset=offset,
            status_filter=status_filter
        )

        total_pages = (total + page_size - 1) // page_size

        return TokenQuotaListResponse(
            items=[TokenQuotaResponse.model_validate(q) for q in quotas],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error listing quotas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list quotas: {str(e)}"
        )


@router.delete(
    "/{quota_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete quota",
    description="Delete a token quota",
    responses={
        204: {"description": "Quota deleted successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Quota not found"},
    },
)
async def delete_quota(
    quota_id: int = Path(..., description="Quota ID", ge=1),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a quota.

    Requires admin privileges.

    Args:
        quota_id: Quota ID
        current_user: Authenticated admin user
        db: Database session
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        # Check if quota exists
        existing = await quota_repo.get_by_id(quota_id, db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )

        # Delete quota
        await quota_repo.delete(quota_id, db)
        await db.commit()

        logger.info(f"Deleted quota {quota_id} by admin {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quota {quota_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete quota: {str(e)}"
        )


@router.get(
    "/{quota_id}/status",
    summary="Get quota status",
    description="Get detailed status information for a quota",
    responses={
        200: {"description": "Quota status retrieved"},
        404: {"description": "Quota not found"},
    },
)
async def get_quota_status(
    quota_id: int = Path(..., description="Quota ID", ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed quota status.

    Args:
        quota_id: Quota ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Quota status information
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        quota_repo = RepositoryFactory.get_token_quota_repository()

        quota = await quota_repo.get_by_id(quota_id, db)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )

        # Check permissions
        if not current_user.is_admin and quota.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view this quota"
            )

        # Build status response
        return {
            "quota_id": quota.id,
            "user_id": quota.user_id,
            "name": quota.name,
            "total_tokens": quota.total_tokens,
            "used_tokens": quota.used_tokens,
            "remaining_tokens": quota.remaining_tokens,
            "usage_percentage": round(quota.usage_percentage, 2),
            "status": quota.status,
            "is_near_limit": quota.is_near_limit(80),
            "is_exhausted": quota.is_exhausted,
            "period_type": quota.period_type,
            "reset_strategy": quota.reset_strategy,
            "period_start": quota.period_start.isoformat(),
            "period_end": quota.period_end.isoformat() if quota.period_end else None,
            "last_reset_at": quota.last_reset_at.isoformat() if quota.last_reset_at else None,
            "enforcement_mode": quota.enforcement_mode,
            "priority": quota.priority,
            "alert_thresholds": quota.alert_thresholds,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota status for {quota_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota status: {str(e)}"
        )
