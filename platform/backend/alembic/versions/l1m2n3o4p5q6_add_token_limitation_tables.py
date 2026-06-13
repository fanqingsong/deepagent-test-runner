"""add_token_limitation_tables

Revision ID: l1m2n3o4p5q6
Revises: j1k2l3m4n5o6
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'l1m2n3o4p5q6'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create token_budgets table
    op.create_table(
        'token_budgets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('scope_type', sa.String(length=50), nullable=False, comment='organization, suite, test, user'),
        sa.Column('scope_id', sa.Integer(), nullable=True, comment='ID of the scoped entity'),
        sa.Column('parent_budget_id', sa.Integer(), nullable=True, comment='Parent budget for inheritance'),
        sa.Column('period_type', sa.String(length=20), nullable=False, server_default='monthly', comment='hourly, daily, weekly, monthly, custom'),
        sa.Column('period_start', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('used_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('remaining_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5', comment='1-10, higher = more important'),
        sa.Column('enforcement_mode', sa.String(length=20), nullable=False, server_default='soft', comment='soft (warn), hard (block), monitoring (track only)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active', comment='active, inactive, exhausted'),
        sa.Column('inherit_from_parent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('inherit_strategy', sa.String(length=50), nullable=True, comment='inherit_percentage, inherit_absolute, cascade'),
        sa.Column('alert_thresholds', JSONB(), nullable=True, server_default=sa.text('\'{"warning": 80, "critical": 90, "emergency": 95}\'::jsonb')),
        sa.Column('metadata', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_reset_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_budget_id'], ['token_budgets.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='Hierarchical budget structure for token usage control'
    )
    op.create_index('ix_token_budgets_scope_type_scope_id', 'token_budgets', ['scope_type', 'scope_id'])
    op.create_index('ix_token_budgets_parent_id', 'token_budgets', ['parent_budget_id'])
    op.create_index('ix_token_budgets_status', 'token_budgets', ['status'])
    op.create_index('ix_token_budgets_period_start_end', 'token_budgets', ['period_start', 'period_end'])
    op.create_index('ix_token_budgets_priority_status', 'token_budgets', ['priority', 'status'])

    # Create token_quotas table
    op.create_table(
        'token_quotas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User this quota applies to'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('period_type', sa.String(length=20), nullable=False, server_default='daily', comment='daily, weekly, monthly'),
        sa.Column('reset_strategy', sa.String(length=20), nullable=False, server_default='calendar', comment='rolling, calendar'),
        sa.Column('period_start', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('used_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('remaining_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5', comment='1-10, higher = more important'),
        sa.Column('enforcement_mode', sa.String(length=20), nullable=False, server_default='soft', comment='soft (warn), hard (block), monitoring (track only)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active', comment='active, inactive, exhausted'),
        sa.Column('alert_thresholds', JSONB(), nullable=True, server_default=sa.text('\'{"warning": 80, "critical": 90, "emergency": 95}\'::jsonb')),
        sa.Column('metadata', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_reset_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='User-specific time-based quotas for token usage control'
    )
    op.create_index('ix_token_quotas_user_id', 'token_quotas', ['user_id'])
    op.create_index('ix_token_quotas_period_type_status', 'token_quotas', ['period_type', 'status'])
    op.create_index('ix_token_quotas_reset_period_start_end', 'token_quotas', ['period_start', 'period_end'])

    # Create token_alerts table
    op.create_table(
        'token_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False, comment='budget_warning, budget_exceeded, quota_warning, quota_exceeded, enforcement_action'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning', comment='info, warning, critical, emergency'),
        sa.Column('budget_id', sa.Integer(), nullable=True, comment='Budget that triggered this alert'),
        sa.Column('quota_id', sa.Integer(), nullable=True, comment='Quota that triggered this alert'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='User associated with this alert'),
        sa.Column('threshold_type', sa.String(length=20), nullable=False, server_default='percentage', comment='percentage, absolute'),
        sa.Column('threshold_value', sa.Float(), nullable=False, server_default=0.0, comment='Threshold that was triggered'),
        sa.Column('current_value', sa.Float(), nullable=False, server_default=0.0, comment='Current value when alert triggered'),
        sa.Column('metrics_snapshot', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Snapshot of metrics at alert time'),
        sa.Column('message', sa.Text(), nullable=False, comment='Human-readable alert message'),
        sa.Column('details', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Additional alert details'),
        sa.Column('enforcement_action', sa.String(length=50), nullable=True, comment='Action taken: blocked, warning_logged, monitoring_only'),
        sa.Column('enforcement_result', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Result of enforcement action'),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false', comment='Whether alert has been acknowledged'),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True, comment='User who acknowledged the alert'),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True, comment='When alert was acknowledged'),
        sa.Column('notifications_sent', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Track notification delivery'),
        sa.Column('notification_errors', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Track notification failures'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='When alert was resolved'),
        sa.ForeignKeyConstraint(['budget_id'], ['token_budgets.id'], ),
        sa.ForeignKeyConstraint(['quota_id'], ['token_quotas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='Alerts for budget/quota usage thresholds and enforcement actions'
    )
    op.create_index('ix_token_alerts_budget_id', 'token_alerts', ['budget_id'])
    op.create_index('ix_token_alerts_quota_id', 'token_alerts', ['quota_id'])
    op.create_index('ix_token_alerts_user_id', 'token_alerts', ['user_id'])
    op.create_index('ix_token_alerts_severity', 'token_alerts', ['severity'])
    op.create_index('ix_token_alerts_alert_type_created_at', 'token_alerts', ['alert_type', 'created_at'])
    op.create_index('ix_token_alerts_acknowledged', 'token_alerts', ['is_acknowledged'])

    # Enhance llm_usage table with new columns
    op.add_column('llm_usage', sa.Column('budget_id', sa.Integer(), nullable=True, comment='Associated budget for this usage'))
    op.add_column('llm_usage', sa.Column('quota_id', sa.Integer(), nullable=True, comment='Associated quota for this usage'))
    op.add_column('llm_usage', sa.Column('cost_rmb', sa.Float(), nullable=True, comment='Cost in RMB for this usage'))
    op.add_column('llm_usage', sa.Column('priority', sa.Integer(), nullable=True, comment='Priority level (1-10) if applicable'))
    op.add_column('llm_usage', sa.Column('enforcement_action', sa.String(length=50), nullable=True, comment='Enforcement action: allowed, blocked, warning'))
    op.add_column('llm_usage', sa.Column('enforcement_details', JSONB(), nullable=True, server_default=sa.text('\'{}\'::jsonb'), comment='Details about enforcement decision'))

    # Create foreign key constraints for llm_usage
    op.create_foreign_key(
        'fk_llm_usage_budget_id',
        'llm_usage', 'token_budgets',
        ['budget_id'], ['id']
    )
    op.create_foreign_key(
        'fk_llm_usage_quota_id',
        'llm_usage', 'token_quotas',
        ['quota_id'], ['id']
    )

    # Create new indexes for llm_usage
    op.create_index('ix_llm_usage_budget_id', 'llm_usage', ['budget_id'])
    op.create_index('ix_llm_usage_quota_id', 'llm_usage', ['quota_id'])


def downgrade() -> None:
    # Remove indexes from llm_usage
    op.drop_index('ix_llm_usage_quota_id', table_name='llm_usage')
    op.drop_index('ix_llm_usage_budget_id', table_name='llm_usage')

    # Remove foreign keys from llm_usage
    op.drop_constraint('fk_llm_usage_quota_id', 'llm_usage', type_='foreignkey')
    op.drop_constraint('fk_llm_usage_budget_id', 'llm_usage', type_='foreignkey')

    # Remove columns from llm_usage
    op.drop_column('llm_usage', 'enforcement_details')
    op.drop_column('llm_usage', 'enforcement_action')
    op.drop_column('llm_usage', 'priority')
    op.drop_column('llm_usage', 'cost_rmb')
    op.drop_column('llm_usage', 'quota_id')
    op.drop_column('llm_usage', 'budget_id')

    # Drop token_alerts table
    op.drop_index('ix_token_alerts_acknowledged', table_name='token_alerts')
    op.drop_index('ix_token_alerts_alert_type_created_at', table_name='token_alerts')
    op.drop_index('ix_token_alerts_severity', table_name='token_alerts')
    op.drop_index('ix_token_alerts_user_id', table_name='token_alerts')
    op.drop_index('ix_token_alerts_quota_id', table_name='token_alerts')
    op.drop_index('ix_token_alerts_budget_id', table_name='token_alerts')
    op.drop_table('token_alerts')

    # Drop token_quotas table
    op.drop_index('ix_token_quotas_reset_period_start_end', table_name='token_quotas')
    op.drop_index('ix_token_quotas_period_type_status', table_name='token_quotas')
    op.drop_index('ix_token_quotas_user_id', table_name='token_quotas')
    op.drop_table('token_quotas')

    # Drop token_budgets table
    op.drop_index('ix_token_budgets_priority_status', table_name='token_budgets')
    op.drop_index('ix_token_budgets_period_start_end', table_name='token_budgets')
    op.drop_index('ix_token_budgets_status', table_name='token_budgets')
    op.drop_index('ix_token_budgets_parent_id', table_name='token_budgets')
    op.drop_index('ix_token_budgets_scope_type_scope_id', table_name='token_budgets')
    op.drop_table('token_budgets')
