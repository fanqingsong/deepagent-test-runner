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
alembic upgrade head

echo "=== Prestart: complete ==="
