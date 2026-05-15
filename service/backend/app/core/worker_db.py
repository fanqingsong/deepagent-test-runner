"""
Async database helpers for Celery workers.

Uses the shared SQLAlchemy engine from app.core.database to avoid
creating a new connection pool per task.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker

T = TypeVar("T")


async def run_with_session(coro: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run an async callable with a fresh DB session."""
    async with async_session_maker() as session:
        return await coro(session)


def run_async(coro: Callable[[], Awaitable[T]]) -> T:
    """Run async code from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro())
    finally:
        loop.close()
