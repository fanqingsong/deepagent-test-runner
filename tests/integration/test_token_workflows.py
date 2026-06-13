"""
Token Workflow Integration Tests

Comprehensive integration tests for token limitation in workflows:
- Test generation with token checking
- Script generation with token tracking
- Test execution with token limits
- Temporal workflow integration
- End-to-end token lifecycle
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.services.token_alert_service import TokenAlertService
from app.services.execution_service_with_tokens import ExecutionServiceWithTokens
from app.core.decorators.token_decorators import enforce_token_limits
from app.core.result_helpers import is_success, is_error


class TestTestGenerationWithTokens:
    """Test suite for test generation with token limitation."""

    @pytest.fixture
    def budget_service(self, test_db_session: AsyncSession):
        """Get budget service instance."""
        return TokenBudgetService()

    @pytest.fixture
    def quota_service(self, test_db_session: AsyncSession):
        """Get quota service instance."""
        return TokenQuotaService()

    @pytest.fixture
    async def test_generation_budget(self, test_db_session: AsyncSession, sample_token_budget_data: dict):
        """Create budget for test generation."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_data = sample_token_budget_data.copy()
        budget_data['scope_type'] = 'test'
        budget_data['scope_id'] = 1
        budget_data['name'] = 'Test Generation Budget'

        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        return await repo.create(budget_schema, test_db_session)

    @pytest.mark.asyncio
    async def test_test_generation_with_sufficient_tokens(
        self,
        budget_service: TokenBudgetService,
        test_generation_budget: TokenBudget,
        test_db_session: AsyncSession
    ):
        """Test test generation when sufficient tokens are available."""
        # Check availability
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=1,
            requested_tokens=5000,
            db=test_db_session
        )

        assert is_success(check_result)
        assert check_result.data['available'] is True

    @pytest.mark.asyncio
    async def test_test_generation_blocked_by_exhausted_budget(
        self,
        budget_service: TokenBudgetService,
        test_db_session: AsyncSession
    ):
        """Test test generation blocked by exhausted budget."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create exhausted budget
        budget_data = {
            'name': 'Exhausted Budget',
            'scope_type': 'test',
            'scope_id': 2,
            'period_type': 'daily',
            'total_tokens': 1000,
            'used_tokens': 1000,
            'remaining_tokens': 0,
            'priority': 5,
            'status': 'exhausted',
            'enforcement_mode': 'hard'
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        budget = await repo.create(budget_schema, test_db_session)

        # Check availability
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=2,
            requested_tokens=500,
            db=test_db_session
        )

        assert is_success(check_result)
        assert check_result.data['available'] is False
        assert check_result.data['reason'] == 'insufficient_tokens'

    @pytest.mark.asyncio
    async def test_test_generation_records_token_usage(
        self,
        budget_service: TokenBudgetService,
        test_generation_budget: TokenBudget,
        test_db_session: AsyncSession
    ):
        """Test that test generation records token usage."""
        initial_used = test_generation_budget.used_tokens

        # Record usage
        record_result = await budget_service.record_token_usage(
            budget_id=test_generation_budget.id,
            scope_type='test',
            scope_id=1,
            tokens_used=3500,
            db=test_db_session
        )

        assert is_success(record_result)
        assert record_result.data['used_tokens'] == initial_used + 3500

        # Verify budget was updated
        updated_budget = await budget_service.get_budget_status(test_generation_budget.id, test_db_session)
        assert updated_budget.data['used_tokens'] == initial_used + 3500


class TestScriptGenerationWithTokens:
    """Test suite for script generation with token tracking."""

    @pytest.fixture
    def budget_service(self, test_db_session: AsyncSession):
        """Get budget service instance."""
        return TokenBudgetService()

    @pytest.fixture
    def quota_service(self, test_db_session: AsyncSession):
        """Get quota service instance."""
        return TokenQuotaService()

    @pytest.fixture
    async def script_generation_budget(self, test_db_session: AsyncSession):
        """Create budget for script generation."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_data = {
            'name': 'Script Generation Budget',
            'scope_type': 'suite',
            'scope_id': 100,
            'period_type': 'monthly',
            'total_tokens': 500000,
            'priority': 7,
            'enforcement_mode': 'soft'
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        return await repo.create(budget_schema, test_db_session)

    @pytest.mark.asyncio
    async def test_script_generation_with_decorator(
        self,
        budget_service: TokenBudgetService,
        quota_service: TokenQuotaService,
        script_generation_budget: TokenBudget,
        test_user,
        test_db_session: AsyncSession
    ):
        """Test script generation with enforce_token_limits decorator."""
        @enforce_token_limits(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id",
            enforcement_mode="soft"
        )
        async def generate_script(prompt: str, scope_type: str, scope_id: int, user_id: int, **kwargs):
            # Simulate LLM call
            return {
                "script": "generated_script",
                "tokens_used": 4500,
                "result": "success"
            }

        result = await generate_script(
            prompt="Generate login test script",
            scope_type='suite',
            scope_id=100,
            user_id=test_user.id,
            token_budget_service=budget_service,
            token_quota_service=quota_service,
            db=test_db_session
        )

        assert result["result"] == "success"
        assert result["tokens_used"] == 4500

    @pytest.mark.asyncio
    async def test_script_generation_tracks_both_budget_and_quota(
        self,
        budget_service: TokenBudgetService,
        quota_service: TokenQuotaService,
        test_user,
        test_db_session: AsyncSession
    ):
        """Test that script generation tracks both budget and quota usage."""
        # Create budget and quota
        from app.schemas.token_budget import TokenBudgetCreate
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        budget_data = {
            'name': 'Test Budget',
            'scope_type': 'test',
            'scope_id': 300,
            'period_type': 'daily',
            'total_tokens': 10000,
            'priority': 5
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        budget_repo = SQLAlchemyTokenBudgetRepository()
        budget = await budget_repo.create(budget_schema, test_db_session)

        quota_data = {
            'user_id': test_user.id,
            'name': 'User Quota',
            'period_type': 'daily',
            'total_tokens': 5000,
            'priority': 5
        }
        quota_schema = TokenQuotaCreate(**quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        quota = await quota_repo.create(quota_schema, test_db_session)

        @enforce_token_limits()
        async def generate_script(prompt: str, scope_type: str, scope_id: int, user_id: int, **kwargs):
            return {"tokens_used": 2000, "result": "success"}

        result = await generate_script(
            prompt="Generate test script",
            scope_type='test',
            scope_id=300,
            user_id=test_user.id,
            token_budget_service=budget_service,
            token_quota_service=quota_service,
            db=test_db_session
        )

        # Verify both were tracked
        budget_status = await budget_service.get_budget_status(budget.id, test_db_session)
        assert budget_status.data['used_tokens'] == 2000

        # Get user quotas and check
        user_quotas = await quota_service.get_user_quota_summary(test_user.id, test_db_session)
        assert user_quotas.data['total_used'] == 2000


class TestTestExecutionWithTokens:
    """Test suite for test execution with token limits."""

    @pytest.fixture
    def execution_service(self, test_db_session: AsyncSession):
        """Get execution service instance."""
        return ExecutionServiceWithTokens()

    @pytest.fixture
    async def execution_budget(self, test_db_session: AsyncSession):
        """Create budget for test execution."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        budget_data = {
            'name': 'Test Execution Budget',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'monthly',
            'total_tokens': 1000000,
            'priority': 10,
            'enforcement_mode': 'hard'
        }

        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        return await repo.create(budget_schema, test_db_session)

    @pytest.mark.asyncio
    async def test_execution_allowed_with_sufficient_budget(
        self,
        execution_budget: TokenBudget,
        test_db_session: AsyncSession
    ):
        """Test that execution is allowed with sufficient budget."""
        budget_service = TokenBudgetService()

        check_result = await budget_service.check_token_availability(
            scope_type='organization',
            scope_id=None,
            requested_tokens=10000,
            db=test_db_session
        )

        assert is_success(check_result)
        assert check_result.data['available'] is True

    @pytest.mark.asyncio
    async def test_execution_blocked_with_insufficient_hard_limit(
        self,
        test_db_session: AsyncSession
    ):
        """Test that execution is blocked with hard limit enforcement."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create budget with hard limit and low remaining
        budget_data = {
            'name': 'Low Budget',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'monthly',
            'total_tokens': 5000,
            'used_tokens': 4500,
            'remaining_tokens': 500,
            'priority': 10,
            'enforcement_mode': 'hard',
            'status': 'active'
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        budget = await repo.create(budget_schema, test_db_session)

        budget_service = TokenBudgetService()

        # Request more than remaining
        check_result = await budget_service.check_token_availability(
            scope_type='organization',
            scope_id=None,
            requested_tokens=1000,  # More than remaining (500)
            db=test_db_session
        )

        assert is_success(check_result)
        assert check_result.data['available'] is False
        assert check_result.data['enforcement_action'] == 'blocked'


class TestAlertGenerationWorkflow:
    """Test suite for alert generation in workflows."""

    @pytest.fixture
    def alert_service(self, test_db_session: AsyncSession):
        """Get alert service instance."""
        return TokenAlertService()

    @pytest.mark.asyncio
    async def test_alert_created_on_threshold_exceeded(
        self,
        alert_service: TokenAlertService,
        sample_token_budget: TokenBudget,
        test_db_session: AsyncSession
    ):
        """Test that alert is created when threshold is exceeded."""
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Use tokens to exceed warning threshold (80%)
        repo = SQLAlchemyTokenBudgetRepository()
        await repo.update_usage(sample_token_budget.id, 850000, test_db_session)

        # Check and create alerts
        result = await alert_service.check_and_create_alerts(
            sample_token_budget.id,
            test_db_session
        )

        assert is_success(result)
        assert result.data['alerts_created'] >= 1

    @pytest.mark.asyncio
    async def test_multiple_alerts_for_different_thresholds(
        self,
        alert_service: TokenAlertService,
        test_db_session: AsyncSession
    ):
        """Test multiple alerts for different thresholds."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository

        # Create budget
        budget_data = {
            'name': 'Multi-Alert Budget',
            'scope_type': 'test',
            'scope_id': 500,
            'period_type': 'daily',
            'total_tokens': 100000,
            'priority': 5,
            'alert_thresholds': {
                'warning': 70,
                'critical': 85,
                'emergency': 95
            }
        }
        budget_schema = TokenBudgetCreate(**budget_data)
        repo = SQLAlchemyTokenBudgetRepository()
        budget = await repo.create(budget_schema, test_db_session)

        # Use tokens to exceed warning threshold
        await repo.update_usage(budget.id, 75000, test_db_session)

        result = await alert_service.check_and_create_alerts(budget.id, test_db_session)

        assert is_success(result)
        assert result.data['alerts_created'] >= 1


class TestEndToEndTokenLifecycle:
    """Test suite for end-to-end token lifecycle."""

    @pytest.mark.asyncio
    async def test_complete_token_lifecycle(
        self,
        test_db_session: AsyncSession,
        test_user
    ):
        """Test complete token lifecycle from creation to exhaustion."""
        from app.schemas.token_budget import TokenBudgetCreate
        from app.schemas.token_quota import TokenQuotaCreate
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository

        budget_service = TokenBudgetService()
        quota_service = TokenQuotaService()
        alert_service = TokenAlertService()

        # 1. Create budget and quota
        budget_data = {
            'name': 'Lifecycle Budget',
            'scope_type': 'test',
            'scope_id': 600,
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
            'name': 'Lifecycle Quota',
            'period_type': 'daily',
            'total_tokens': 5000,
            'priority': 5
        }
        quota_schema = TokenQuotaCreate(**quota_data)
        quota_repo = SQLAlchemyTokenQuotaRepository()
        quota = await quota_repo.create(quota_schema, test_db_session)

        # 2. Check availability (should be available)
        check_result = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=600,
            requested_tokens=3000,
            db=test_db_session
        )
        assert is_success(check_result)
        assert check_result.data['available'] is True

        # 3. Record usage (first use)
        record_result = await budget_service.record_token_usage(
            budget_id=budget.id,
            scope_type='test',
            scope_id=600,
            tokens_used=3000,
            db=test_db_session
        )
        assert is_success(record_result)

        await quota_service.record_quota_usage(
            user_id=test_user.id,
            tokens_used=3000,
            db=test_db_session
        )

        # 4. Check if warning threshold exceeded (50% = 5000 tokens)
        await budget_repo.update_usage(budget.id, 3000, test_db_session)
        alert_result = await alert_service.check_and_create_alerts(budget.id, test_db_session)
        assert is_success(alert_result)

        # 5. Use more tokens (now at 6000 total)
        await budget_service.record_token_usage(
            budget_id=budget.id,
            scope_type='test',
            scope_id=600,
            tokens_used=3000,
            db=test_db_session
        )

        # 6. Check status
        status_result = await budget_service.get_budget_status(budget.id, test_db_session)
        assert is_success(status_result)
        assert status_result.data['usage_percentage'] == 60.0

        # 7. Use remaining tokens
        await budget_service.record_token_usage(
            budget_id=budget.id,
            scope_type='test',
            scope_id=600,
            tokens_used=4000,
            db=test_db_session
        )

        # 8. Verify exhausted status
        final_status = await budget_service.get_budget_status(budget.id, test_db_session)
        assert final_status.data['status'] == 'exhausted'

        # 9. Verify no longer available
        final_check = await budget_service.check_token_availability(
            scope_type='test',
            scope_id=600,
            requested_tokens=1000,
            db=test_db_session
        )
        assert is_success(final_check)
        assert final_check.data['available'] is False

        # 10. Reset period
        new_start = datetime.utcnow()
        reset_result = await budget_service.reset_budget_period(
            budget_id=budget.id,
            new_period_start=new_start,
            new_period_end=new_start + timedelta(days=1),
            db=test_db_session
        )
        assert is_success(reset_result)
        assert reset_result.data['status'] == 'active'
        assert reset_result.data['used_tokens'] == 0
