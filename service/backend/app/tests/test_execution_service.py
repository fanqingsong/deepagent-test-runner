import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.execution_service import ExecutionService
from app.models.schedule import Schedule
from app.models.test_suite import TestSuite


@pytest.mark.asyncio
async def test_resolve_single_test(db_session: AsyncSession):
    """Test resolving single test type"""
    schedule = Schedule(
        name="Single Test",
        schedule_type="single",
        test_definition_ids=[5],  # Use array field as per schema
        test_definition_id=5,   # Keep legacy field for compatibility
        cron_expression="0 9 * * *"
    )

    service = ExecutionService(db_session)
    test_ids = await service.resolve_target_tests(schedule, db_session)

    assert test_ids == [5]


@pytest.mark.asyncio
async def test_resolve_suite_tests(db_session: AsyncSession):
    """Test resolving suite test type"""
    # Create test suite
    suite = TestSuite(
        name="Test Suite",
        test_definition_ids=[1, 2, 3]
    )

    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    # Create schedule for suite
    schedule = Schedule(
        name="Suite Schedule",
        schedule_type="suite",
        test_definition_ids=[],  # Empty array for suite type
        test_suite_id=suite.id,
        cron_expression="0 9 * * *"
    )

    service = ExecutionService(db_session)
    test_ids = await service.resolve_target_tests(schedule, db_session)

    assert test_ids == [1, 2, 3]


@pytest.mark.asyncio
async def test_check_execution_limit_allow_concurrent(db_session: AsyncSession):
    """Test execution check with concurrent allowed"""
    schedule = Schedule(
        name="Concurrent Test",
        schedule_type="single",
        test_definition_ids=[1],  # Use array field
        cron_expression="0 9 * * *",
        allow_concurrent=True
    )

    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)

    service = ExecutionService(db_session)
    result = await service.check_execution_limit(schedule, db_session)

    assert result is True


@pytest.mark.asyncio
async def test_build_environment_merge(db_session: AsyncSession):
    """Test environment configuration merging"""
    schedule = Schedule(
        name="Test",
        schedule_type="single",
        test_definition_id=1,
        cron_expression="0 9 * * *",
        environment_overrides={
            "BASE_URL": "https://staging.example.com",
            "TIMEOUT": "30"
        }
    )

    service = ExecutionService(db_session)
    test_env = {"BASE_URL": "https://dev.example.com", "DEBUG": "false"}

    merged = service.build_environment(schedule, test_env)

    assert merged["BASE_URL"] == "https://staging.example.com"  # Overridden
    assert merged["DEBUG"] == "false"  # From base
    assert merged["TIMEOUT"] == "30"  # From override


@pytest.mark.asyncio
async def test_create_test_run(db_session: AsyncSession):
    """Test creating a test run"""
    import time
    service = ExecutionService(db_session)

    test_run = await service.create_test_run(
        run_id=f"test_run_{int(time.time()*1000)}",  # Unique run_id
        test_definition_ids=[1],
        environment={},
        db=db_session,
        schedule_id=1
    )

    assert test_run.id is not None
    assert test_run.status == "pending"


@pytest.mark.asyncio
async def test_update_run_status_valid_transition(db_session: AsyncSession):
    """Test valid status transition"""
    import time
    service = ExecutionService(db_session)

    # Create test run
    run_id = f"test_run_{int(time.time()*1000)}"
    test_run = await service.create_test_run(
        run_id=run_id,
        test_definition_ids=[1],
        environment={},
        db=db_session,
        schedule_id=1
    )

    # Update to running (convert datetime to milliseconds for database)
    from datetime import datetime
    start_time_ms = int(datetime.utcnow().timestamp() * 1000)
    updated = await service.update_run_status(run_id, "running", start_time=start_time_ms)

    assert updated.status == "running"
    assert updated.start_time is not None


@pytest.mark.asyncio
async def test_update_run_status_invalid_transition(db_session: AsyncSession):
    """Test invalid status transition"""
    import time
    service = ExecutionService(db_session)

    # Create test run with unique run_id
    run_id = f"test_run_{int(time.time()*1000)}"
    test_run = await service.create_test_run(
        run_id=run_id,
        test_definition_ids=[1],
        environment={},
        db=db_session,
        schedule_id=1
    )

    # Try invalid transition: pending -> passed
    with pytest.raises(ValueError, match="Invalid status transition"):
        await service.update_run_status(run_id, "passed")
