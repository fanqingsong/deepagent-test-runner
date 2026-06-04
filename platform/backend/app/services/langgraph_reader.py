"""
LangGraph Conversation Reader

Reads conversation data from the running LangGraph Platform Server
via the LangGraph SDK sync client. The server runs in in-memory mode,
so we query it directly rather than reading from the database.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from jose import jwt
from langgraph_sdk import get_sync_client

from app.core.config import settings

logger = logging.getLogger(__name__)

LANGGRAPH_URL = "http://langgraph-server:2024"
JWT_SECRET = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"


def _make_server_token() -> str:
    """Generate a server-to-server JWT for querying the LangGraph server."""
    return jwt.encode({"sub": "0", "scope": "server"}, JWT_SECRET, algorithm=ALGORITHM)


def _get_client():
    return get_sync_client(
        url=LANGGRAPH_URL,
        headers={"Authorization": f"Bearer {_make_server_token()}"},
    )


class LangGraphReader:
    """Reads conversation data from the LangGraph Platform Server via SDK."""

    async def list_threads(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List threads from the running LangGraph server."""
        def _sync():
            client = _get_client()
            return client.threads.search(limit=200)

        try:
            threads = await asyncio.to_thread(_sync)
        except Exception:
            logger.warning("Failed to list threads from LangGraph server", exc_info=True)
            return {"total": 0, "offset": offset, "limit": limit, "items": []}

        items = []
        for t in threads:
            meta = t.get("metadata") or {}
            tid = t.get("thread_id")
            created = t.get("created_at")
            updated = t.get("updated_at")
            title = meta.get("title")
            t_user_id = meta.get("user_id")

            if user_id and str(t_user_id) != str(user_id):
                continue

            items.append({
                "thread_id": tid,
                "user_id": t_user_id,
                "title": title,
                "status": self._derive_status(updated),
                "message_count": 0,
                "last_message_at": updated,
                "subagents_used": [],
                "total_tokens": 0,
                "created_at": created,
            })

        total = len(items)
        paginated = items[offset:offset + limit]
        return {"total": total, "offset": offset, "limit": limit, "items": paginated}

    async def get_thread_messages(
        self,
        thread_id: str,
    ) -> List[Dict[str, Any]]:
        """Get message history for a thread from the LangGraph server."""
        def _sync():
            client = _get_client()
            state = client.threads.get_state(thread_id)
            return state

        try:
            state = await asyncio.to_thread(_sync)
        except Exception:
            logger.warning("Failed to get state for thread %s", thread_id, exc_info=True)
            return []

        values = state.get("values", {})
        messages = values.get("messages", [])
        return self._format_messages(messages)

    @staticmethod
    def _derive_status(updated_at) -> str:
        if not updated_at:
            return "idle"
        from datetime import datetime, timedelta
        try:
            if isinstance(updated_at, str):
                updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                updated = updated_at if getattr(updated_at, "tzinfo", None) is None else updated_at.replace(tzinfo=None)
        except Exception:
            return "idle"
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        return "active" if updated > cutoff else "idle"

    async def get_session_metrics(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Aggregated metrics from the LangGraph server."""
        data = await self.list_threads(limit=200)
        total_sessions = data["total"]
        active_count = sum(1 for item in data["items"] if item["status"] == "active")
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_count,
            "total_messages": 0,
            "total_tokens": 0,
            "days": days,
        }

    def _format_messages(self, messages: list) -> List[Dict[str, Any]]:
        """Format message dicts from LangGraph state into API response format."""
        formatted = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            entry = {
                "role": msg.get("type", msg.get("role", "unknown")),
                "content": msg.get("content", ""),
            }
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                entry["tool_calls"] = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {})}
                    for tc in tool_calls
                ]
            name = msg.get("name")
            if name:
                entry["name"] = name
            formatted.append(entry)
        return formatted


langgraph_reader = LangGraphReader()
