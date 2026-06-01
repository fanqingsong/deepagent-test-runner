#!/usr/bin/env bash
set -e

echo "=== Prestart: waiting for database ==="
python -c "
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import settings

# Convert async URL to sync for health check
url = settings.DATABASE_URL.replace('+asyncpg', '')
engine = create_engine(url)

for i in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Database is ready')
        break
    except Exception as e:
        if i == 59:
            print(f'Database not ready after 60s: {e}')
            sys.exit(1)
        print(f'Waiting for database... ({i+1}/60)')
        time.sleep(1)
"

echo "=== Prestart: running Alembic migrations ==="
# Try to run migrations, fall back to create_all() if they fail
if ! alembic upgrade head 2>/dev/null; then
    echo "=== Migrations failed, using SQLAlchemy create_all() ==="
    python -c "
import asyncio
from app.core.database import engine, Base
# Import all models to ensure they're registered with Base.metadata
from app.models.user import User
from app.models.role import Role, Permission
from app.models.app import App
from app.models.app_permission import AppPermission
from app.models.test_definition import TestDefinition
from app.models.test_step import TestStep
from app.models.test_version import TestVersion
from app.models.test_suite import TestSuite
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.models.test_case import TestCase
from app.models.suite_run import SuiteRun, SuiteRunEntry
from app.models.run_config import RunConfig
from app.models.conversation import ConversationThread, ConversationMessage
from app.models.llm_usage import LlmUsage
from app.models.auth import UserSession, MFASecret, EmailToken, AuditLog

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
"
    echo "=== Tables created via SQLAlchemy ==="
fi

echo "=== Prestart: complete ==="
