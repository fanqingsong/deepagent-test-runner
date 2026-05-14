import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.models.schedule import Schedule
from app.models.test_run import TestRun


@pytest.mark.asyncio
async def test_create_test_suite(db_session: AsyncSession):
    """Test creating a test suite"""
    suite = TestSuite(
        name="Regression Suite",
        description="Core regression tests",
        test_definition_ids=[1, 2, 3],
        tags={"category": "regression"}
    )

    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    assert suite.id is not None
    assert suite.name == "Regression Suite"
    assert len(suite.test_definition_ids) == 3
    assert suite.tags["category"] == "regression"
    assert suite.created_at is not None


@pytest.mark.asyncio
async def test_test_suite_repr(db_session: AsyncSession):
    """Test TestSuite __repr__ method"""
    suite = TestSuite(
        name="Test Suite",
        test_definition_ids=[1, 2]
    )

    db_session.add(suite)
    await db_session.commit()

    repr_str = repr(suite)
    assert "TestSuite" in repr_str
    assert "Test Suite" in repr_str


@pytest.mark.asyncio
async def test_create_schedule(db_session: AsyncSession):
    """Test creating a schedule"""
    schedule = Schedule(
        name="Daily Regression",
        schedule_type="single",
        test_definition_ids=[1],  # Use array field instead of single ID
        cron_expression="0 9 * * *",
        timezone="UTC",
        is_active=True,
        allow_concurrent=False,
        max_retries=2
    )

    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)

    assert schedule.id is not None
    assert schedule.name == "Daily Regression"
    assert schedule.schedule_type == "single"
    assert schedule.test_definition_ids == [1]
    assert schedule.cron_expression == "0 9 * * *"
    assert schedule.is_active is True
    assert schedule.max_retries == 2


@pytest.mark.asyncio
async def test_schedule_suite_type(db_session: AsyncSession):
    """Test schedule with suite type"""
    schedule = Schedule(
        name="Weekly Suite Run",
        schedule_type="suite",
        test_definition_ids=[],  # Empty array for suite type
        test_suite_id=1,
        cron_expression="0 9 * * 1",
        environment_overrides={"BASE_URL": "https://staging.example.com"}
    )

    db_session.add(schedule)
    await db_session.commit()

    assert schedule.schedule_type == "suite"
    assert schedule.test_definition_ids == []
    assert schedule.environment_overrides["BASE_URL"] == "https://staging.example.com"


@pytest.mark.asyncio
async def test_create_test_run(db_session: AsyncSession):
    """Test creating a test run"""
    import time
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    run = TestRun(
        test_definition_id=1,
        run_id=f"test_run_{int(time.time())}",  # Unique ID for each test run
        status="passed",
        start_time=now_ms,
        end_time=now_ms + 45000,
        total_duration=45000,
        total_tests=10,
        passed=10,
        failed=0,
        skipped=0
    )

    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    assert run.id is not None
    assert run.status == "passed"
    assert run.total_tests == 10
    assert run.passed == 10
    assert run.total_duration == 45000
    await db_session.commit()
    await db_session.refresh(run)

    assert run.id is not None
    assert run.status == "passed"
    assert run.total_tests == 10
    assert run.passed == 10
    assert run.failed == 0


@pytest.mark.asyncio
async def test_test_run_with_failure(db_session: AsyncSession):
    """Test test run with failure details"""
    import time
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    run = TestRun(
        test_definition_id=1,
        run_id=f"failed_run_{int(time.time())}",  # Unique ID for each test run
        status="failed",
        start_time=now_ms,
        end_time=now_ms + 30000,
        total_duration=30000,
        total_tests=2,
        passed=1,
        failed=1,
        skipped=0,
        error_message="Element not found: #submit-button"
    )

    db_session.add(run)
    await db_session.commit()

    assert run.status == "failed"
    assert run.failed == 1
    assert run.error_message == "Element not found: #submit-button"
    assert run.error_message is not None


