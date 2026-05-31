"""
Database session management for Temporal workers.

Temporal workers run in a persistent event loop, so we maintain
a global database engine and session maker for the worker lifetime.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator

from app.core.config import settings

# Global engine and session maker for Temporal workers
_engine = None
_session_maker = None


def get_worker_engine():
    """Get or create the global worker database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_worker_session_maker() -> async_sessionmaker:
    """Get or create the global worker session maker."""
    global _session_maker
    if _session_maker is None:
        engine = get_worker_engine()
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


async def get_worker_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for use in Temporal activities.

    Usage:
        async with get_worker_session() as session:
            # use session here
            pass
    """
    session_maker = get_worker_session_maker()
    async with session_maker() as session:
        yield session


async def close_worker_engine():
    """Close the global worker database engine."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None
