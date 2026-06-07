"""Add permissions to existing version snapshots

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2025-06-07 10:30:00.000000

"""
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'n2o3p4q5r6s7'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    """Migrate existing snapshots to include permissions."""
    conn = op.get_bind()

    # Get all test_versions without permissions in snapshot
    # Using PostgreSQL JSONB operators
    result = conn.execute(text("""
        SELECT tv.id, tv.test_definition_id, tv.snapshot, tw.id as workspace_id
        FROM test_versions tv
        JOIN test_definitions td ON tv.test_definition_id = td.id
        JOIN test_workspace tw ON td.source_workspace_id = tw.id
        WHERE tv.snapshot IS NULL OR NOT (tv.snapshot ? 'permissions')
    """))

    rows = result.fetchall()
    migration_count = 0

    for row in rows:
        version_id = row.id
        test_definition_id = row.test_definition_id
        workspace_id = row.workspace_id
        snapshot = row.snapshot or {}

        # Load permissions for workspace
        perm_result = conn.execute(text("""
            SELECT twp.user_id, u.username, u.email, twp.permission_type
            FROM test_workspace_permissions twp
            JOIN users u ON twp.user_id = u.id
            WHERE twp.workspace_id = :workspace_id
        """), {"workspace_id": workspace_id})

        permissions = [
            {
                "user_id": p.user_id,
                "username": p.username,
                "email": p.email,
                "permission_type": p.permission_type
            }
            for p in perm_result
        ]

        # Update snapshot with permissions
        snapshot["permissions"] = permissions
        conn.execute(text("""
            UPDATE test_versions
            SET snapshot = CAST(:snapshot AS jsonb)
            WHERE id = :version_id
        """), {"snapshot": json.dumps(snapshot), "version_id": version_id})

        migration_count += 1

    print(f"Migrated {migration_count} version snapshots to include permissions")


def downgrade():
    """Remove permissions from all snapshots."""
    conn = op.get_bind()

    # Remove permissions key from all snapshots
    conn.execute(text("""
        UPDATE test_versions
        SET snapshot = snapshot - 'permissions'
        WHERE snapshot IS NOT NULL AND (snapshot ? 'permissions')
    """))

    print("Removed permissions from all version snapshots")
