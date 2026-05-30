"""add_email_sent_log_table

Revision ID: a0b1c2d3e4f5
Revises: 9c085b1cef6e
Create Date: 2026-05-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = '9c085b1cef6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_sent_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('to_email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body_preview', sa.String(length=200), nullable=True),
        sa.Column('cc', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='sent'),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('sent_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_email_sent_log_sender_id', 'email_sent_log', ['sender_id'])
    op.create_index('ix_email_sent_log_sent_at', 'email_sent_log', ['sent_at'])


def downgrade() -> None:
    op.drop_index('ix_email_sent_log_sent_at', table_name='email_sent_log')
    op.drop_index('ix_email_sent_log_sender_id', table_name='email_sent_log')
    op.drop_table('email_sent_log')
