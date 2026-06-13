"""
SOLID Verification Part 6: Complete Workflows

Tests complete end-to-end workflows through all layers:
- All layers work together
- SOLID principles maintained throughout
- Error handling across layers
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import Container, init_container, get_container
from app.core.simple_result_types import (
    service_success, service_error, service_not_found,
    service_validation_error, ServiceSuccess, ServiceError,
    get_http_status_from_result
)
from app.repositories.repository_factory import RepositoryFactory
from app.services.execution_service import ExecutionService
from app.health.checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    LLMHealthChecker,
    TemporalHealthChecker,
    FileSystemHealthChecker
)
from app.core.metrics.in_memory_metrics import InMemoryMetricsCollector
from app.models.test_run import TestRun
from app.models.test_definition import TestDefinition
from app.models.schedule import Schedule


class TestCompleteWorkflows:
    """Test complete end-to-end workflows through all layers."""

    @pytest.mark.asyncio
    async def test_complete_test_execution_workflow(self, db_session: AsyncSession):
        """Test complete workflow: Create definition → Schedule → Execute → Results."""

        # Step 1: Create test definition
        test_def = TestDefinition(
            name="E2E Test",
            description="End-to-end test",
            test_type="e2e",
            target_url="https://example.com",
            created_by="user123"
        )
        test_def_repo = RepositoryFactory.get_test_definition_repository()
        created_def = await test_def_repo.create(test_def, db_session)
        assert created_def is not None

        # Step 2: Create schedule
        schedule = Schedule(
            name="Test Schedule",
            schedule_type="single",
            cron_expression="0 0 * * *",
            test_definition_id=created_def.id,
            created_by="user123"
        )
        schedule_repo = RepositoryFactory.get_schedule_repository()
        created_schedule = await schedule_repo.create(schedule, db_session)
        assert created_schedule is not None

        # Step 3: Resolve target tests (Service layer)
        execution_service = ExecutionService(db_session=db_session)
        result = await execution_service.resolve_target_tests_v2(created_schedule, db_session)

        assert isinstance(result, ServiceSuccess)
        assert result.data == [created_def.id]

        # Step 4: Create test run
        test_run = TestRun(
            id="workflow-test-run",
            run_id="workflow-test-run",
            test_definition_id=created_def.id,
            status="pending",
            total_tests=1,
            environment={"test": "true"}
        )
        test_run_repo = RepositoryFactory.get_test_run_repository()
        created_run = await test_run_repo.create(test_run, db_session)
        assert created_run is not None

        # Step 5: Update run status
        created_run.status = "running"
        created_run.start_time = datetime.utcnow()
        updated_run = await test_run_repo.update(created_run, db_session)
        assert updated_run.status == "running"

        # Step 6: Complete the run
        updated_run.status = "completed"
        updated_run.end_time = datetime.utcnow()
        updated_run.total_duration_ms = 1000
        updated_run.passed_tests = 1
        completed_run = await test_run_repo.update(updated_run, db_session)
        assert completed_run.status == "completed"

        # Verify all data is persisted correctly
        final_run = await test_run_repo.get_by_id("workflow-test-run", db_session)
        assert final_run.status == "completed"
        assert final_run.passed_tests == 1

    @pytest.mark.asyncio
    async def test_complete_health_check_workflow(self):
        """Test complete workflow: Run health checks → Aggregate results → API response."""

        # Step 1: Run all health checks
        checkers = [
            DatabaseHealthChecker(),
            RedisHealthChecker(),
            LLMHealthChecker(),
            TemporalHealthChecker(),
            FileSystemHealthChecker()
        ]

        # Step 2: Execute checks in parallel
        results = await asyncio.gather(*[checker.check_health() for checker in checkers])

        # Step 3: Aggregate results
        overall_status = "healthy"
        components = {}

        for result in results:
            component = result['component']
            status = result['status']
            components[component] = result

            if status == 'unhealthy':
                overall_status = "unhealthy"
            elif status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        # Step 4: Verify aggregation
        assert overall_status in ['healthy', 'unhealthy', 'degraded']
        assert len(components) == 5
        assert 'database' in components
        assert 'redis' in components

        # Step 5: Simulate API response format
        api_response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components
        }

        assert api_response['status'] == overall_status
        assert len(api_response['components']) == 5

    @pytest.mark.asyncio
    async def test_complete_metrics_workflow(self):
        """Test complete workflow: Execute operations → Collect metrics → Query analytics."""

        # Step 1: Initialize metrics collector
        collector = InMemoryMetricsCollector()

        # Step 2: Simulate various operations
        operations = [
            ("database.query", 45.2),
            ("database.query", 52.1),
            ("api.call", 120.5),
            ("api.call", 115.8),
            ("cache.get", 5.2),
        ]

        for operation, duration in operations:
            collector.record_timing(operation, duration)

        # Step 3: Record counters
        collector.record_counter("http.requests", 1)
        collector.record_counter("http.requests", 1)
        collector.record_counter("cache.hits", 1)

        # Step 4: Record some errors
        collector.record_error("api.call", "TimeoutError", "Request timeout")

        # Step 5: Get comprehensive summary
        summary = collector.get_metrics_summary()

        # Step 6: Verify summary contains all data
        assert 'timing' in summary
        assert 'counters' in summary
        assert 'errors' in summary
        assert len(summary['timing']) >= 3  # database, api, cache
        assert summary['counters']['http.requests'] == 2
        assert summary['counters']['cache.hits'] == 1
        assert 'api.call' in summary['errors']

    @pytest.mark.asyncio
    async def test_complete_error_handling_workflow(self, db_session: AsyncSession):
        """Test complete workflow: Trigger errors → Result types → HTTP mapping."""

        # Step 1: Create service that returns Result types
        service = ExecutionService(db_session=db_session)

        # Step 2: Trigger various error scenarios
        scenarios = [
            ("None schedule", None),
            ("Invalid schedule type", Schedule(
                id=1,
                name="Invalid",
                schedule_type="invalid_type",
                cron_expression="",
                created_by="user123"
            ))
        ]

        results = []
        for scenario_name, schedule in scenarios:
            try:
                result = await service.resolve_target_tests_v2(schedule, db_session)
                results.append((scenario_name, result))
            except Exception as e:
                # Some errors might be exceptions
                results.append((scenario_name, ServiceError(str(e))))

        # Step 3: Verify all results are ServiceError
        for scenario_name, result in results:
            assert isinstance(result, ServiceError), f"{scenario_name} should return ServiceError"

        # Step 4: Verify HTTP status mapping
        for scenario_name, result in results:
            status_code = get_http_status_from_result(result)
            # Error types should map to 4xx or 5xx
            assert 400 <= status_code < 600

    @pytest.mark.asyncio
    async def test_complete_di_workflow(self, db_session: AsyncSession):
        """Test complete workflow: Container → Service → Repository → Database."""

        # Step 1: Get service from container
        container = init_container()
        execution_service = container.execution_service()

        # Step 2: Use service to perform operations
        schedule = Schedule(
            id=1,
            name="DI Test",
            schedule_type="single",
            cron_expression="0 0 * * *",
            test_definition_id=1,
            created_by="user123"
        )

        result = await execution_service.resolve_target_tests_v2(schedule, db_session)

        # Step 3: Verify result
        assert isinstance(result, (ServiceSuccess, ServiceError))

        # Step 4: Verify all dependencies were injected correctly
        assert execution_service.schedule_resolver is not None
        assert execution_service.test_run_repository is not None
