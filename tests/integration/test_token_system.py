"""
Token System Integration Tests

Comprehensive integration tests for the complete token limitation system:
- Complete token lifecycle
- Budget exhaustion scenarios
- Quota reset scenarios
- Alert generation and notification
- Multi-user scenarios
- Concurrent operations
- Performance under load
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.services.token_alert_service import TokenAlertService
from app.services.token_reporting_service import TokenReportingService
from app.core.result_helpers import is_success, is_error


class TestCompleteTokenLifecycle:
    """Test suite for complete token lifecycle."""

    @pytest.mark.asyncio
    async def test_lifecycle_from_creation_to_exhaustion(
        self,
        test_db_session: AsyncSession,
        test_user
    ):
        """Test complete lifecycle from budget creation to exhaustion and reset."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        budget_service = TokenBudgetService()
        quota_service = TokenQuotaService()
        reporting_service = TokenReportingService()

        # Create budget and quota
        budget_data = {
            'name': 'Lifecycle Test Budget',
            'scope_type': 'test',
            'scope_id': 700,
            'period_type': 'daily',
            'total_tokens': 10000,
            'priority': 5,
            'alert_thresholds': {'warning': 50, 'critical': 80}
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        quota_data = {
            'user_id': test_user.id,
            'name': 'Lifecycle Test Quota',
            'period_type': 'daily',
            'total_tokens': 5000,
            'priority': 5
        }

        quota_schema = TokenQuotaCreate(**quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        quota = await quota_repo.create(quota_schema, test_db_session)

        # Phase 1: Initial availability
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=700,
            requested_tokens=5000,
            db=test_db_session
        )
        assert is_success(check_result)
        assert check_result.data['available'] is True

        # Phase 2: Progressive usage
        usage_amounts = [2000, 2500, 3000, 2500]
        for amount in usage_amounts:
            await budget_service.record_token_usage(
                budget_id=budget.id,
                scope_type='test',
                scope_id=700,
                tokens_used=amount,
                db=test_db_session
            )
            await quota_service.record_quota_usage(
                user_id=test_user.id,
                tokens_used=amount,
                db=test_db_session
            )

        # Phase 3: Check status after usage
        status_result = await budget_service.get_budget_status(budget.id, test_db_session)
        assert is_success(status_result)
        assert status_result.data['used_tokens'] == sum(usage_amounts)

        # Phase 4: Exhaust budget
        remaining = status_result.data['remaining_tokens']
        await budget_service.record_token_usage(
            budget_id=budget.id,
            scope_type='test',
            scope_id=700,
            tokens_used=remaining,
            db=test_db_session
        )

        # Phase 5: Verify exhausted status
        final_status = await budget_service.get_budget_status(budget.id, test_db_session)
        assert final_status.data['status'] == 'exhausted'

        # Phase 6: Generate report
        report_result = await reporting_service.generate_budget_report(budget.id, test_db_session)
        assert is_success(report_result)

        # Phase 7: Reset period
        new_start = datetime.utcnow()
        new_end = new_start + timedelta(days=1)

        reset_result = await budget_service.reset_budget_period(
            budget_id=budget.id,
            new_period_start=new_start,
            new_period_end=new_end,
            db=test_db_session
        )
        assert is_success(reset_result)
        assert reset_result.data['used_tokens'] == 0
        assert reset_result.data['status'] == 'active'


class TestBudgetExhaustionScenarios:
    """Test suite for budget exhaustion scenarios."""

    @pytest.mark.asyncio
    async def test_hard_enforcement_blocks_execution(
        self,
        test_db_session: AsyncSession
    ):
        """Test that hard enforcement blocks LLM execution."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_service = TokenBudgetService()

        # Create budget with hard enforcement
        budget_data = {
            'name': 'Hard Enforcement Budget',
            'scope_type': 'test',
            'scope_id': 800,
            'period_type': 'daily',
            'total_tokens': 1000,
            'priority': 5,
            'enforcement_mode': 'hard',
            'status': 'active'
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        # Exhaust budget
        await budget_repo.update_usage(budget.id, 1000, test_db_session)

        # Check availability for more tokens
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=800,
            requested_tokens=500,
            db=test_db_session
        )

        assert is_success(check_result)
        assert check_result.data['available'] is False
        assert check_result.data['enforcement_action'] == 'blocked'

    @pytest.mark.asyncio
    async def test_soft_enforcement_allows_with_warning(
        self,
        test_db_session: AsyncSession
    ):
        """Test that soft enforcement allows with warning."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_service = TokenBudgetService()

        # Create budget with soft enforcement
        budget_data = {
            'name': 'Soft Enforcement Budget',
            'scope_type': 'test',
            'scope_id = 900',
            'period_type': 'daily',
            'total_tokens': 1000,
            'priority': 5,
            'enforcement_mode': 'soft',
            'status': 'active'
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        # Exhaust budget
        await budget_repo.update_usage(budget.id, 1000, test_db_session)

        # Check availability
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=900,
            requested_tokens=500,
            db=test_db_session
        )

        assert is_success(check_result)
        # Soft enforcement should allow but warn
        assert check_result.data['enforcement_action'] == 'warning'

    @pytest.mark.asyncio
    async def test_monitoring_mode_tracks_only(
        self,
        test_db_session: AsyncSession
    ):
        """Test that monitoring mode only tracks without enforcement."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_service = TokenBudgetService()

        # Create budget with monitoring mode
        budget_data = {
            'name': 'Monitoring Budget',
            'scope_type': 'test',
            'scope_id': 1000,
            'period_type': 'daily',
            'total_tokens': 1000,
            'priority': 5,
            'enforcement_mode': 'monitoring',
            'status': 'active'
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        # Check availability even when exhausted
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=1000,
            requested_tokens=5000,
            db=test_db_session
        )

        assert is_success(check_result)
        # Monitoring mode should always allow
        assert check_result.data['available'] is True


class TestQuotaResetScenarios:
    """Test suite for quota reset scenarios."""

    @pytest.mark.asyncio
    async def test_calendar_reset_at_midnight(
        self,
        test_db_session: AsyncSession,
        test_user
    ):
        """Test calendar-based quota reset at midnight."""
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        quota_service = TokenQuotaService()

        # Create quota with calendar reset
        quota_data = {
            'user_id': test_user.id,
            'name': 'Calendar Reset Quota',
            'period_type': 'daily',
            'reset_strategy': 'calendar',
            'total_tokens': 10000,
            'priority': 5
        }

        quota_schema = TokenQuotaCreate(**quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        quota = await quota_repo.create(quota_schema, test_db_session)

        # Use some tokens
        await quota_repo.update_usage(quota.id, 5000, test_db_session)

        # Reset quota (simulating midnight)
        new_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        reset_result = await quota_service.reset_quota_period(
            quota_id=quota.id,
            new_period_start=new_start,
            new_period_end=new_start + timedelta(days=1),
            db_session=test_db_session
        )

        assert is_success(reset_result)
        assert reset_result.data['used_tokens'] == 0
        assert reset_result.data['status'] == 'active'

    @pytest.mark.asyncio
    async def test_rolling_reset_from_first_use(
        self,
        test_db_session: AsyncSession,
        test_user
    ):
        """Test rolling reset from first use."""
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        quota_service = TokenQuotaService()

        # Create quota with rolling reset
        quota_data = {
            'user_id': test_user.id,
            'name': 'Rolling Reset Quota',
            'period_type': 'weekly',
            'reset_strategy': 'rolling',
            'total_tokens': 50000,
            'priority': 5
        }

        quota_schema = TokenQuotaCreate(**quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        quota = await quota_repo.create(quota_schema, test_db_session)

        # First use sets the period start
        first_use_time = datetime.utcnow() - timedelta(days=3)
        quota.period_start = first_use_time

        # Simulate reset after 7 days
        reset_time = first_use_time + timedelta(days=7)
        reset_result = await quota_service.reset_quota_period(
            quota_id=quota.id,
            new_period_start=reset_time,
            new_period_end=reset_time + timedelta(weeks=1),
            db_session=test_db_session
        )

        assert is_success(reset_result)
        assert reset_result.data['used_tokens'] == 0


class TestAlertGenerationScenarios:
    """Test suite for alert generation scenarios."""

    @pytest.mark.asyncio
    async def test_warning_alert_at_threshold(
        self,
        test_db_session: AsyncSession
    ):
        """Test warning alert generation at threshold."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        alert_service = TokenAlertService()

        # Create budget with warning threshold at 50%
        budget_data = {
            'name': 'Warning Alert Budget',
            'scope_type': 'test',
            'scope_id': 1100,
            'period_type': 'daily',
            'total_tokens': 10000,
            'priority': 5,
            'alert_thresholds': {'warning': 50}
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        # Use tokens to exceed 50% threshold
        await budget_repo.update_usage(budget.id, 5500, test_db_session)

        # Check and create alerts
        alert_result = await alert_service.check_and_create_alerts(budget.id, test_db_session)

        assert is_success(alert_result)
        assert alert_result.data['alerts_created'] >= 1

    @pytest.mark.asyncio
    async def test_critical_alert_at_high_threshold(
        self,
        test_db_session: AsyncSession
    ):
        """Test critical alert generation at high threshold."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        alert_service = TokenAlertService()

        # Create budget with critical threshold at 90%
        budget_data = {
            'name': 'Critical Alert Budget',
            'scope_type': 'test',
            'scope_id': 1200,
            'period_type': 'daily',
            'total_tokens': 10000,
            'priority': 5,
            'alert_thresholds': {'critical': 90}
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        # Use tokens to exceed 90% threshold
        await budget_repo.update_usage(budget.id, 9500, test_db_session)

        # Check and create alerts
        alert_result = await alert_service.check_and_create_alerts(budget.id, test_db_session)

        assert is_success(alert_result)
        assert alert_result.data['alerts_created'] >= 1

    @pytest.mark.asyncio
    async def test_alert_acknowledgment_workflow(
        self,
        test_db_session: AsyncSession,
        sample_token_alert: TokenAlert,
        test_user
    ):
        """Test alert acknowledgment workflow."""
        alert_service = TokenAlertService()

        # Acknowledge alert
        acknowledge_result = await alert_service.acknowledge_alert(
            alert_id=sample_token_alert.id,
            user_id=test_user.id,
            db_session=test_db_session
        )

        assert is_success(acknowledge_result)
        assert acknowledge_result.data['is_acknowledged'] is True
        assert acknowledge_result.data['acknowledged_by'] == test_user.id

        # Verify acknowledgment
        unacknowledged_result = await alert_service.get_unacknowledged_alerts(test_db_session)
        assert is_success(unacknowledged_result)
        assert sample_token_alert.id not in [a['id'] for a in unacknowledged_result.data['alerts']]


class TestMultiUserScenarios:
    """Test suite for multi-user scenarios."""

    @pytest.mark.asyncio
    async def test_separate_quotas_per_user(
        self,
        test_db_session: AsyncSession,
        test_user,
        test_admin_user
    ):
        """Test separate quotas for different users."""
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        quota_service = TokenQuotaService()

        # Create quota for test_user
        user_quota_data = {
            'user_id': test_user.id,
            'name': 'User Quota',
            'period_type': 'daily',
            'total_tokens': 5000,
            'priority': 5
        }

        user_quota_schema = TokenQuotaCreate(**user_quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        user_quota = await quota_repo.create(user_quota_schema, test_db_session)

        # Create quota for admin_user
        admin_quota_data = {
            'user_id': test_admin_user.id,
            'name': 'Admin Quota',
            'period_type': 'daily',
            'total_tokens': 10000,
            'priority': 8
        }

        admin_quota_schema = TokenQuotaCreate(**admin_quota_data)
        admin_quota = await quota_repo.create(admin_quota_schema, test_db_session)

        # Use tokens for each user
        await quota_service.record_quota_usage(
            user_id=test_user.id,
            tokens_used=2500,
            db=test_db_session
        )

        await quota_service.record_quota_usage(
            user_id=test_admin_user.id,
            tokens_used=5000,
            db=test_db_session
        )

        # Check each user's quota
        user_summary = await quota_service.get_user_quota_summary(test_user.id, test_db_session)
        admin_summary = await quota_service.get_user_quota_summary(test_admin_user.id, test_db_session)

        assert is_success(user_summary)
        assert user_summary.data['total_used'] == 2500

        assert is_success(admin_summary)
        assert admin_summary.data['total_used'] == 5000


class TestConcurrentOperations:
    """Test suite for concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_token_updates(
        self,
        test_db_session: AsyncSession,
        sample_token_budget: TokenBudget
    ):
        """Test concurrent token updates to same budget."""
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_repo = SQLAlchemyTokenBudgetRepository()

        # Create concurrent update tasks
        async def update_budget(amount: int):
            await budget_repo.update_usage(sample_token_budget.id, amount, test_db_session)

        # Run concurrent updates
        tasks = [update_budget(100) for _ in range(10)]
        await asyncio.gather(*tasks)

        # Verify final state
        final_budget = await budget_repo.get_by_id(sample_token_budget.id, test_db_session)
        assert final_budget.used_tokens == 1000  # 10 updates * 100 tokens

    @pytest.mark.asyncio
    async def test_concurrent_availability_checks(
        self,
        test_db_session: AsyncSession,
        sample_token_budget: TokenBudget
    ):
        """Test concurrent availability checks."""
        budget_service = TokenBudgetService()

        # Create concurrent check tasks
        async def check_availability():
            return await budget_service.check_token_availability(
                scope_type=sample_token_budget.scope_type,
                scope_id=sample_token_budget.scope_id,
                requested_tokens=500,
                db=test_db_session
            )

        # Run concurrent checks
        tasks = [check_availability() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # All checks should succeed
        assert all(is_success(r) for r in results)
        assert all(r.data['available'] for r in results)


class TestPerformanceUnderLoad:
    """Test suite for performance under load."""

    @pytest.mark.asyncio
    async def test_token_check_performance(
        self,
        test_db_session: AsyncSession,
        sample_token_budget: TokenBudget
    ):
        """Test token check performance under load."""
        import time

        budget_service = TokenBudgetService()

        # Measure performance of multiple checks
        start_time = time.perf_counter()

        for _ in range(100):
            result = await budget_service.check_token_availability(
                scope_type=sample_token_budget.scope_type,
                scope_id=sample_token_budget.scope_id,
                requested_tokens=500,
                db=test_db_session
            )
            assert is_success(result)

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds
        avg_time = total_time / 100

        # Average check should be under 5ms
        assert avg_time < 5.0, f"Average check time {avg_time}ms exceeds 5ms threshold"

    @pytest.mark.asyncio
    async def test_token_update_performance(
        self,
        test_db_session: AsyncSession,
        sample_token_budget: TokenBudget
    ):
        """Test token update performance under load."""
        import time
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_repo = SQLAlchemyTokenBudgetRepository()

        # Measure performance of multiple updates
        start_time = time.perf_counter()

        for i in range(50):
            result = await budget_repo.update_usage(
                sample_token_budget.id,
                10,
                test_db_session
            )

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        avg_time = total_time / 50

        # Average update should be under 10ms
        assert avg_time < 10.0, f"Average update time {avg_time}ms exceeds 10ms threshold"

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(
        self,
        test_db_session: AsyncSession,
        sample_token_budget: TokenBudget
    ):
        """Test performance with concurrent operations."""
        import time
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_service = TokenBudgetService()
        budget_repo = SQLAlchemyTokenBudgetRepository()

        async def mixed_operation(operation_type: str):
            if operation_type == 'check':
                return await budget_service.check_token_availability(
                    scope_type=sample_token_budget.scope_type,
                    scope_id=sample_token_budget.scope_id,
                    requested_tokens=500,
                    db=test_db_session
                )
            elif operation_type == 'update':
                return await budget_repo.update_usage(
                    sample_token_budget.id,
                    10,
                    test_db_session
                )
            elif operation_type == 'status':
                return await budget_service.get_budget_status(
                    sample_token_budget.id,
                    test_db_session
                )

        # Run mixed operations concurrently
        operations = ['check', 'update', 'status'] * 20
        start_time = time.perf_counter()

        results = await asyncio.gather(*[mixed_operation(op) for op in operations])

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000

        # All operations should succeed
        assert all(is_success(r) for r in results)

        # Total time should be reasonable (under 2 seconds for 60 operations)
        assert total_time < 2000.0, f"Total time {total_time}ms exceeds 2000ms threshold"
