"""add review_status columns to test_definitions and test_suites

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d4
Create Date: 2026-05-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # test_definitions: add review columns
    op.add_column('test_definitions', sa.Column('review_status', sa.String(20), nullable=False, server_default='draft'))
    op.add_column('test_definitions', sa.Column('reviewed_by', sa.Integer(), nullable=True))
    op.add_column('test_definitions', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('test_definitions', sa.Column('rejection_reason', sa.Text(), nullable=True))

    # Data migration: already published tests get 'approved' status
    op.execute(
        "UPDATE test_definitions SET review_status = 'approved' WHERE is_draft = false"
    )

    # test_suites: add review columns
    op.add_column('test_suites', sa.Column('review_status', sa.String(20), nullable=False, server_default='draft'))
    op.add_column('test_suites', sa.Column('reviewed_by', sa.String(100), nullable=True))
    op.add_column('test_suites', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('test_suites', sa.Column('rejection_reason', sa.Text(), nullable=True))

    # Data migration: all existing suites are grandfathered as approved
    op.execute(
        "UPDATE test_suites SET review_status = 'approved'"
    )


def downgrade() -> None:
    op.drop_column('test_suites', 'rejection_reason')
    op.drop_column('test_suites', 'reviewed_at')
    op.drop_column('test_suites', 'reviewed_by')
    op.drop_column('test_suites', 'review_status')

    op.drop_column('test_definitions', 'rejection_reason')
    op.drop_column('test_definitions', 'reviewed_at')
    op.drop_column('test_definitions', 'reviewed_by')
    op.drop_column('test_definitions', 'review_status')
