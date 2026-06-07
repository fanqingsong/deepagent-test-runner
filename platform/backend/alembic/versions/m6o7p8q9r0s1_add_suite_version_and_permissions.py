"""add suite version and permissions

Revision ID: m6o7p8q9r0s1
Revises: l5n6o7p8q9r0
Create Date: 2026-06-07

Add test_suite_versions and test_suite_permissions tables
for version control and access control of test suites.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m6o7p8q9r0s1"
down_revision = "l5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create test_suite_versions table
    op.create_table(
        'test_suite_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('test_suite_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=100), nullable=False, server_default='system'),
        sa.ForeignKeyConstraint(['test_suite_id'], ['test_suites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_test_suite_versions_test_suite_id', 'test_suite_versions', ['test_suite_id'])
    op.create_index('ix_test_suite_versions_version', 'test_suite_versions', ['version'])

    # Create test_suite_permissions table
    op.create_table(
        'test_suite_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('test_suite_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permission_type', sa.String(length=20), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['test_suite_id'], ['test_suites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_test_suite_permissions_test_suite_id', 'test_suite_permissions', ['test_suite_id'])
    op.create_index('ix_test_suite_permissions_user_id', 'test_suite_permissions', ['user_id'])
    op.create_unique_constraint('uq_test_suite_permissions_suite_user', 'test_suite_permissions', ['test_suite_id', 'user_id'])


def downgrade() -> None:
    op.drop_table('test_suite_permissions')
    op.drop_table('test_suite_versions')
