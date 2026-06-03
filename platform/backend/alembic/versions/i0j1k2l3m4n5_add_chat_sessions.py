"""add_chat_sessions and thread_id on llm_usage

Revision ID: i0j1k2l3m4n5
Revises: a0b1c2d3e4f5
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'i0j1k2l3m4n5'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('langgraph_thread_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('subagents_used', postgresql.JSONB(), nullable=True, server_default='[]'),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_duration_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('langgraph_thread_id'),
    )
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    op.create_index('ix_chat_sessions_status', 'chat_sessions', ['status'])
    op.create_index('ix_chat_sessions_langgraph_thread_id', 'chat_sessions', ['langgraph_thread_id'])
    op.create_index('ix_chat_sessions_last_message_at', 'chat_sessions', ['last_message_at'])

    # 2. Add thread_id column to llm_usage
    op.add_column('llm_usage', sa.Column('thread_id', sa.String(length=100), nullable=True))
    op.create_index('ix_llm_usage_thread_id', 'llm_usage', ['thread_id'])


def downgrade() -> None:
    op.drop_index('ix_llm_usage_thread_id', table_name='llm_usage')
    op.drop_column('llm_usage', 'thread_id')

    op.drop_index('ix_chat_sessions_last_message_at', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_langgraph_thread_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_status', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_table('chat_sessions')
