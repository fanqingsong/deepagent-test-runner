"""
Async database helpers for Temporal workers.

Temporal workers run in a persistent event loop, so they use a global engine.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Module-level session maker — set by Temporal worker initialization.
_active_session_maker: async_sessionmaker | None = None


def _get_session_maker() -> async_sessionmaker:
    if _active_session_maker is None:
        raise RuntimeError("No active session maker. Call set_temporal_session_maker() first.")
    return _active_session_maker


def set_temporal_session_maker(session_maker: async_sessionmaker) -> None:
    """Set the global session maker for Temporal workers.

    This should be called once when the Temporal worker starts up.
    """
    global _active_session_maker
    _active_session_maker = session_maker


async def run_with_session(coro: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run an async callable with a fresh DB session from the active maker."""
    maker = _get_session_maker()
    async with maker() as session:
        return await coro(session)
