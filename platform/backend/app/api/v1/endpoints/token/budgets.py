"""
Token Budget API Endpoints

CRUD operations for token budget management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.core.result_helpers import is_success, is_error, get_data, get_error
from app.models.user import User
from app.schemas.token_budget import (
    TokenBudgetCreate,
    TokenBudgetUpdate,
    TokenBudgetResponse,
    TokenBudgetListResponse,
)
from app.services.token_budget_service import TokenBudgetService

router = APIRouter(prefix="/budgets", tags=["token-budgets"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=TokenBudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a token budget",
    description="Create a new token budget with specified limits and enforcement mode",
    responses={
        201: {"description": "Budget created successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Insufficient permissions"},
        422: {"description": "Validation error"},
    },
)
async def create_budget(
    budget_data: TokenBudgetCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenBudgetResponse:
    """
    Create a new token budget.

    Requires admin privileges.

    Args:
        budget_data: Budget creation data
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Created budget details
    """
    try:
        service = TokenBudgetService()

        # Create budget via repository
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Create the budget
        budget = await budget_repo.create(budget_data.model_dump(), db)
        await db.commit()
        await db.refresh(budget)

        logger.info(f"Created budget {budget.id} by user {current_user.id}")
        return TokenBudgetResponse.model_validate(budget)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create budget: {str(e)}"
        )


@router.get(
    "/{budget_id}",
    response_model=TokenBudgetResponse,
    summary="Get budget by ID",
    description="Retrieve detailed information about a specific token budget",
    responses={
        200: {"description": "Budget retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Budget not found"},
    },
)
async def get_budget(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenBudgetResponse:
    """
    Get budget details by ID.

    Requires authentication.

    Args:
        budget_id: Budget ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Budget details
    """
    try:
        service = TokenBudgetService()
        result = await service.get_budget_status(budget_id, db)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message(result)
            )

        return TokenBudgetResponse(**get_data(result))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget: {str(e)}"
        )


@router.put(
    "/{budget_id}",
    response_model=TokenBudgetResponse,
    summary="Update budget",
    description="Update an existing token budget configuration",
    responses={
        200: {"description": "Budget updated successfully"},
        400: {"description": "Invalid input data"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Budget not found"},
    },
)
async def update_budget(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    budget_data: TokenBudgetUpdate = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenBudgetResponse:
    """
    Update budget configuration.

    Requires admin privileges.

    Args:
        budget_id: Budget ID
        budget_data: Update data
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated budget details
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Check if budget exists
        existing = await budget_repo.get_by_id(budget_id, db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Update budget
        update_data = {k: v for k, v in budget_data.model_dump().items() if v is not None}
        updated = await budget_repo.update(budget_id, update_data, db)
        await db.commit()
        await db.refresh(updated)

        logger.info(f"Updated budget {budget_id} by user {current_user.id}")
        return TokenBudgetResponse.model_validate(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update budget: {str(e)}"
        )


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete budget",
    description="Delete a token budget (cascades to child budgets)",
    responses={
        204: {"description": "Budget deleted successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Budget not found"},
    },
)
async def delete_budget(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a budget.

    Requires admin privileges.

    Args:
        budget_id: Budget ID
        current_user: Authenticated admin user
        db: Database session
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Check if budget exists
        existing = await budget_repo.get_by_id(budget_id, db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Delete budget
        await budget_repo.delete(budget_id, db)
        await db.commit()

        logger.info(f"Deleted budget {budget_id} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete budget: {str(e)}"
        )


@router.get(
    "/status/{scope}/{scope_id}",
    summary="Get budget status by scope",
    description="Get current status of budget for a specific scope",
    responses={
        200: {"description": "Budget status retrieved"},
        404: {"description": "Budget not found for scope"},
    },
)
async def get_budget_status_by_scope(
    scope: str = Path(..., description="Scope type (organization, suite, test, user)"),
    scope_id: int = Path(..., description="Scope ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get budget status for a specific scope.

    Args:
        scope: Scope type
        scope_id: Scope entity ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Budget status information
    """
    try:
        service = TokenBudgetService()
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Get budget by scope
        budget = await budget_repo.get_by_scope(scope, scope_id, db)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Budget not found for scope {scope}:{scope_id}"
            )

        # Get status
        result = await service.get_budget_status(budget.id, db)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget status for {scope}:{scope_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget status: {str(e)}"
        )


@router.get(
    "/hierarchy/{budget_id}",
    summary="Get budget hierarchy",
    description="Get budget hierarchy including parent and child budgets",
    responses={
        200: {"description": "Hierarchy retrieved successfully"},
        404: {"description": "Budget not found"},
    },
)
async def get_budget_hierarchy(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    include_children: bool = Query(True, description="Include child budgets"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get budget hierarchy.

    Args:
        budget_id: Budget ID
        include_children: Whether to include child budgets
        current_user: Authenticated user
        db: Database session

    Returns:
        Budget hierarchy data
    """
    try:
        service = TokenBudgetService()
        result = await service.get_budget_hierarchy(budget_id, db, include_children)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget hierarchy for {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget hierarchy: {str(e)}"
        )


@router.get(
    "",
    response_model=TokenBudgetListResponse,
    summary="List all budgets",
    description="List all token budgets with pagination",
    responses={
        200: {"description": "Budgets retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def list_budgets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TokenBudgetListResponse:
    """
    List all budgets with pagination and filters.

    Requires admin privileges.

    Args:
        page: Page number
        page_size: Items per page
        scope_type: Optional scope type filter
        status_filter: Optional status filter
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Paginated budget list
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Get budgets with pagination
        offset = (page - 1) * page_size

        budgets, total = await budget_repo.list_all(
            db,
            limit=page_size,
            offset=offset,
            scope_type=scope_type,
            status_filter=status_filter
        )

        total_pages = (total + page_size - 1) // page_size

        return TokenBudgetListResponse(
            items=[TokenBudgetResponse.model_validate(b) for b in budgets],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error listing budgets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list budgets: {str(e)}"
        )


@router.post(
    "/{budget_id}/check-availability",
    summary="Check token availability",
    description="Check if sufficient tokens are available for a request",
    responses={
        200: {"description": "Availability check completed"},
        404: {"description": "Budget not found"},
    },
)
async def check_token_availability(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    requested_tokens: int = Query(..., gt=0, description="Number of tokens requested"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if tokens are available for a request.

    Args:
        budget_id: Budget ID
        requested_tokens: Number of tokens requested
        current_user: Authenticated user
        db: Database session

    Returns:
        Availability check result
    """
    try:
        service = TokenBudgetService()
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Get budget
        budget = await budget_repo.get_by_id(budget_id, db)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Check availability
        result = await service.check_token_availability(
            budget.scope_type,
            budget.scope_id,
            requested_tokens,
            db
        )

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking token availability for budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check token availability: {str(e)}"
        )


@router.post(
    "/{budget_id}/reset",
    summary="Reset budget period",
    description="Reset budget period and usage counters",
    responses={
        200: {"description": "Budget reset successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Budget not found"},
    },
)
async def reset_budget(
    budget_id: int = Path(..., description="Budget ID", ge=1),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset budget period and usage.

    Requires admin privileges.

    Args:
        budget_id: Budget ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Reset result with updated budget
    """
    try:
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()

        # Check if budget exists
        budget = await budget_repo.get_by_id(budget_id, db)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Reset budget
        result = await budget_repo.reset_period(budget_id, db)
        await db.commit()
        await db.refresh(result)

        logger.info(f"Reset budget {budget_id} by user {current_user.id}")

        return {
            "budget_id": result.id,
            "message": "Budget reset successfully",
            "used_tokens": result.used_tokens,
            "remaining_tokens": result.remaining_tokens,
            "last_reset_at": result.last_reset_at.isoformat() if result.last_reset_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset budget: {str(e)}"
        )
