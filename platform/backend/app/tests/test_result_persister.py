"""
Unit tests for ResultPersister service
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.result_persister import ResultPersister
from app.services.execution_service import ExecutionService


@pytest.mark.asyncio
async def test_result_persister_save_test_results(db_session: AsyncSession):
    """Test ResultPersister saves test results correctly"""
    import time

    # Create a test run first
    service = ExecutionService(db_session)
    run_id = f"test_run_persister_{int(time.time() * 1000)}"
    test_run = await service.create_test_run(
        run_id=run_id,
        test_definition_ids=[1],
        environment={},
        db=db_session,
        schedule_id=1,
    )

    # Use ResultPersister to save results
    persister = ResultPersister(db_session)

    saved_run = await persister.save_test_results(
        run_id=run_id,
        total_tests=5,
        passed_tests=3,
        failed_tests=2,
        skipped_tests=0,
        total_duration_ms=10000,
        test_definition_id=1,
        status="failed",
        error_message="Some tests failed",
        start_time_ms=int(datetime.utcnow().timestamp() * 1000) - 10000,
        end_time_ms=int(datetime.utcnow().timestamp() * 1000),
        test_results=[
            {
                "description": "Test step 1",
                "status": "passed",
                "duration": 1000,
                "error": None,
            },
            {
                "description": "Test step 2",
                "status": "failed",
                "duration": 2000,
                "error": "Assertion failed",
            },
        ],
        db=db_session
    )

    # Verify the results were saved correctly
    assert saved_run is not None
    assert saved_run.run_id == run_id
    assert saved_run.status == "failed"
    assert saved_run.total_tests == 5
    assert saved_run.passed == 3
    assert saved_run.failed == 2
    assert saved_run.skipped == 0
    assert saved_run.error_message == "Some tests failed"
    assert saved_run.total_duration == 10  # 10000ms / 1000 = 10s


@pytest.mark.asyncio
async def test_result_persister_via_execution_service(db_session: AsyncSession):
    """Test ExecutionService delegates to ResultPersister correctly"""
    import time

    service = ExecutionService(db_session)
    run_id = f"test_run_delegate_{int(time.time() * 1000)}"
    await service.create_test_run(
        run_id=run_id,
        test_definition_ids=[2],
        environment={},
        db=db_session,
        schedule_id=1,
    )

    # Save results via ExecutionService (should delegate to ResultPersister)
    saved_run = await service.save_test_results(
        run_id,
        {
            "test_definition_id": "2",  # Test string to int conversion
            "status": "passed",
            "total_tests": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0,
            "total_duration": 5000,
            "start_time": int(datetime.utcnow().timestamp() * 1000) - 5000,
            "end_time": int(datetime.utcnow().timestamp() * 1000),
            "test_cases": [
                {
                    "description": "Step 1",
                    "status": "passed",
                    "duration": 1000,
                },
                {
                    "description": "Step 2",
                    "status": "passed",
                    "duration": 1000,
                },
            ],
        }
    )

    # Verify delegation worked correctly
    assert saved_run is not None
    assert saved_run.status == "passed"
    assert saved_run.total_tests == 3
    assert saved_run.passed == 3
    assert saved_run.failed == 0
    assert saved_run.test_definition_id == 2  # Should be converted from string
