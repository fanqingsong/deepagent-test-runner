"""
LLM Usage Analytics API Endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.llm_usage_service import LlmUsageService

router = APIRouter()
llm_usage_service = LlmUsageService()


@router.get("/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.is_admin or current_user.has_role("admin")
    user_id = None if is_admin else current_user.id

    return await llm_usage_service.get_usage_summary(db=db, days=days, user_id=user_id)


@router.get("/by-agent")
async def get_usage_by_agent(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await llm_usage_service.get_usage_by_agent(db=db, days=days)


@router.get("/by-day")
async def get_usage_by_day(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.is_admin or current_user.has_role("admin")
    user_id = None if is_admin else current_user.id

    return await llm_usage_service.get_usage_by_day(db=db, days=days, user_id=user_id)


@router.get("/test-run/{test_run_id}")
async def get_usage_for_test_run(
    test_run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await llm_usage_service.get_usage_for_test_run(db=db, test_run_id=test_run_id)


@router.get("/recent")
async def get_recent_usage(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await llm_usage_service.get_recent_usage(db=db, limit=limit)
