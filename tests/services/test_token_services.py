"""
Token Service Tests

Comprehensive tests for all token-related services:
- TokenBudgetService
- TokenQuotaService
- TokenAlertService
- TokenReportingService
"""

import pytest
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
from app.core.result_helpers import service_success, service_error, is_success, is_error


class TestTokenBudgetService:
    """Test suite for TokenBudgetService."""

    @pytest.fixture
    def service(self):
        """Get service instance with mocked repository."""
        mock_repo = Mock()
        mock_metrics = Mock()
        return TokenBudgetService(budget_repository=mock_repo, metrics_collector=mock_metrics)

    @pytest.mark.asyncio
    async def test_check_token_availability_success(self, service: TokenBudgetService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test successful token availability check."""
        result = await service.check_token_availability(
            sample_token_budget.scope_type,
            sample_token_budget.scope_id,
            50000,
            test_db_session
        )

        assert is_success(result)
        assert result.data['available'] is True
        assert result.data['remaining_tokens'] == sample_token_budget.total_tokens

    @pytest.mark.asyncio
    async def test_check_token_availability_insufficient_tokens(self, service: TokenBudgetService, test_db_session: AsyncSession):
        """Test token availability check with insufficient tokens."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create budget with small limit
        budget_data = {
            'name': 'Small Budget',
            'scope_type': 'user',
            'scope_id': 111,
            'period_type': 'daily',
            'total_tokens': 1000,
            'priority': 5
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        budget = await repo.create(budget_schema, test_db_session)

        # Use most of budget
        await repo.update_usage(budget.id, 900, test_db_session)

        # Check availability for more than remaining
        result = await service.check_token_availability(
            budget.scope_type,
            budget.scope_id,
            200,  # Request more than remaining (100)
            test_db_session
        )

        assert is_success(result)
        assert result.data['available'] is False
        assert result.data['reason'] == 'insufficient_tokens'

    @pytest.mark.asyncio
    async def test_check_token_availability_budget_not_found(self, service: TokenBudgetService, test_db_session: AsyncSession):
        """Test token availability check when budget not found."""
        result = await service.check_token_availability(
            'organization',
            99999,
            50000,
            test_db_session
        )

        # Should return success with available=True (no budget = no limit)
        assert is_success(result)
        assert result.data['available'] is True

    @pytest.mark.asyncio
    async def test_record_token_usage(self, service: TokenBudgetService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test recording token usage."""
        tokens_used = 75000

        result = await service.record_token_usage(
            sample_token_budget.id,
            tokens_used,
            test_db_session
        )

        assert is_success(result)
        assert result.data['used_tokens'] == tokens_used
        assert result.data['remaining_tokens'] == sample_token_budget.total_tokens - tokens_used

    @pytest.mark.asyncio
    async def test_record_token_usage_exhausts_budget(self, service: TokenBudgetService, test_db_session: AsyncSession):
        """Test that recording usage updates budget to exhausted status."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create budget with small limit
        budget_data = {
            'name': 'Small Budget',
            'scope_type': 'user',
            'scope_id': 222,
            'period_type': 'daily',
            'total_tokens': 1000,
            'priority': 5
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        budget = await repo.create(budget_schema, test_db_session)

        # Record usage that exhausts budget
        result = await service.record_token_usage(
            budget.id,
            1000,  # Exactly the budget limit
            test_db_session
        )

        assert is_success(result)
        assert result.data['status'] == 'exhausted'

    @pytest.mark.asyncio
    async def test_get_budget_status(self, service: TokenBudgetService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test getting budget status."""
        result = await service.get_budget_status(sample_token_budget.id, test_db_session)

        assert is_success(result)
        assert result.data['budget_id'] == sample_token_budget.id
        assert result.data['status'] == sample_token_budget.status
        assert 'usage_percentage' in result.data
        assert 'remaining_tokens' in result.data

    @pytest.mark.asyncio
    async def test_get_budget_hierarchy(self, service: TokenBudgetService, test_db_session: AsyncSession):
        """Test getting budget hierarchy."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create budget hierarchy
        parent_data = {
            'name': 'Parent Budget',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'monthly',
            'total_tokens': 1000000,
            'priority': 10
        }
        parent_schema = TokenBudgetCreate(**parent_data)
        repo = SQLAlchemyTokenBudgetRepository()
        parent = await repo.create(parent_schema, test_db_session)

        child_data = {
            'name': 'Child Budget',
            'scope_type': 'suite',
            'scope_id': 100,
            'parent_budget_id': parent.id,
            'period_type': 'monthly',
            'total_tokens': 500000,
            'priority': 5
        }
        child_schema = TokenBudgetCreate(**child_data)
        child = await repo.create(child_schema, test_db_session)

        result = await service.get_budget_hierarchy(child.id, test_db_session)

        assert is_success(result)
        assert len(result.data['hierarchy']) == 2
        assert result.data['hierarchy'][0]['id'] == child.id
        assert result.data['hierarchy'][1]['id'] == parent.id

    @pytest.mark.asyncio
    async def test_calculate_forecast(self, service: TokenBudgetService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test usage forecast calculation."""
        # Use some tokens
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        repo = SQLAlchemyTokenBudgetRepository()
        await repo.update_usage(sample_token_budget.id, 50000, test_db_session)

        result = await service.calculate_forecast(
            sample_token_budget.id,
            test_db_session
        )

        assert is_success(result)
        assert 'forecast_data' in result.data
        assert 'projected_exhaustion_date' in result.data
        assert 'daily_average_usage' in result.data

    @pytest.mark.asyncio
    async def test_reset_budget_period(self, service: TokenBudgetService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test resetting budget period."""
        # Use some tokens first
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        repo = SQLAlchemyTokenBudgetRepository()
        await repo.update_usage(sample_token_budget.id, 50000, test_db_session)

        # Reset period
        new_start = datetime.utcnow()
        new_end = new_start + timedelta(days=30)

        result = await service.reset_budget_period(
            sample_token_budget.id,
            new_start,
            new_end,
            test_db_session
        )

        assert is_success(result)
        assert result.data['used_tokens'] == 0
        assert result.data['status'] == 'active'

    @pytest.mark.asyncio
    async def test_validate_requested_tokens_negative(self, service: TokenBudgetService, test_db_session: AsyncSession):
        """Test validation with negative token request."""
        result = await service.check_token_availability(
            'organization',
            None,
            -100,  # Negative tokens
            test_db_session
        )

        assert is_error(result)
        assert 'must be positive' in result.message.lower()


class TestTokenQuotaService:
    """Test suite for TokenQuotaService."""

    @pytest.fixture
    def service(self):
        """Get service instance with mocked repository."""
        mock_repo = Mock()
        mock_metrics = Mock()
        return TokenQuotaService(quota_repository=mock_repo, metrics_collector=mock_metrics)

    @pytest.mark.asyncio
    async def test_check_quota_availability(self, service: TokenQuotaService, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test checking quota availability."""
        result = await service.check_quota_availability(
            sample_token_quota.user_id,
            25000,
            test_db_session
        )

        assert is_success(result)
        assert result.data['available'] is True

    @pytest.mark.asyncio
    async def test_record_quota_usage(self, service: TokenQuotaService, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test recording quota usage."""
        tokens_used = 30000

        result = await service.record_quota_usage(
            sample_token_quota.user_id,
            tokens_used,
            test_db_session
        )

        assert is_success(result)
        assert result.data['recorded_tokens'] == tokens_used

    @pytest.mark.asyncio
    async def test_reset_user_quotas(self, service: TokenQuotaService, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test resetting user quotas."""
        # Use some tokens first
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository
        repo = SQLAlchemyTokenQuotaRepository()
        await repo.update_usage(sample_token_quota.id, 50000, test_db_session)

        # Reset
        result = await service.reset_user_quotas(
            sample_token_quota.user_id,
            test_db_session
        )

        assert is_success(result)
        assert result.data['reset_count'] >= 1

    @pytest.mark.asyncio
    async def test_get_user_quota_summary(self, service: TokenQuotaService, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test getting user quota summary."""
        result = await service.get_user_quota_summary(
            sample_token_quota.user_id,
            test_db_session
        )

        assert is_success(result)
        assert 'quotas' in result.data
        assert 'total_quota' in result.data
        assert 'total_used' in result.data


class TestTokenAlertService:
    """Test suite for TokenAlertService."""

    @pytest.fixture
    def service(self):
        """Get service instance with mocked repository."""
        mock_repo = Mock()
        mock_metrics = Mock()
        return TokenAlertService(alert_repository=mock_repo, metrics_collector=mock_metrics)

    @pytest.mark.asyncio
    async def test_create_alert(self, service: TokenAlertService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test creating an alert."""
        alert_data = {
            'alert_type': 'budget_warning',
            'severity': 'warning',
            'budget_id': sample_token_budget.id,
            'threshold_type': 'percentage',
            'threshold_value': 80.0,
            'current_value': 85.0,
            'message': 'Budget usage exceeded 80%'
        }

        result = await service.create_alert(alert_data, test_db_session)

        assert is_success(result)
        assert result.data['alert_type'] == 'budget_warning'

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, service: TokenAlertService, test_db_session: AsyncSession, sample_token_alert: TokenAlert, test_user):
        """Test acknowledging an alert."""
        result = await service.acknowledge_alert(
            sample_token_alert.id,
            test_user.id,
            test_db_session
        )

        assert is_success(result)
        assert result.data['is_acknowledged'] is True
        assert result.data['acknowledged_by'] == test_user.id

    @pytest.mark.asyncio
    async def test_check_and_create_alerts(self, service: TokenAlertService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test automatic alert creation based on thresholds."""
        # Use tokens to trigger warning threshold (80%)
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        repo = SQLAlchemyTokenBudgetRepository()
        await repo.update_usage(sample_token_budget.id, 850000, test_db_session)

        result = await service.check_and_create_alerts(
            sample_token_budget.id,
            test_db_session
        )

        assert is_success(result)
        assert result.data['alerts_created'] >= 1

    @pytest.mark.asyncio
    async def test_get_critical_alerts(self, service: TokenAlertService, test_db_session: AsyncSession):
        """Test getting critical alerts."""
        result = await service.get_critical_alerts(test_db_session)

        assert is_success(result)
        assert 'alerts' in result.data
        assert isinstance(result.data['alerts'], list)

    @pytest.mark.asyncio
    async def test_mark_notification_sent(self, service: TokenAlertService, test_db_session: AsyncSession, sample_token_alert: TokenAlert):
        """Test marking notification as sent."""
        result = await service.mark_notification_sent(
            sample_token_alert.id,
            'email',
            test_db_session
        )

        assert is_success(result)
        assert result.data['notifications_sent']['email'] is True


class TestTokenReportingService:
    """Test suite for TokenReportingService."""

    @pytest.fixture
    def service(self):
        """Get service instance."""
        return TokenReportingService()

    @pytest.mark.asyncio
    async def test_generate_budget_report(self, service: TokenReportingService, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test generating budget report."""
        result = await service.generate_budget_report(
            sample_token_budget.id,
            test_db_session
        )

        assert is_success(result)
        assert 'budget_info' in result.data
        assert 'usage_stats' in result.data
        assert 'alerts' in result.data

    @pytest.mark.asyncio
    async def test_generate_user_report(self, service: TokenReportingService, test_db_session: AsyncSession, test_user):
        """Test generating user report."""
        result = await service.generate_user_report(
            test_user.id,
            test_db_session
        )

        assert is_success(result)
        assert 'user_id' in result.data
        assert 'quotas' in result.data
        assert 'summary' in result.data

    @pytest.mark.asyncio
    async def test_generate_system_overview(self, service: TokenReportingService, test_db_session: AsyncSession):
        """Test generating system overview."""
        result = await service.generate_system_overview(test_db_session)

        assert is_success(result)
        assert 'total_budgets' in result.data
        assert 'total_quotas' in result.data
        assert 'active_budgets' in result.data
        assert 'exhausted_budgets' in result.data

    @pytest.mark.asyncio
    async def test_get_usage_trends(self, service: TokenReportingService, test_db_session: AsyncSession):
        """Test getting usage trends."""
        result = await service.get_usage_trends(
            days=7,
            db_session=test_db_session
        )

        assert is_success(result)
        assert 'trends' in result.data
        assert 'period_start' in result.data
        assert 'period_end' in result.data

    @pytest.mark.asyncio
    async def test_get_top_consumers(self, service: TokenReportingService, test_db_session: AsyncSession):
        """Test getting top consumers."""
        result = await service.get_top_consumers(
            limit=10,
            db_session=test_db_session
        )

        assert is_success(result)
        assert 'consumers' in result.data
        assert isinstance(result.data['consumers'], list)
