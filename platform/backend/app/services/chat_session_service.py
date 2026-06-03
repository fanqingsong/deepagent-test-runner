"""
Chat Session Service

Admin-facing queries for monitoring chat sessions.
Handles session lifecycle tracking and aggregated metrics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class ChatSessionService:
    """Service for admin chat session monitoring."""

    # --- Session lifecycle (called by tracking callback) ---

    async def upsert_session(
        self,
        db: AsyncSession,
        thread_id: str,
        user_id: int,
        title: str = None,
    ) -> None:
        from app.models.chat_session import ChatSession

        stmt = insert(ChatSession).values(
            langgraph_thread_id=thread_id,
            user_id=user_id,
            title=title,
            message_count=1,
            last_message_at=datetime.utcnow(),
            status="active",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["langgraph_thread_id"],
            set_={
                "last_message_at": datetime.utcnow(),
                "status": "active",
                "updated_at": datetime.utcnow(),
            },
        )
        await db.execute(stmt)
        await db.commit()

    async def record_subagent(
        self,
        db: AsyncSession,
        thread_id: str,
        subagent_name: str,
    ) -> None:
        from app.models.chat_session import ChatSession

        result = await db.execute(
            select(ChatSession.subagents_used).where(
                ChatSession.langgraph_thread_id == thread_id
            )
        )
        row = result.first()
        if not row:
            return

        existing = row.subagents_used or []
        if subagent_name not in existing:
            existing.append(subagent_name)
            await db.execute(
                update(ChatSession)
                .where(ChatSession.langgraph_thread_id == thread_id)
                .values(subagents_used=existing, updated_at=datetime.utcnow())
            )
            await db.commit()

    # --- Admin query methods ---

    async def list_active_sessions(
        self,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        from app.models.chat_session import ChatSession

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        query = (
            select(ChatSession)
            .where(
                ChatSession.status == "active",
                ChatSession.last_message_at > cutoff,
            )
            .order_by(ChatSession.last_message_at.desc())
        )
        result = await db.execute(query)
        sessions = list(result.scalars().all())

        return [
            {
                "thread_id": s.langgraph_thread_id,
                "user_id": s.user_id,
                "title": s.title,
                "status": s.status,
                "message_count": s.message_count,
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                "subagents_used": s.subagents_used or [],
                "total_tokens": s.total_tokens,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ]

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        from app.models.chat_session import ChatSession

        query = select(ChatSession)
        count_query = select(func.count(ChatSession.id))

        if user_id:
            query = query.where(ChatSession.user_id == user_id)
            count_query = count_query.where(ChatSession.user_id == user_id)
        if status:
            query = query.where(ChatSession.status == status)
            count_query = count_query.where(ChatSession.status == status)

        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        sessions = list(result.scalars().all())

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "thread_id": s.langgraph_thread_id,
                    "user_id": s.user_id,
                    "title": s.title,
                    "status": s.status,
                    "message_count": s.message_count,
                    "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                    "subagents_used": s.subagents_used or [],
                    "total_tokens": s.total_tokens,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sessions
            ],
        }

    async def get_session_detail(
        self,
        db: AsyncSession,
        thread_id: str,
    ) -> Optional[Dict[str, Any]]:
        from app.models.chat_session import ChatSession

        result = await db.execute(
            select(ChatSession).where(
                ChatSession.langgraph_thread_id == thread_id
            )
        )
        s = result.scalar_one_or_none()
        if not s:
            return None

        return {
            "thread_id": s.langgraph_thread_id,
            "user_id": s.user_id,
            "title": s.title,
            "status": s.status,
            "message_count": s.message_count,
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "subagents_used": s.subagents_used or [],
            "total_tokens": s.total_tokens,
            "total_duration_ms": s.total_duration_ms,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }

    async def get_session_metrics(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> Dict[str, Any]:
        from app.models.chat_session import ChatSession

        start = datetime.utcnow() - timedelta(days=days)
        cutoff = datetime.utcnow() - timedelta(minutes=5)

        stats_query = select(
            func.count(ChatSession.id).label("total_sessions"),
            func.sum(ChatSession.message_count).label("total_messages"),
            func.sum(ChatSession.total_tokens).label("total_tokens"),
            func.avg(ChatSession.message_count).label("avg_messages"),
        ).where(ChatSession.created_at > start)

        row = (await db.execute(stats_query)).first()

        active_query = select(func.count(ChatSession.id)).where(
            ChatSession.status == "active",
            ChatSession.last_message_at > cutoff,
        )
        active_count = (await db.execute(active_query)).scalar() or 0

        return {
            "total_sessions": row.total_sessions or 0,
            "active_sessions": active_count,
            "total_messages": row.total_messages or 0,
            "avg_messages_per_session": round(float(row.avg_messages or 0), 1),
            "total_tokens": row.total_tokens or 0,
            "days": days,
        }

    async def get_subagent_usage(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        from app.models.llm_usage import LlmUsage

        start = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                LlmUsage.agent_type,
                func.count(LlmUsage.id).label("call_count"),
                func.sum(LlmUsage.total_tokens).label("total_tokens"),
                func.avg(LlmUsage.duration_ms).label("avg_duration_ms"),
            )
            .where(LlmUsage.created_at > start)
            .where(LlmUsage.thread_id.isnot(None))
            .group_by(LlmUsage.agent_type)
            .order_by(func.count(LlmUsage.id).desc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "subagent_name": row.agent_type,
                "call_count": row.call_count,
                "total_tokens": row.total_tokens or 0,
                "avg_duration_ms": int(row.avg_duration_ms) if row.avg_duration_ms else 0,
            }
            for row in rows
        ]


chat_session_service = ChatSessionService()
