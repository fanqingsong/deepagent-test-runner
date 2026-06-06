"""remove planner fields from test_definitions and apps

Revision ID: k4m5n6o7p8q9
Revises: j2k3l4m5n6o7
Create Date: 2026-06-06

Remove ai_generated_plan, plan_generation_status, plan_metadata
from test_definitions and current_plan from apps.
"""

from alembic import op
import sqlalchemy as sa

revision = "k4m5n6o7p8q9"
down_revision = "j2k3l4m5n6o7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("test_definitions", "ai_generated_plan")
    op.drop_column("test_definitions", "plan_generation_status")
    op.drop_column("test_definitions", "plan_metadata")
    op.drop_column("apps", "current_plan")


def downgrade() -> None:
    op.add_column(
        "apps",
        sa.Column("current_plan", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "test_definitions",
        sa.Column("plan_metadata", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "test_definitions",
        sa.Column("plan_generation_status", sa.String(20), server_default="pending", nullable=False),
    )
    op.add_column(
        "test_definitions",
        sa.Column("ai_generated_plan", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
    )
