"""
Pytest configuration and fixtures for testing.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from app.core.database import Base
from app.main import app

# Set test mode flag to disable rate limiting
os.environ["TESTING_MODE"] = "1"


# Test database URL - use PostgreSQL for compatibility with ARRAY types
# Falls back to SQLite if PostgreSQL is not available
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cc_test_user:test_password_123@postgres:5432/cc_test_db"
)

# Alternative SQLite URL for simple schema tests
SQLITE_TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine - session scope for performance."""
    # Use NullPool for PostgreSQL to avoid connection pooling issues in tests
    pool_class = NullPool if "postgresql" in TEST_DATABASE_URL else StaticPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=pool_class,
        echo=False,  # Set to True for SQL query debugging
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Note: Skipping automatic cleanup to avoid foreign key constraint issues
    # Tests should clean up their own data or use transactions that rollback
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncSession:
    """Create test database session with automatic rollback."""
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        # Begin transaction for test isolation
        async with session.begin():
            yield session
            # Rollback transaction after test (automatic via context manager)


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncSession:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncClient:
    """Create async HTTP client for testing API endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def admin_token(async_client: AsyncClient, db_session: AsyncSession) -> str:
    """Create an admin user and return access token."""
    import time
    from sqlalchemy import select
    from app.models.user import User as UserAccount

    # Create unique user to avoid conflicts
    unique_id = int(time.time() * 1000)
    email = f"admin_{unique_id}@test.com"
    password = "Admin@123"

    # Register admin user
    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": f"admin_{unique_id}",
            "email": email,
            "password": password
        }
    )

    if register_response.status_code == 201:
        # Mark user as verified in database
        result = await db_session.execute(
            select(UserAccount).where(UserAccount.email == email.lower())
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            await db_session.commit()

    # Login to get token (use email field, not username)
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture(scope="function")
async def user_token(async_client: AsyncClient, db_session: AsyncSession) -> str:
    """Create a regular user and return access token."""
    import time
    from sqlalchemy import select
    from app.models.user import User as UserAccount

    # Create unique user to avoid conflicts
    unique_id = int(time.time() * 1000)
    email = f"user_{unique_id}@test.com"
    password = "User@123"

    # Register regular user
    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": f"user_{unique_id}",
            "email": email,
            "password": password
        }
    )

    if register_response.status_code == 201:
        # Mark user as verified in database
        result = await db_session.execute(
            select(UserAccount).where(UserAccount.email == email.lower())
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            await db_session.commit()

    # Login to get token (use email field, not username)
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    data = response.json()
    return data["access_token"]
