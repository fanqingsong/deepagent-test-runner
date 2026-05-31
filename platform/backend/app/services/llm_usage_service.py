"""
LLM Usage Analytics Service

Handles queries for token usage tracking and analytics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class LlmUsageService:
    """Service for LLM token usage analytics."""

    async def get_usage_summary(
        self,
        db: AsyncSession,
        days: int = 30,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.models.llm_usage import LlmUsage

        start_time = datetime.utcnow() - timedelta(days=days)

        query = select(
            func.count(LlmUsage.id).label("call_count"),
            func.sum(LlmUsage.total_tokens).label("total_tokens"),
            func.sum(LlmUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(LlmUsage.completion_tokens).label("total_completion_tokens"),
            func.avg(LlmUsage.duration_ms).label("avg_duration_ms"),
        ).where(LlmUsage.created_at > start_time)

        if user_id:
            query = query.where(LlmUsage.user_id == user_id)

        result = await db.execute(query)
        row = result.first()

        return {
            "call_count": row.call_count or 0,
            "total_tokens": row.total_tokens or 0,
            "total_prompt_tokens": row.total_prompt_tokens or 0,
            "total_completion_tokens": row.total_completion_tokens or 0,
            "avg_duration_ms": int(row.avg_duration_ms) if row.avg_duration_ms else 0,
            "days": days,
        }

    async def get_usage_by_agent(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        from app.models.llm_usage import LlmUsage

        start_time = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                LlmUsage.agent_type,
                func.count(LlmUsage.id).label("call_count"),
                func.sum(LlmUsage.total_tokens).label("total_tokens"),
                func.sum(LlmUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(LlmUsage.completion_tokens).label("completion_tokens"),
                func.avg(LlmUsage.duration_ms).label("avg_duration_ms"),
            )
            .where(LlmUsage.created_at > start_time)
            .group_by(LlmUsage.agent_type)
            .order_by(func.sum(LlmUsage.total_tokens).desc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "agent_type": row.agent_type,
                "call_count": row.call_count,
                "total_tokens": row.total_tokens or 0,
                "prompt_tokens": row.prompt_tokens or 0,
                "completion_tokens": row.completion_tokens or 0,
                "avg_duration_ms": int(row.avg_duration_ms) if row.avg_duration_ms else 0,
            }
            for row in rows
        ]

    async def get_usage_by_day(
        self,
        db: AsyncSession,
        days: int = 30,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        from app.models.llm_usage import LlmUsage

        start_time = datetime.utcnow() - timedelta(days=days)

        date_col = func.date_trunc("day", LlmUsage.created_at).label("date")

        query = (
            select(
                date_col,
                func.count(LlmUsage.id).label("call_count"),
                func.sum(LlmUsage.total_tokens).label("total_tokens"),
                func.sum(LlmUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(LlmUsage.completion_tokens).label("completion_tokens"),
            )
            .where(LlmUsage.created_at > start_time)
        )

        if user_id:
            query = query.where(LlmUsage.user_id == user_id)

        query = query.group_by(date_col).order_by(date_col.desc())

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "call_count": row.call_count,
                "total_tokens": row.total_tokens or 0,
                "prompt_tokens": row.prompt_tokens or 0,
                "completion_tokens": row.completion_tokens or 0,
            }
            for row in rows
        ]

    async def get_usage_for_test_run(
        self,
        db: AsyncSession,
        test_run_id: str,
    ) -> List[Dict[str, Any]]:
        from app.models.llm_usage import LlmUsage

        query = (
            select(LlmUsage)
            .where(LlmUsage.test_run_id == test_run_id)
            .order_by(LlmUsage.created_at)
        )

        result = await db.execute(query)
        rows = list(result.scalars().all())

        return [
            {
                "id": row.id,
                "agent_type": row.agent_type,
                "model_name": row.model_name,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
                "duration_ms": row.duration_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def get_recent_usage(
        self,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        from app.models.llm_usage import LlmUsage

        query = (
            select(LlmUsage)
            .order_by(LlmUsage.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        rows = list(result.scalars().all())

        return [
            {
                "id": row.id,
                "agent_type": row.agent_type,
                "model_name": row.model_name,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
                "duration_ms": row.duration_ms,
                "user_id": row.user_id,
                "test_run_id": row.test_run_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
