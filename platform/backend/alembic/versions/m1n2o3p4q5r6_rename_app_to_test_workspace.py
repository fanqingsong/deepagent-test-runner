"""rename app to test_workspace

Revision ID: m1n2o3p4q5r6
Revises: l5n6o7p8q9r0
Create Date: 2026-06-07

Renames app table to test_workspace for better semantics.
"""
from alembic import op
import sqlalchemy as sa

revision = "m1n2o3p4q5r6"
down_revision = "l5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Rename tables
    op.rename_table('apps', 'test_workspace')
    op.rename_table('app_permissions', 'test_workspace_permissions')

    # Step 2: Rename columns in test_workspace_permissions
    op.alter_column('test_workspace_permissions', 'app_id',
                       new_column_name='workspace_id',
                       existing_type=sa.Integer(), nullable=False)

    # Step 3: Rename columns in test_definitions
    op.alter_column('test_definitions', 'source_app_id',
                       new_column_name='source_workspace_id',
                       existing_type=sa.Integer(), nullable=True)

    # Step 4: Update foreign key constraints in test_workspace_permissions
    # First drop existing foreign key constraints
    op.execute('ALTER TABLE test_workspace_permissions DROP CONSTRAINT IF EXISTS test_workspace_permissions_app_id_fkey')
    op.execute('ALTER TABLE test_workspace_permissions DROP CONSTRAINT IF EXISTS test_workspace_permissions_app_id_fkey')

    # Create new foreign key
    op.execute('ALTER TABLE test_workspace_permissions ADD CONSTRAINT test_workspace_permissions_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES test_workspace(id) ON DELETE CASCADE')

    # Step 5: Update foreign key constraints in test_definitions
    op.execute('ALTER TABLE test_definitions DROP CONSTRAINT IF EXISTS test_definitions_source_app_id_fkey')
    op.execute('ALTER TABLE test_definitions DROP CONSTRAINT IF EXISTS test_definitions_source_app_id_fkey')

    op.execute('ALTER TABLE test_definitions ADD CONSTRAINT test_definitions_source_workspace_id_fkey FOREIGN KEY (source_workspace_id) REFERENCES test_workspace(id) ON DELETE SET NULL')

    # Step 6: Rename sequence
    op.execute('ALTER SEQUENCE apps_id_seq RENAME TO test_workspace_id_seq')

    # Step 7: Rename indexes
    op.execute('ALTER INDEX IF EXISTS ix_apps_created_by RENAME TO ix_test_workspace_created_by')
    op.execute('ALTER INDEX IF EXISTS idx_apps_status RENAME TO idx_test_workspace_status')


def downgrade():
    # Reverse all changes
    op.rename_table('test_workspace', 'apps')
    op.rename_table('test_workspace_permissions', 'app_permissions')

    op.alter_column('test_workspace_permissions', 'workspace_id',
                       new_column_name='app_id',
                       existing_type=sa.Integer(), nullable=False)
    op.alter_column('test_definitions', 'source_workspace_id',
                       new_column_name='source_app_id',
                       existing_type=sa.Integer(), nullable=True)

    # Restore foreign key constraints
    op.execute('ALTER TABLE test_workspace_permissions DROP CONSTRAINT IF EXISTS test_workspace_permissions_workspace_id_fkey')
    op.execute('ALTER TABLE test_workspace_permissions ADD CONSTRAINT test_workspace_permissions_app_id_fkey FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE')

    op.execute('ALTER TABLE test_definitions DROP CONSTRAINT IF EXISTS test_definitions_source_workspace_id_fkey')
    op.execute('ALTER TABLE test_definitions ADD CONSTRAINT test_definitions_source_app_id_fkey FOREIGN KEY (source_app_id) REFERENCES apps(id) ON DELETE SET NULL')

    op.execute('ALTER SEQUENCE test_workspace_id_seq RENAME TO apps_id_seq')

    op.execute('ALTER INDEX ix_test_workspace_created_by RENAME TO ix_apps_created_by')
    op.execute('ALTER INDEX IF EXISTS idx_test_workspace_status RENAME TO idx_apps_status')
