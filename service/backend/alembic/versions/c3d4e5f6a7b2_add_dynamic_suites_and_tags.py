"""add dynamic suites and tags support

Revision ID: c3d4e5f6a7b2
Revises: b2c3d4e5f6a1
Create Date: 2026-05-23 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'c3d4e5f6a7b2'
down_revision: Union[str, None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('test_suites', sa.Column(
        'is_dynamic', sa.Boolean(), nullable=False,
        server_default='false'))
    op.add_column('test_suites', sa.Column(
        'dynamic_tag_rule', JSONB, nullable=False,
        server_default='{}'))


def downgrade() -> None:
    op.drop_column('test_suites', 'dynamic_tag_rule')
    op.drop_column('test_suites', 'is_dynamic')
