"""
Repository Tests Configuration

Pytest fixtures and configuration for repository tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.test_run import TestRun
from app.core.database import Base


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create in-memory database session for testing.

    Creates all tables before test and drops them after.
    """
    # Create test engine
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    # Create session factory
    test_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with test_session_maker() as session:
        yield session

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
def sample_test_run_data():
    """Sample test run data for testing."""
    from datetime import datetime

    return {
        'run_id': 'test-run-123',
        'test_definition_id': 100,
        'status': 'pending',
        'start_time': int(datetime.utcnow().timestamp() * 1000),
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }


@pytest.fixture
async def sample_test_run(test_db_session):
    """Create sample test run in database."""
    from datetime import datetime

    test_run = TestRun(
        run_id='test-run-123',
        test_definition_id=100,
        status='pending',
        start_time=int(datetime.utcnow().timestamp() * 1000),
        total_tests=0,
        passed=0,
        failed=0,
        skipped=0
    )

    test_db_session.add(test_run)
    await test_db_session.commit()
    await test_db_session.refresh(test_run)

    return test_run
