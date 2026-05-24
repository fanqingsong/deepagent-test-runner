"""add rbac tables (roles, permissions, user_roles, role_permissions)

Revision ID: b2c3d4e5f6g7
Revises: c3d4e5f6a7b2
Create Date: 2026-05-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'd4e5f6a7b8c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # asyncpg requires one statement per op.execute() call.
    # Use IF NOT EXISTS because tables may already exist from create_all().
    op.execute(
        "CREATE TABLE IF NOT EXISTS permissions ("
        "id SERIAL PRIMARY KEY, "
        "name VARCHAR(100) NOT NULL UNIQUE, "
        "description TEXT, "
        "resource VARCHAR(50) NOT NULL, "
        "action VARCHAR(50) NOT NULL, "
        "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_permissions_resource ON permissions(resource)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_permissions_action ON permissions(action)")

    op.execute(
        "CREATE TABLE IF NOT EXISTS roles ("
        "id SERIAL PRIMARY KEY, "
        "name VARCHAR(100) NOT NULL UNIQUE, "
        "description TEXT, "
        "is_system BOOLEAN NOT NULL DEFAULT FALSE, "
        "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
        "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )

    op.execute(
        "CREATE TABLE IF NOT EXISTS user_roles ("
        "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE, "
        "PRIMARY KEY (user_id, role_id)"
        ")"
    )

    op.execute(
        "CREATE TABLE IF NOT EXISTS role_permissions ("
        "role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE, "
        "permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE, "
        "PRIMARY KEY (role_id, permission_id)"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS user_roles")
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TABLE IF EXISTS permissions")
