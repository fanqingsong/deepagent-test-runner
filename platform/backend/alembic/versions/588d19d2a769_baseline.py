"""baseline - create all base tables from SQLAlchemy models

Revision ID: 588d19d2a769
Revises:
Create Date: 2026-05-21 01:19:36.387679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '588d19d2a769'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import Base and all models to ensure they're registered
    from app.core.database import Base
    # Import models directly from their modules to avoid import issues
    from app.models.user import User
    from app.models.role import Role, Permission
    from app.models.app import App
    # Note: app_permissions is created by migration a1b2c3d4e5f6
    from app.models.test_definition import TestDefinition
    from app.models.test_step import TestStep
    from app.models.test_version import TestVersion
    from app.models.test_suite import TestSuite
    from app.models.schedule import Schedule
    from app.models.test_run import TestRun
    from app.models.test_case import TestCase
    # Note: suite_runs and suite_run_entries are created by migration b2c3d4e5f6a1
    from app.models.run_config import RunConfig
    from app.models.conversation import ConversationThread, ConversationMessage
    from app.models.llm_usage import LlmUsage
    from app.models.auth import UserSession, MFASecret, EmailToken, AuditLog

    # Create base tables (excluding those created by other migrations)
    op.execute("CREATE TABLE IF NOT EXISTS users ("
               "id SERIAL PRIMARY KEY, "
               "username VARCHAR(100) NOT NULL UNIQUE, "
               "email VARCHAR(255) NOT NULL UNIQUE, "
               "hashed_password VARCHAR(255) NOT NULL, "
               "full_name VARCHAR(255), "
               "is_active BOOLEAN NOT NULL DEFAULT TRUE, "
               "is_superuser BOOLEAN NOT NULL DEFAULT FALSE, "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS conversation_threads ("
               "id SERIAL PRIMARY KEY, "
               "title VARCHAR(255), "
               "status VARCHAR(20) NOT NULL DEFAULT 'active', "
               "metadata JSONB DEFAULT '{}', "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS conversation_messages ("
               "id SERIAL PRIMARY KEY, "
               "thread_id INTEGER NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE, "
               "role VARCHAR(20) NOT NULL, "
               "content TEXT NOT NULL, "
               "metadata JSONB DEFAULT '{}', "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS apps ("
               "id SERIAL PRIMARY KEY, "
               "name VARCHAR(255) NOT NULL, "
               "description TEXT, "
               "url VARCHAR(500), "
               "status VARCHAR(20) NOT NULL DEFAULT 'draft', "
               "test_goal TEXT, "
               "test_context JSONB DEFAULT '{}', "
               "current_plan JSONB DEFAULT '{}', "
               "conversation_thread_id INTEGER REFERENCES conversation_threads(id) ON DELETE SET NULL, "
               "test_definition_id INTEGER, "
               "latest_run_id VARCHAR(100), "
               "latest_result JSONB DEFAULT '{}', "
               "iteration_count INTEGER NOT NULL DEFAULT 0, "
               "icon VARCHAR(50) NOT NULL DEFAULT 'test-tube', "
               "color VARCHAR(20) NOT NULL DEFAULT '#0f62fe', "
               "created_by INTEGER REFERENCES users(id), "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_definitions ("
               "id SERIAL PRIMARY KEY, "
               "name VARCHAR(255) NOT NULL, "
               "description TEXT, "
               "test_id VARCHAR(100) UNIQUE NOT NULL, "
               "url VARCHAR(500), "
               "environment JSONB DEFAULT '{}', "
               "tags TEXT[] DEFAULT '{}', "
               "test_goal TEXT, "
               "test_context JSONB DEFAULT '{}', "
               "plan_generation_status VARCHAR(20) DEFAULT 'pending', "
               "ai_generated_plan JSONB DEFAULT '{}', "
               "plan_metadata JSONB DEFAULT '{}', "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "updated_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "created_by INTEGER REFERENCES users(id), "
               "version INTEGER DEFAULT 1, "
               "is_active BOOLEAN DEFAULT TRUE, "
               "is_regression BOOLEAN DEFAULT FALSE, "
               "regression_source_run_id VARCHAR(100), "
               "is_draft BOOLEAN DEFAULT FALSE, "
               "source_app_id INTEGER REFERENCES apps(id) ON DELETE SET NULL"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_steps ("
               "id SERIAL PRIMARY KEY, "
               "test_definition_id INTEGER NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE, "
               "step_order INTEGER NOT NULL, "
               "action VARCHAR(100) NOT NULL, "
               "target VARCHAR(255), "
               "value TEXT, "
               "expected_result TEXT, "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_versions ("
               "id SERIAL PRIMARY KEY, "
               "test_definition_id INTEGER NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE, "
               "version_number INTEGER NOT NULL, "
               "description TEXT, "
               "created_by INTEGER REFERENCES users(id), "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_suites ("
               "id SERIAL PRIMARY KEY, "
               "name VARCHAR(255) NOT NULL, "
               "description TEXT, "
               "created_by INTEGER REFERENCES users(id), "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW(), "
               "updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS schedules ("
               "id SERIAL PRIMARY KEY, "
               "test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE SET NULL, "
               "test_suite_id INTEGER REFERENCES test_suites(id) ON DELETE SET NULL, "
               "cron_expression VARCHAR(100) NOT NULL, "
               "is_active BOOLEAN NOT NULL DEFAULT TRUE, "
               "next_run_time TIMESTAMP, "
               "last_run_time TIMESTAMP, "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_runs ("
               "id VARCHAR(100) PRIMARY KEY, "
               "test_definition_id INTEGER NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE, "
               "status VARCHAR(20) NOT NULL DEFAULT 'pending', "
               "total_tests INTEGER NOT NULL DEFAULT 0, "
               "passed_tests INTEGER NOT NULL DEFAULT 0, "
               "failed_tests INTEGER NOT NULL DEFAULT 0, "
               "skipped_tests INTEGER NOT NULL DEFAULT 0, "
               "total_duration_ms INTEGER, "
               "error_message TEXT, "
               "start_time TIMESTAMP, "
               "end_time TIMESTAMP, "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    op.execute("CREATE TABLE IF NOT EXISTS test_cases ("
               "id SERIAL PRIMARY KEY, "
               "run_id VARCHAR(100) NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE, "
               "test_definition_id INTEGER NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE, "
               "step_order INTEGER NOT NULL, "
               "action VARCHAR(100) NOT NULL, "
               "target VARCHAR(255), "
               "value TEXT, "
               "status VARCHAR(20) NOT NULL DEFAULT 'pending', "
               "error_message TEXT, "
               "screenshot_path VARCHAR(500), "
               "duration INTEGER, "
               "created_at TIMESTAMP NOT NULL DEFAULT NOW()"
               ")")

    # Note: suite_runs and suite_run_entries are created by migration b2c3d4e5f6a1
    # Note: run_configs is created by migration d4e5f6a7b8c3
    # Note: llm_usage is created by migration 9c085b1cef6e

    # Create indexes (excluding those created by other migrations)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversation_messages_thread_id ON conversation_messages(thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_apps_created_by ON apps(created_by)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_apps_created_by ON apps(created_by)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_definitions_test_id ON test_definitions(test_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_definitions_source_app_id ON test_definitions(source_app_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_steps_test_definition_id ON test_steps(test_definition_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_schedules_test_definition_id ON schedules(test_definition_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_schedules_test_suite_id ON schedules(test_suite_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_runs_test_definition_id ON test_runs(test_definition_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_runs_status ON test_runs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_runs_created_at ON test_runs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_cases_run_id ON test_cases(run_id)")
    # Note: suite_runs indexes are created by migration b2c3d4e5f6a1
    # Note: llm_usage indexes are created by migration 9c085b1cef6e


def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key constraints
    # Note: suite_run_entries and suite_runs are dropped by their own migration
    # Note: run_configs and llm_usage are dropped by their own migrations
    tables = [
        'test_cases', 'test_runs',
        'schedules', 'test_steps', 'test_versions', 'test_definitions',
        'test_suites', 'apps', 'conversation_messages',
        'conversation_threads'
    ]

    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("DROP TABLE IF EXISTS users CASCADE")
