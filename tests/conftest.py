"""
Main Test Configuration

Pytest fixtures and configuration for all tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert


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
async def test_user(test_db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    return user


@pytest.fixture
async def test_admin_user(test_db_session: AsyncSession) -> User:
    """Create test admin user."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=True
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    return user


@pytest.fixture
def sample_token_budget_data():
    """Sample token budget data for testing."""
    return {
        'name': 'Test Budget',
        'description': 'Test budget description',
        'scope_type': 'organization',
        'scope_id': None,
        'parent_budget_id': None,
        'period_type': 'monthly',
        'period_start': datetime.utcnow(),
        'period_end': None,
        'total_tokens': 1000000,
        'priority': 5,
        'enforcement_mode': 'soft',
        'status': 'active',
        'inherit_from_parent': False,
        'inherit_strategy': None,
        'alert_thresholds': {
            'warning': 80,
            'critical': 90,
            'emergency': 95
        },
        'config_data': {}
    }


@pytest.fixture
async def sample_token_budget(test_db_session: AsyncSession, sample_token_budget_data: dict) -> TokenBudget:
    """Create sample token budget in database."""
    budget = TokenBudget(**sample_token_budget_data)
    budget.remaining_tokens = budget.total_tokens

    test_db_session.add(budget)
    await test_db_session.commit()
    await test_db_session.refresh(budget)

    return budget


@pytest.fixture
def sample_token_quota_data(test_user: User):
    """Sample token quota data for testing."""
    return {
        'user_id': test_user.id,
        'name': 'Daily Quota',
        'description': 'Daily token quota',
        'period_type': 'daily',
        'reset_strategy': 'calendar',
        'period_start': datetime.utcnow(),
        'period_end': None,
        'total_tokens': 100000,
        'priority': 5,
        'enforcement_mode': 'soft',
        'status': 'active',
        'alert_thresholds': {
            'warning': 80,
            'critical': 90,
            'emergency': 95
        },
        'config_data': {}
    }


@pytest.fixture
async def sample_token_quota(test_db_session: AsyncSession, sample_token_quota_data: dict) -> TokenQuota:
    """Create sample token quota in database."""
    quota = TokenQuota(**sample_token_quota_data)
    quota.remaining_tokens = quota.total_tokens

    test_db_session.add(quota)
    await test_db_session.commit()
    await test_db_session.refresh(quota)

    return quota


@pytest.fixture
def sample_token_alert_data(sample_token_budget: TokenBudget):
    """Sample token alert data for testing."""
    return {
        'alert_type': 'budget_warning',
        'severity': 'warning',
        'budget_id': sample_token_budget.id,
        'quota_id': None,
        'user_id': None,
        'threshold_type': 'percentage',
        'threshold_value': 80.0,
        'current_value': 85.0,
        'metrics_snapshot': {
            'used_tokens': 850000,
            'total_tokens': 1000000,
            'usage_percentage': 85.0
        },
        'message': 'Budget usage exceeded 80% threshold',
        'details': {},
        'enforcement_action': None,
        'enforcement_result': {}
    }


@pytest.fixture
async def sample_token_alert(test_db_session: AsyncSession, sample_token_alert_data: dict) -> TokenAlert:
    """Create sample token alert in database."""
    alert = TokenAlert(**sample_token_alert_data)

    test_db_session.add(alert)
    await test_db_session.commit()
    await test_db_session.refresh(alert)

    return alert
