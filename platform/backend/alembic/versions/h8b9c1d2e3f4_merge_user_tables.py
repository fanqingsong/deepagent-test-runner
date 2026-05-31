"""merge user_accounts and users tables

Revision ID: h8b9c1d2e3f4
Revises: g7a8b9c0d1e2
Create Date: 2026-05-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h8b9c1d2e3f4'
down_revision: Union[str, None] = 'g7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new columns to users table
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('status', sa.String(50), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))

    # Make username nullable
    op.alter_column('users', 'username', nullable=True)

    # Step 2: Migrate data from user_accounts to users
    op.execute("""
        UPDATE users u
        SET
            is_verified = COALESCE(ua.is_verified, false),
            status = COALESCE(ua.status, 'active'),
            mfa_enabled = COALESCE(ua.mfa_enabled, false),
            failed_login_attempts = COALESCE(ua.failed_login_attempts, 0),
            locked_until = ua.locked_until,
            last_login = ua.last_login,
            hashed_password = COALESCE(ua.password_hash, u.hashed_password)
        FROM (SELECT * FROM user_accounts) ua
        WHERE u.email = ua.email
    """)

    # Step 3: Update foreign key constraints on related tables
    # Drop old foreign keys
    op.drop_constraint('user_sessions_user_id_fkey', 'user_sessions', type_='foreignkey')
    op.drop_constraint('mfa_secrets_user_id_fkey', 'mfa_secrets', type_='foreignkey')
    op.drop_constraint('email_tokens_user_id_fkey', 'email_tokens', type_='foreignkey')
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')

    # Clean orphan records referencing users that no longer exist
    op.execute("DELETE FROM email_tokens WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute("DELETE FROM mfa_secrets WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute("DELETE FROM user_sessions WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute("UPDATE audit_logs SET user_id = NULL WHERE user_id NOT IN (SELECT id FROM users)")

    # Create new foreign keys pointing to users table
    op.create_foreign_key('user_sessions_user_id_fkey', 'user_sessions', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('mfa_secrets_user_id_fkey', 'mfa_secrets', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('email_tokens_user_id_fkey', 'email_tokens', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    # Step 4: Update schedules.created_by to use user_id instead of email
    # Add temporary column for migration
    op.add_column('schedules', sa.Column('created_by_new', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_schedules_created_by_new', 'schedules', 'users', ['created_by_new'], ['id'])

    # Migrate data from email to user_id
    op.execute("""
        UPDATE schedules s
        SET created_by_new = u.id
        FROM users u
        WHERE s.created_by = u.email AND s.created_by != 'system'
    """)

    # Drop old column and rename new one
    # Drop default constraint on created_by first
    op.execute("ALTER TABLE schedules ALTER COLUMN created_by DROP DEFAULT")
    op.drop_column('schedules', 'created_by')
    op.alter_column('schedules', 'created_by_new', new_column_name='created_by')

    # Step 5: Drop user_accounts table
    op.drop_table('user_accounts')


def downgrade() -> None:
    # Reverse: Recreate user_accounts table
    op.create_table(
        'user_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_accounts_email', 'user_accounts', ['email'], unique=True)
    op.create_index('ix_user_accounts_status', 'user_accounts', ['status'])

    # Migrate data back to user_accounts
    op.execute("""
        INSERT INTO user_accounts (email, password_hash, is_verified, status, mfa_enabled, failed_login_attempts, locked_until, created_at, last_login, updated_at)
        SELECT email, hashed_password, is_verified, status, mfa_enabled, failed_login_attempts, locked_until, created_at, last_login, updated_at
        FROM users
        ON CONFLICT (email) DO NOTHING
    """)

    # Restore foreign keys on related tables
    op.drop_constraint('user_sessions_user_id_fkey', 'user_sessions', type_='foreignkey')
    op.drop_constraint('mfa_secrets_user_id_fkey', 'mfa_secrets', type_='foreignkey')
    op.drop_constraint('email_tokens_user_id_fkey', 'email_tokens', type_='foreignkey')
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')

    op.create_foreign_key('user_sessions_user_id_fkey', 'user_sessions', 'user_accounts', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('mfa_secrets_user_id_fkey', 'mfa_secrets', 'user_accounts', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('email_tokens_user_id_fkey', 'email_tokens', 'user_accounts', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'user_accounts', ['user_id'], ['id'], ondelete='SET NULL')

    # Reverse schedules.created_by changes
    op.add_column('schedules', sa.Column('created_by_old', sa.String(length=100), nullable=True))
    op.execute("""
        UPDATE schedules s
        SET created_by_old = COALESCE(u.email, 'system')
        FROM users u
        WHERE s.created_by = u.id
    """)
    op.drop_constraint('fk_schedules_created_by_new', 'schedules', type_='foreignkey')
    op.drop_column('schedules', 'created_by')
    op.alter_column('schedules', 'created_by_old', new_column_name='created_by', server_default='system')

    # Drop new columns from users table
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'status')
    op.drop_column('users', 'is_verified')

    # Make username not nullable again
    op.alter_column('users', 'username', nullable=False)
