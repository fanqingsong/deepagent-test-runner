"""add_llm_usage_table

Revision ID: 9c085b1cef6e
Revises: h8b9c1d2e3f4
Create Date: 2026-05-27 15:41:18.311616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c085b1cef6e'
down_revision: Union[str, None] = 'h8b9c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_usage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prompt_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('duration_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('test_run_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_usage_created_at', 'llm_usage', ['created_at'])
    op.create_index('ix_llm_usage_agent_type_created_at', 'llm_usage', ['agent_type', 'created_at'])
    op.create_index('ix_llm_usage_user_id_created_at', 'llm_usage', ['user_id', 'created_at'])
    op.create_index('ix_llm_usage_test_run_id', 'llm_usage', ['test_run_id'])


def downgrade() -> None:
    op.drop_index('ix_llm_usage_test_run_id', table_name='llm_usage')
    op.drop_index('ix_llm_usage_user_id_created_at', table_name='llm_usage')
    op.drop_index('ix_llm_usage_agent_type_created_at', table_name='llm_usage')
    op.drop_index('ix_llm_usage_created_at', table_name='llm_usage')
    op.drop_table('llm_usage')
