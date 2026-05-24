"""enhance test_suites and add suite_runs tables

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add execution config columns to test_suites
    op.add_column('test_suites', sa.Column(
        'execution_mode', sa.String(20), nullable=False,
        server_default='sequential'))
    op.add_column('test_suites', sa.Column(
        'max_concurrency', sa.Integer(), nullable=False,
        server_default='1'))
    op.add_column('test_suites', sa.Column(
        'fail_strategy', sa.String(20), nullable=False,
        server_default='continue'))
    op.add_column('test_suites', sa.Column(
        'retry_config', JSONB, nullable=False,
        server_default='{}'))
    op.add_column('test_suites', sa.Column(
        'environment_vars', JSONB, nullable=False,
        server_default='{}'))
    op.add_column('test_suites', sa.Column(
        'suite_entries', JSONB, nullable=False,
        server_default='[]'))

    # Create suite_runs table
    op.create_table(
        'suite_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('suite_id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('execution_mode', sa.String(20), nullable=False, server_default='sequential'),
        sa.Column('total_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('start_time', sa.BigInteger(), nullable=True),
        sa.Column('end_time', sa.BigInteger(), nullable=True),
        sa.Column('total_duration', sa.Integer(), nullable=True),
        sa.Column('environment', JSONB, nullable=False, server_default='{}'),
        sa.Column('triggered_by', sa.String(100), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['suite_id'], ['test_suites.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_suite_runs_suite_id', 'suite_runs', ['suite_id'])
    op.create_index('ix_suite_runs_run_id', 'suite_runs', ['run_id'], unique=True)

    # Create suite_run_entries table
    op.create_table(
        'suite_run_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('suite_run_id', sa.Integer(), nullable=False),
        sa.Column('test_definition_id', sa.Integer(), nullable=False),
        sa.Column('test_run_id', sa.String(100), nullable=True),
        sa.Column('entry_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('condition', sa.String(20), nullable=False, server_default='always'),
        sa.Column('started_at', sa.BigInteger(), nullable=True),
        sa.Column('finished_at', sa.BigInteger(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['suite_run_id'], ['suite_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_suite_run_entries_run_id', 'suite_run_entries', ['suite_run_id'])


def downgrade() -> None:
    op.drop_index('ix_suite_run_entries_run_id', table_name='suite_run_entries')
    op.drop_table('suite_run_entries')
    op.drop_index('ix_suite_runs_run_id', table_name='suite_runs')
    op.drop_index('ix_suite_runs_suite_id', table_name='suite_runs')
    op.drop_table('suite_runs')

    op.drop_column('test_suites', 'suite_entries')
    op.drop_column('test_suites', 'environment_vars')
    op.drop_column('test_suites', 'retry_config')
    op.drop_column('test_suites', 'fail_strategy')
    op.drop_column('test_suites', 'max_concurrency')
    op.drop_column('test_suites', 'execution_mode')
