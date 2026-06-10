"""add_monitoring_tables

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-06-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, Sequence[str], None] = ['m6o7p8q9r0s1', 'n2o3p4q5r6s7']
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_monitoring table
    op.create_table(
        'agent_monitoring',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('check_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('metrics', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('alerts_generated', postgresql.JSONB(), nullable=True),
        sa.Column('report_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_monitoring_check_time', 'agent_monitoring', ['check_time'])
    op.create_index('ix_agent_monitoring_status', 'agent_monitoring', ['status'])
    op.create_index('ix_agent_monitoring_created_at', 'agent_monitoring', ['created_at'])

    # Create agent_alerts table
    op.create_table(
        'agent_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metrics_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('acknowledged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_alerts_alert_type', 'agent_alerts', ['alert_type'])
    op.create_index('ix_agent_alerts_severity', 'agent_alerts', ['severity'])
    op.create_index('ix_agent_alerts_acknowledged', 'agent_alerts', ['acknowledged'])
    op.create_index('ix_agent_alerts_created_at', 'agent_alerts', ['created_at'])

    # Create alert_configurations table
    op.create_table(
        'alert_configurations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('condition_json', postgresql.JSONB(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cooldown_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_configurations_alert_type', 'alert_configurations', ['alert_type'])
    op.create_index('ix_alert_configurations_enabled', 'alert_configurations', ['enabled'])
    op.create_index('ix_alert_configurations_created_by', 'alert_configurations', ['created_by'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_alert_configurations_created_by', table_name='alert_configurations')
    op.drop_index('ix_alert_configurations_enabled', table_name='alert_configurations')
    op.drop_index('ix_alert_configurations_alert_type', table_name='alert_configurations')
    op.drop_table('alert_configurations')

    op.drop_index('ix_agent_alerts_created_at', table_name='agent_alerts')
    op.drop_index('ix_agent_alerts_acknowledged', table_name='agent_alerts')
    op.drop_index('ix_agent_alerts_severity', table_name='agent_alerts')
    op.drop_index('ix_agent_alerts_alert_type', table_name='agent_alerts')
    op.drop_table('agent_alerts')

    op.drop_index('ix_agent_monitoring_created_at', table_name='agent_monitoring')
    op.drop_index('ix_agent_monitoring_status', table_name='agent_monitoring')
    op.drop_index('ix_agent_monitoring_check_time', table_name='agent_monitoring')
    op.drop_table('agent_monitoring')
