"""
Async database helpers for Celery workers.

Each Celery task runs in its own event loop. To avoid asyncpg connections
being bound to a stale loop, we create a temporary engine per task invocation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Module-level session maker — set by run_async before each task invocation.
_active_session_maker: async_sessionmaker | None = None


def _get_session_maker() -> async_sessionmaker:
    if _active_session_maker is None:
        raise RuntimeError("No active session maker. Call run_async() first.")
    return _active_session_maker


async def run_with_session(coro: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run an async callable with a fresh DB session from the active maker."""
    maker = _get_session_maker()
    async with maker() as session:
        return await coro(session)


def run_async(coro: Callable[[], Awaitable[T]]) -> T:
    """Run async code from a synchronous Celery task.

    Creates a fresh event loop AND a temporary engine per call, so asyncpg
    connections are never shared across different event loops.
    """
    global _active_session_maker

    loop = asyncio.new_event_loop()
    tmp_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _active_session_maker = async_sessionmaker(
        tmp_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro())
    finally:
        # Clean up temporary engine and event loop
        try:
            loop.run_until_complete(tmp_engine.dispose())
        except Exception:
            logger.debug("Could not dispose temporary engine")

        # Cancel any remaining tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )

        loop.close()
        asyncio.set_event_loop(None)
        _active_session_maker = None
