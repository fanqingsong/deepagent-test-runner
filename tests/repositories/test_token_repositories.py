"""
Token Repository Tests

Comprehensive tests for all token-related repositories:
- TokenBudgetRepository
- TokenQuotaRepository
- TokenAlertRepository
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert
from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository
from app.repositories.token_alert_repository import SQLAlchemyTokenAlertRepository


class TestTokenBudgetRepository:
    """Test suite for TokenBudgetRepository."""

    @pytest.fixture
    def repository(self):
        """Get repository instance."""
        return SQLAlchemyTokenBudgetRepository()

    @pytest.mark.asyncio
    async def test_create_budget(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget_data: dict):
        """Test creating a new token budget."""
        from app.schemas.token_budget import TokenBudgetCreate

        create_schema = TokenBudgetCreate(**sample_token_budget_data)
        budget = await repository.create(create_schema, test_db_session)

        assert budget.id is not None
        assert budget.name == sample_token_budget_data['name']
        assert budget.scope_type == sample_token_budget_data['scope_type']
        assert budget.total_tokens == sample_token_budget_data['total_tokens']
        assert budget.used_tokens == 0
        assert budget.remaining_tokens == sample_token_budget_data['total_tokens']
        assert budget.status == 'active'

    @pytest.mark.asyncio
    async def test_create_duplicate_budget_fails(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test that creating duplicate budget for same scope fails."""
        from app.schemas.token_budget import TokenBudgetCreate

        create_schema = TokenBudgetCreate(
            name='Duplicate Budget',
            scope_type=sample_token_budget.scope_type,
            scope_id=sample_token_budget.scope_id,
            period_type='monthly',
            total_tokens=500000,
            priority=5
        )

        with pytest.raises(ValueError, match="Budget already exists"):
            await repository.create(create_schema, test_db_session)

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test retrieving budget by ID."""
        budget = await repository.get_by_id(sample_token_budget.id, test_db_session)

        assert budget is not None
        assert budget.id == sample_token_budget.id
        assert budget.name == sample_token_budget.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving non-existent budget by ID."""
        budget = await repository.get_by_id(99999, test_db_session)
        assert budget is None

    @pytest.mark.asyncio
    async def test_get_by_scope(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test retrieving budget by scope."""
        budget = await repository.get_by_scope(
            sample_token_budget.scope_type,
            sample_token_budget.scope_id,
            test_db_session
        )

        assert budget is not None
        assert budget.id == sample_token_budget.id

    @pytest.mark.asyncio
    async def test_get_by_scope_not_found(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving non-existent budget by scope."""
        budget = await repository.get_by_scope('organization', 99999, test_db_session)
        assert budget is None

    @pytest.mark.asyncio
    async def test_get_all_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test retrieving all budgets."""
        # Create additional budget
        from app.schemas.token_budget import TokenBudgetCreate

        additional_data = sample_token_budget_data = {
            'name': 'Additional Budget',
            'scope_type': 'user',
            'scope_id': 123,
            'period_type': 'daily',
            'total_tokens': 50000,
            'priority': 3
        }
        create_schema = TokenBudgetCreate(**additional_data)
        await repository.create(create_schema, test_db_session)

        budgets = await repository.get_all(test_db_session)

        assert len(budgets) >= 2
        assert any(b.name == 'Test Budget' for b in budgets)
        assert any(b.name == 'Additional Budget' for b in budgets)

    @pytest.mark.asyncio
    async def test_get_active_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test retrieving active budgets."""
        # Create inactive budget
        from app.schemas.token_budget import TokenBudgetCreate

        inactive_data = {
            'name': 'Inactive Budget',
            'scope_type': 'user',
            'scope_id': 456,
            'period_type': 'daily',
            'total_tokens': 30000,
            'priority': 3,
            'status': 'inactive'
        }
        create_schema = TokenBudgetCreate(**inactive_data)
        await repository.create(create_schema, test_db_session)

        active_budgets = await repository.get_active_budgets(test_db_session)

        assert len(active_budgets) >= 1
        assert all(b.status == 'active' for b in active_budgets)

    @pytest.mark.asyncio
    async def test_get_by_scope_type(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test retrieving budgets by scope type."""
        # Create budget with same scope type
        from app.schemas.token_budget import TokenBudgetCreate

        additional_data = {
            'name': 'Same Scope Type',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'weekly',
            'total_tokens': 200000,
            'priority': 7
        }
        create_schema = TokenBudgetCreate(**additional_data)
        await repository.create(create_schema, test_db_session)

        org_budgets = await repository.get_by_scope_type('organization', test_db_session)

        assert len(org_budgets) >= 2
        assert all(b.scope_type == 'organization' for b in org_budgets)

    @pytest.mark.asyncio
    async def test_get_parent_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving parent budget hierarchy."""
        from app.schemas.token_budget import TokenBudgetCreate

        # Create parent budget
        parent_data = {
            'name': 'Parent Budget',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'monthly',
            'total_tokens': 1000000,
            'priority': 10
        }
        parent_schema = TokenBudgetCreate(**parent_data)
        parent = await repository.create(parent_schema, test_db_session)

        # Create child budget
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
        child = await repository.create(child_schema, test_db_session)

        # Create grandchild budget
        grandchild_data = {
            'name': 'Grandchild Budget',
            'scope_type': 'test',
            'scope_id': 200,
            'parent_budget_id': child.id,
            'period_type': 'monthly',
            'total_tokens': 100000,
            'priority': 3
        }
        grandchild_schema = TokenBudgetCreate(**grandchild_data)
        await repository.create(grandchild_schema, test_db_session)

        # Test parent retrieval
        parents = await repository.get_parent_budgets(grandchild.id, test_db_session)

        assert len(parents) == 2
        assert parents[0].id == child.id
        assert parents[1].id == parent.id

    @pytest.mark.asyncio
    async def test_get_child_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving child budgets."""
        from app.schemas.token_budget import TokenBudgetCreate

        # Create parent budget
        parent_data = {
            'name': 'Parent Budget',
            'scope_type': 'organization',
            'scope_id': None,
            'period_type': 'monthly',
            'total_tokens': 1000000,
            'priority': 10
        }
        parent_schema = TokenBudgetCreate(**parent_data)
        parent = await repository.create(parent_schema, test_db_session)

        # Create child budgets
        for i in range(3):
            child_data = {
                'name': f'Child Budget {i}',
                'scope_type': 'suite',
                'scope_id': 100 + i,
                'parent_budget_id': parent.id,
                'period_type': 'monthly',
                'total_tokens': 500000,
                'priority': 5
            }
            child_schema = TokenBudgetCreate(**child_data)
            await repository.create(child_schema, test_db_session)

        children = await repository.get_child_budgets(parent.id, test_db_session)

        assert len(children) == 3
        assert all(c.parent_budget_id == parent.id for c in children)

    @pytest.mark.asyncio
    async def test_get_exhausted_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving exhausted budgets."""
        from app.schemas.token_budget import TokenBudgetCreate

        # Create exhausted budget
        exhausted_data = {
            'name': 'Exhausted Budget',
            'scope_type': 'user',
            'scope_id': 789,
            'period_type': 'daily',
            'total_tokens': 1000,
            'used_tokens': 1000,
            'remaining_tokens': 0,
            'priority': 5,
            'status': 'exhausted'
        }
        exhausted_schema = TokenBudgetCreate(**exhausted_data)
        await repository.create(exhausted_schema, test_db_session)

        exhausted_budgets = await repository.get_exhausted_budgets(test_db_session)

        assert len(exhausted_budgets) >= 1
        assert all(b.status == 'exhausted' for b in exhausted_budgets)

    @pytest.mark.asyncio
    async def test_get_budgets_near_limit(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test retrieving budgets near their limit."""
        from app.schemas.token_budget import TokenBudgetCreate

        # Create budget near limit (85% used)
        near_limit_data = {
            'name': 'Near Limit Budget',
            'scope_type': 'user',
            'scope_id': 999,
            'period_type': 'daily',
            'total_tokens': 100000,
            'used_tokens': 85000,
            'remaining_tokens': 15000,
            'priority': 5
        }
        near_limit_schema = TokenBudgetCreate(**near_limit_data)
        await repository.create(near_limit_schema, test_db_session)

        near_limit_budgets = await repository.get_budgets_near_limit(threshold=80.0, db_session=test_db_session)

        assert len(near_limit_budgets) >= 1
        assert all(b.usage_percentage >= 80.0 for b in near_limit_budgets)

    @pytest.mark.asyncio
    async def test_update_budget(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test updating a budget."""
        updates = {
            'name': 'Updated Budget Name',
            'total_tokens': 2000000,
            'priority': 8
        }

        updated_budget = await repository.update(sample_token_budget.id, updates, test_db_session)

        assert updated_budget.name == 'Updated Budget Name'
        assert updated_budget.total_tokens == 2000000
        assert updated_budget.priority == 8
        assert updated_budget.remaining_tokens == 2000000  # Recalculated

    @pytest.mark.asyncio
    async def test_update_budget_not_found(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test updating non-existent budget."""
        with pytest.raises(ValueError, match="not found"):
            await repository.update(99999, {'name': 'New Name'}, test_db_session)

    @pytest.mark.asyncio
    async def test_update_usage(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test updating budget usage."""
        tokens_used = 50000

        updated_budget = await repository.update_usage(sample_token_budget.id, tokens_used, test_db_session)

        assert updated_budget.used_tokens == tokens_used
        assert updated_budget.remaining_tokens == sample_token_budget.total_tokens - tokens_used

    @pytest.mark.asyncio
    async def test_update_usage_triggers_exhausted_status(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test that updating usage triggers exhausted status when limit reached."""
        from app.schemas.token_budget import TokenBudgetCreate

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
        budget = await repository.create(budget_schema, test_db_session)

        # Use all tokens
        updated_budget = await repository.update_usage(budget.id, 1000, test_db_session)

        assert updated_budget.status == 'exhausted'
        assert updated_budget.is_exhausted

    @pytest.mark.asyncio
    async def test_reset_period(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test resetting budget period."""
        # Use some tokens first
        await repository.update_usage(sample_token_budget.id, 50000, test_db_session)

        # Reset period
        new_start = datetime.utcnow()
        new_end = new_start + timedelta(days=30)

        reset_budget = await repository.reset_period(
            sample_token_budget.id,
            new_start,
            new_end,
            test_db_session
        )

        assert reset_budget.used_tokens == 0
        assert reset_budget.remaining_tokens == reset_budget.total_tokens
        assert reset_budget.status == 'active'
        assert reset_budget.period_start == new_start
        assert reset_budget.period_end == new_end

    @pytest.mark.asyncio
    async def test_delete_budget(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test deleting a budget."""
        result = await repository.delete(sample_token_budget.id, test_db_session)

        assert result is True

        # Verify deletion
        deleted_budget = await repository.get_by_id(sample_token_budget.id, test_db_session)
        assert deleted_budget is None

    @pytest.mark.asyncio
    async def test_delete_budget_not_found(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession):
        """Test deleting non-existent budget."""
        result = await repository.delete(99999, test_db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_count_budgets(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test counting budgets."""
        # Create additional budgets
        from app.schemas.token_budget import TokenBudgetCreate

        for i in range(3):
            budget_data = {
                'name': f'Count Budget {i}',
                'scope_type': 'user',
                'scope_id': 200 + i,
                'period_type': 'daily',
                'total_tokens': 10000,
                'priority': 5
            }
            budget_schema = TokenBudgetCreate(**budget_data)
            await repository.create(budget_schema, test_db_session)

        total_count = await repository.count(test_db_session)
        active_count = await repository.count(test_db_session, status='active')

        assert total_count >= 4  # sample + 3 new
        assert active_count >= 4

    @pytest.mark.asyncio
    async def test_exists_by_scope(self, repository: SQLAlchemyTokenBudgetRepository, test_db_session: AsyncSession, sample_token_budget: TokenBudget):
        """Test checking if budget exists by scope."""
        exists = await repository.exists_by_scope(
            sample_token_budget.scope_type,
            sample_token_budget.scope_id,
            test_db_session
        )

        assert exists is True

        # Test non-existent scope
        not_exists = await repository.exists_by_scope('organization', 99999, test_db_session)
        assert not_exists is False


class TestTokenQuotaRepository:
    """Test suite for TokenQuotaRepository."""

    @pytest.fixture
    def repository(self):
        """Get repository instance."""
        return SQLAlchemyTokenQuotaRepository()

    @pytest.mark.asyncio
    async def test_create_quota(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota_data: dict, test_user):
        """Test creating a new token quota."""
        from app.schemas.token_quota import TokenQuotaCreate

        create_schema = TokenQuotaCreate(**sample_token_quota_data)
        quota = await repository.create(create_schema, test_db_session)

        assert quota.id is not None
        assert quota.user_id == sample_token_quota_data['user_id']
        assert quota.name == sample_token_quota_data['name']
        assert quota.total_tokens == sample_token_quota_data['total_tokens']
        assert quota.used_tokens == 0
        assert quota.remaining_tokens == sample_token_quota_data['total_tokens']

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test retrieving quota by ID."""
        quota = await repository.get_by_id(sample_token_quota.id, test_db_session)

        assert quota is not None
        assert quota.id == sample_token_quota.id
        assert quota.name == sample_token_quota.name

    @pytest.mark.asyncio
    async def test_get_by_user(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test retrieving quotas by user."""
        quotas = await repository.get_by_user(sample_token_quota.user_id, test_db_session)

        assert len(quototas) >= 1
        assert sample_token_quota in quotas

    @pytest.mark.asyncio
    async def test_get_active_quotas(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test retrieving active quotas."""
        active_quotas = await repository.get_active_quotas(test_db_session)

        assert len(active_quotas) >= 1
        assert all(q.status == 'active' for q in active_quotas)

    @pytest.mark.asyncio
    async def test_update_quota(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test updating a quota."""
        updates = {
            'name': 'Updated Quota Name',
            'total_tokens': 200000,
            'priority': 8
        }

        updated_quota = await repository.update(sample_token_quota.id, updates, test_db_session)

        assert updated_quota.name == 'Updated Quota Name'
        assert updated_quota.total_tokens == 200000
        assert updated_quota.priority == 8

    @pytest.mark.asyncio
    async def test_update_usage(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test updating quota usage."""
        tokens_used = 25000

        updated_quota = await repository.update_usage(sample_token_quota.id, tokens_used, test_db_session)

        assert updated_quota.used_tokens == tokens_used
        assert updated_quota.remaining_tokens == sample_token_quota.total_tokens - tokens_used

    @pytest.mark.asyncio
    async def test_reset_quota_period(self, repository: SQLAlchemyTokenQuotaRepository, test_db_session: AsyncSession, sample_token_quota: TokenQuota):
        """Test resetting quota period."""
        # Use some tokens first
        await repository.update_usage(sample_token_quota.id, 30000, test_db_session)

        # Reset period
        new_start = datetime.utcnow()
        new_end = new_start + timedelta(days=1)

        reset_quota = await repository.reset_period(
            sample_token_quota.id,
            new_start,
            new_end,
            test_db_session
        )

        assert reset_quota.used_tokens == 0
        assert reset_quota.remaining_tokens == reset_quota.total_tokens
        assert reset_quota.status == 'active'


class TestTokenAlertRepository:
    """Test suite for TokenAlertRepository."""

    @pytest.fixture
    def repository(self):
        """Get repository instance."""
        return SQLAlchemyTokenAlertRepository()

    @pytest.mark.asyncio
    async def test_create_alert(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert_data: dict):
        """Test creating a new token alert."""
        from app.schemas.token_alert import TokenAlertCreate

        create_schema = TokenAlertCreate(**sample_token_alert_data)
        alert = await repository.create(create_schema, test_db_session)

        assert alert.id is not None
        assert alert.alert_type == sample_token_alert_data['alert_type']
        assert alert.severity == sample_token_alert_data['severity']
        assert alert.is_acknowledged is False

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert: TokenAlert):
        """Test retrieving alert by ID."""
        alert = await repository.get_by_id(sample_token_alert.id, test_db_session)

        assert alert is not None
        assert alert.id == sample_token_alert.id
        assert alert.alert_type == sample_token_alert.alert_type

    @pytest.mark.asyncio
    async def test_get_by_budget(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert: TokenAlert):
        """Test retrieving alerts by budget."""
        alerts = await repository.get_by_budget(sample_token_alert.budget_id, test_db_session)

        assert len(alerts) >= 1
        assert sample_token_alert in alerts

    @pytest.mark.asyncio
    async def test_get_unacknowledged_alerts(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert: TokenAlert):
        """Test retrieving unacknowledged alerts."""
        unacknowledged = await repository.get_unacknowledged_alerts(test_db_session)

        assert len(unacknowledged) >= 1
        assert all(a.is_acknowledged is False for a in unacknowledged)

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert: TokenAlert, test_user):
        """Test acknowledging an alert."""
        acknowledged_alert = await repository.acknowledge_alert(
            sample_token_alert.id,
            test_user.id,
            test_db_session
        )

        assert acknowledged_alert.is_acknowledged is True
        assert acknowledged_alert.acknowledged_by == test_user.id
        assert acknowledged_alert.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_get_critical_alerts(self, repository: SQLAlchemyTokenAlertRepository, test_db_session: AsyncSession, sample_token_alert: TokenAlert):
        """Test retrieving critical alerts."""
        critical_alerts = await repository.get_critical_alerts(test_db_session)

        assert isinstance(critical_alerts, list)
        # Sample alert has 'warning' severity, so might not be in critical list
