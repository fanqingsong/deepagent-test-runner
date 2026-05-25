"""add review fields to test_versions

Revision ID: g7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g7a8b9c0d1e2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('test_versions', sa.Column('review_status', sa.String(20), nullable=False, server_default='draft'))
    op.add_column('test_versions', sa.Column('reviewed_by', sa.Integer(), nullable=True))
    op.add_column('test_versions', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('test_versions', sa.Column('rejection_reason', sa.Text(), nullable=True))

    op.create_foreign_key('fk_test_versions_reviewed_by', 'test_versions', 'users', ['reviewed_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_test_versions_reviewed_by', 'test_versions', type_='foreignkey')
    op.drop_column('test_versions', 'rejection_reason')
    op.drop_column('test_versions', 'reviewed_at')
    op.drop_column('test_versions', 'reviewed_by')
    op.drop_column('test_versions', 'review_status')
