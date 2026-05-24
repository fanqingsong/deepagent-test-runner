"""add setup/teardown test IDs to test_suites

Revision ID: e5f6a7b8c9d4
Revises: d4e5f6a7b8c3
Create Date: 2026-05-23

"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d4"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_suites",
        sa.Column("setup_test_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "test_suites",
        sa.Column("teardown_test_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_suites", "teardown_test_id")
    op.drop_column("test_suites", "setup_test_id")
