"""add run_configs table and run_config_id to schedules

Revision ID: d4e5f6a7b8c3
Revises: c3d4e5f6a7b2
Create Date: 2026-05-23

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "d4e5f6a7b8c3"
down_revision = "c3d4e5f6a7b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("browser_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("timeout_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("environment_vars", JSONB, nullable=False, server_default="{}"),
        sa.Column("retry_policy", JSONB, nullable=False, server_default="{}"),
        sa.Column("execution_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "schedules",
        sa.Column("run_config_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_schedules_run_config_id",
        "schedules", "run_configs",
        ["run_config_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_schedules_run_config_id", "schedules", type_="foreignkey")
    op.drop_column("schedules", "run_config_id")
    op.drop_table("run_configs")
