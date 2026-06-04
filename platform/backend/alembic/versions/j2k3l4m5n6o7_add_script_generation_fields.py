"""add script generation fields

Revision ID: j2k3l4m5n6o7
Revises: i0j1k2l3m4n5
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "j2k3l4m5n6o7"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_definitions",
        sa.Column("execution_mode", sa.String(20), nullable=False, server_default="nl_steps"),
    )
    op.add_column(
        "test_definitions",
        sa.Column("playwright_script", sa.Text(), nullable=True),
    )
    op.add_column(
        "test_definitions",
        sa.Column("script_status", sa.String(20), nullable=False, server_default="none"),
    )
    op.add_column(
        "test_definitions",
        sa.Column("script_metadata", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("test_definitions", "script_metadata")
    op.drop_column("test_definitions", "script_status")
    op.drop_column("test_definitions", "playwright_script")
    op.drop_column("test_definitions", "execution_mode")
