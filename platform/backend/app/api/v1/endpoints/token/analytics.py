"""
Token Analytics API Endpoints

Analytics and reporting for token usage, costs, and forecasts.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.core.result_helpers import is_success, is_error, get_data, get_error
from app.models.user import User
from app.services.token_budget_service import TokenBudgetService
from app.services.token_reporting_service import TokenReportingService

router = APIRouter(prefix="/analytics", tags=["token-analytics"])
logger = logging.getLogger(__name__)


@router.get(
    "/costs",
    summary="Get token costs",
    description="Retrieve token cost information and spending analysis",
    responses={
        200: {"description": "Cost data retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_token_costs(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    scope_id: Optional[int] = Query(None, description="Filter by scope ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get token cost analysis.

    Users see their own costs, admins see all costs.

    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        scope_type: Optional scope type filter
        scope_id: Optional scope ID filter
        current_user: Authenticated user
        db: Database session

    Returns:
        Token cost analysis data
    """
    try:
        reporting_service = TokenReportingService()

        # Set default date range (last 30 days)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build filters
        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }

        # Add scope filters if provided
        if scope_type:
            filters["scope_type"] = scope_type
        if scope_id:
            filters["scope_id"] = scope_id

        # For non-admin users, filter by their user_id
        if not current_user.is_admin:
            filters["user_id"] = current_user.id

        # Get cost data
        result = await reporting_service.get_cost_analysis(db, **filters)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token costs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token costs: {str(e)}"
        )


@router.get(
    "/by-scope/{scope}",
    summary="Get usage by scope",
    description="Retrieve token usage statistics grouped by scope type",
    responses={
        200: {"description": "Scope usage retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_usage_by_scope(
    scope: str = Path(..., description="Scope type (organization, suite, test, user)"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    group_by: str = Query("day", description="Grouping period (hour, day, week, month)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get token usage statistics by scope.

    Args:
        scope: Scope type to analyze
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        group_by: Grouping period for time series data
        current_user: Authenticated user
        db: Database session

    Returns:
        Usage statistics by scope
    """
    try:
        reporting_service = TokenReportingService()

        # Validate scope type
        valid_scopes = {"organization", "suite", "test", "user"}
        if scope not in valid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope type. Must be one of: {valid_scopes}"
            )

        # Set default date range (last 30 days)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get usage data
        result = await reporting_service.get_usage_by_scope(
            db,
            scope_type=scope,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage by scope {scope}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage by scope: {str(e)}"
        )


@router.get(
    "/forecasts",
    summary="Get usage forecasts",
    description="Get token usage forecasts and budget exhaustion predictions",
    responses={
        200: {"description": "Forecasts retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Budget not found"},
    },
)
async def get_usage_forecasts(
    budget_id: int = Query(..., description="Budget ID to forecast"),
    forecast_days: int = Query(30, ge=1, le=365, description="Days to forecast"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get usage forecast for a budget.

    Args:
        budget_id: Budget ID
        forecast_days: Number of days to forecast
        current_user: Authenticated user
        db: Database session

    Returns:
        Usage forecast data
    """
    try:
        budget_service = TokenBudgetService()

        # Check if budget exists and user has access
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()
        budget = await budget_repo.get_by_id(budget_id, db)

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Get forecast
        result = await budget_service.calculate_forecast(
            budget_id,
            db,
            forecast_days=forecast_days
        )

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecasts for budget {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get forecasts: {str(e)}"
        )


@router.get(
    "/trends",
    summary="Get usage trends",
    description="Analyze token usage trends over time",
    responses={
        200: {"description": "Trends retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_usage_trends(
    period: str = Query("daily", description="Analysis period (hourly, daily, weekly, monthly)"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get token usage trends over time.

    Args:
        period: Analysis period
        days_back: Number of days to analyze
        scope_type: Optional scope type filter
        current_user: Authenticated user
        db: Database session

    Returns:
        Usage trend analysis
    """
    try:
        reporting_service = TokenReportingService()

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # Build filters
        filters = {
            "start_date": start_date,
            "end_date": end_date,
            "period": period,
        }

        # Add scope filter if provided
        if scope_type:
            filters["scope_type"] = scope_type

        # For non-admin users, filter by their user_id
        if not current_user.is_admin:
            filters["user_id"] = current_user.id

        # Get trend data
        result = await reporting_service.get_usage_trends(db, **filters)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage trends: {str(e)}"
        )


@router.get(
    "/summary",
    summary="Get usage summary",
    description="Get overall token usage summary statistics",
    responses={
        200: {"description": "Summary retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_usage_summary(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get overall token usage summary.

    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        current_user: Authenticated user
        db: Database session

    Returns:
        Usage summary statistics
    """
    try:
        reporting_service = TokenReportingService()

        # Set default date range (last 30 days)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build filters
        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }

        # For non-admin users, filter by their user_id
        if not current_user.is_admin:
            filters["user_id"] = current_user.id

        # Get summary data
        result = await reporting_service.get_usage_summary(db, **filters)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.get(
    "/model-usage",
    summary="Get usage by model",
    description="Retrieve token usage statistics grouped by LLM model",
    responses={
        200: {"description": "Model usage retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_model_usage(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get token usage by LLM model.

    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        current_user: Authenticated user
        db: Database session

    Returns:
        Model usage statistics
    """
    try:
        reporting_service = TokenReportingService()

        # Set default date range (last 30 days)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build filters
        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }

        # For non-admin users, filter by their user_id
        if not current_user.is_admin:
            filters["user_id"] = current_user.id

        # Get model usage data
        result = await reporting_service.get_model_usage(db, **filters)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model usage: {str(e)}"
        )


@router.get(
    "/agent-usage",
    summary="Get usage by agent type",
    description="Retrieve token usage statistics grouped by agent type",
    responses={
        200: {"description": "Agent usage retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_agent_usage(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get token usage by agent type.

    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        current_user: Authenticated user
        db: Database session

    Returns:
        Agent usage statistics
    """
    try:
        reporting_service = TokenReportingService()

        # Set default date range (last 30 days)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build filters
        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }

        # For non-admin users, filter by their user_id
        if not current_user.is_admin:
            filters["user_id"] = current_user.id

        # Get agent usage data
        result = await reporting_service.get_agent_usage(db, **filters)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        return get_data(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent usage: {str(e)}"
        )


@router.get(
    "/budget-performance",
    summary="Get budget performance",
    description="Analyze budget performance and efficiency metrics",
    responses={
        200: {"description": "Budget performance retrieved"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_budget_performance(
    budget_id: int = Query(..., description="Budget ID to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get budget performance metrics.

    Args:
        budget_id: Budget ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Budget performance metrics
    """
    try:
        # Check if budget exists and user has access
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()
        budget = await budget_repo.get_by_id(budget_id, db)

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # Get performance data
        budget_service = TokenBudgetService()
        result = await budget_service.get_budget_status(budget_id, db)

        if is_error(result):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_message(result)
            )

        status_data = get_data(result)

        # Calculate performance metrics
        return {
            "budget_id": budget_id,
            "budget_name": status_data.get("name"),
            "performance": {
                "usage_rate": status_data.get("usage_percentage", 0),
                "remaining_percentage": round(
                    (status_data.get("remaining_tokens", 0) / status_data.get("total_tokens", 1)) * 100, 2
                ),
                "is_exhausted": status_data.get("is_exhausted", False),
                "is_near_limit": status_data.get("is_near_limit", False),
                "days_until_exhaustion": status_data.get("days_until_exhaustion"),
                "efficiency_score": round(
                    (status_data.get("used_tokens", 0) / max(status_data.get("total_tokens", 1), 1)) * 100, 2
                )
            },
            "period": {
                "start": status_data.get("period_start"),
                "end": status_data.get("period_end"),
                "days_remaining": status_data.get("days_remaining"),
            },
            "enforcement": {
                "mode": status_data.get("enforcement_mode"),
                "status": status_data.get("status"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget performance for {budget_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget performance: {str(e)}"
        )


@router.get(
    "/comparisons",
    summary="Compare budget performance",
    description="Compare multiple budgets side by side",
    responses={
        200: {"description": "Comparison retrieved successfully"},
        401: {"description": "Not authenticated"},
        400: {"description": "Invalid budget IDs"},
    },
)
async def compare_budgets(
    budget_ids: str = Query(..., description="Comma-separated budget IDs to compare"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compare multiple budgets side by side.

    Args:
        budget_ids: Comma-separated budget IDs (e.g., "1,2,3")
        current_user: Authenticated user
        db: Database session

    Returns:
        Budget comparison data
    """
    try:
        # Parse budget IDs
        try:
            ids = [int(id.strip()) for id in budget_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid budget IDs format. Use comma-separated integers."
            )

        if len(ids) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compare more than 10 budgets at once"
            )

        budget_service = TokenBudgetService()
        comparisons = []

        for budget_id in ids:
            result = await budget_service.get_budget_status(budget_id, db)

            if is_success(result):
                data = get_data(result)
                comparisons.append({
                    "budget_id": budget_id,
                    "name": data.get("name"),
                    "scope_type": data.get("scope_type"),
                    "scope_id": data.get("scope_id"),
                    "usage_percentage": data.get("usage_percentage"),
                    "total_tokens": data.get("total_tokens"),
                    "used_tokens": data.get("used_tokens"),
                    "remaining_tokens": data.get("remaining_tokens"),
                    "status": data.get("status"),
                    "enforcement_mode": data.get("enforcement_mode"),
                })

        return {
            "budgets": comparisons,
            "total_budgets": len(comparisons),
            "generated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing budgets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare budgets: {str(e)}"
        )
