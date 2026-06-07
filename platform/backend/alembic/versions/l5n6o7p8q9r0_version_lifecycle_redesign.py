"""version lifecycle redesign — consolidate draft versions

Revision ID: l5n6o7p8q9r0
Revises: k4m5n6o7p8q9
Create Date: 2026-06-07

Keep only the latest draft version per test_definition.
Set remaining drafts to version=0 (unassigned, will get a real number on submit).
"""

from alembic import op
import sqlalchemy as sa

revision = "l5n6o7p8q9r0"
down_revision = "k4m5n6o7p8q9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete all but the latest draft version per test_definition
    op.execute("""
        DELETE FROM test_versions tv1
        WHERE tv1.review_status = 'draft'
        AND EXISTS (
            SELECT 1 FROM test_versions tv2
            WHERE tv2.test_definition_id = tv1.test_definition_id
            AND tv2.review_status = 'draft'
            AND tv2.id > tv1.id
        )
    """)
    # Set remaining drafts to version=0 (unassigned)
    op.execute("""
        UPDATE test_versions SET version = 0
        WHERE review_status = 'draft'
    """)


def downgrade() -> None:
    # No-op: cannot reconstruct deleted draft versions
    pass
