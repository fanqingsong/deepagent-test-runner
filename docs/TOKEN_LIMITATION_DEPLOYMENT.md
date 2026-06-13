# Token Limitation Deployment Guide

## Table of Contents

1. [Installation Steps](#installation-steps)
2. [Database Migration](#database-migration)
3. [Configuration Options](#configuration-options)
4. [Environment Variables](#environment-variables)
5. [Health Checks](#health-checks)
6. [Monitoring Setup](#monitoring-setup)
7. [Rollback Procedures](#rollback-procedures)
8. [Performance Tuning](#performance-tuning)

## Installation Steps

### Prerequisites

Before deploying the Token Limitation System, ensure:

- **Python**: 3.11 or higher
- **PostgreSQL**: 14 or higher
- **Docker**: 20.10 or higher (for containerized deployment)
- **Redis**: 6 or higher (for caching)
- **Memory**: Minimum 4GB RAM, 8GB recommended

### Step 1: Database Setup

#### Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-contrib-14

# macOS (Homebrew)
brew install postgresql@14

# Start PostgreSQL
sudo systemctl start postgresql
```

#### Create Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE cc_test_db;
CREATE USER cc_test_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE cc_test_db TO cc_test_user;
\q
```

### Step 2: Application Setup

#### Clone Repository

```bash
git clone https://github.com/your-org/deepagent-test-runner.git
cd deepagent-test-runner
```

#### Install Dependencies

```bash
# Navigate to platform directory
cd platform

# Install Python dependencies
pip install -r requirements.txt

# Or using Poetry
poetry install
```

#### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### Step 3: Database Migration

The Token Limitation System requires database tables to be created.

#### Run Migrations

```bash
# Using Alembic
cd platform/backend
alembic upgrade head

# Or using docker compose
docker compose run --rm backend alembic upgrade head
```

#### Verify Migration

```bash
# Connect to database
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db

# Check tables
\dt token_*

# Should show:
# token_budgets
# token_quotas
# token_alerts
```

### Step 4: Start Services

#### Using Docker Compose (Recommended)

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f backend
```

#### Manual Start

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Start Redis
sudo systemctl start redis

# Start Backend
cd platform/backend
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload

# Start Frontend
cd platform/frontend
npm run dev
```

### Step 5: Verify Installation

```bash
# Check health endpoint
curl http://localhost:8080/api/v1/health

# Check token API availability
curl http://localhost:8080/api/v1/token/budgets \
  -H "Authorization: Bearer $TOKEN"

# Should return budget list or empty array
```

## Database Migration

### Understanding Migrations

The Token Limitation System uses Alembic for database migrations:

```
alembic/
├── versions/
│   └── l1m2n3o4p5q6_add_token_limitation_tables.py  # Token system migration
├── env.py
├── script.py.mako
└── README
```

### Migration File Structure

```python
"""add token limitation tables

Revision ID: l1m2n3o4p5q6
Revises: k1j2h3g4f5d6
Create Date: 2026-06-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Create token limitation tables."""
    
    # Create token_budgets table
    op.create_table(
        'token_budgets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('scope_type', sa.String(length=50), nullable=False),
        sa.Column('scope_id', sa.Integer(), nullable=True),
        sa.Column('parent_budget_id', sa.Integer(), nullable=True),
        sa.Column('period_type', sa.String(length=20), nullable=False, server_default='monthly'),
        # ... additional columns
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_token_budgets_scope_type_scope_id', 'token_budgets', ['scope_type', 'scope_id'])
    op.create_index('ix_token_budgets_parent_id', 'token_budgets', ['parent_budget_id'])
    
    # Create token_quotas table
    op.create_table('token_quotas', ...)
    
    # Create token_alerts table
    op.create_table('token_alerts', ...)

def downgrade():
    """Drop token limitation tables."""
    
    op.drop_table('token_alerts')
    op.drop_table('token_quotas')
    op.drop_table('token_budgets')
```

### Running Migrations

#### Apply All Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Or with docker compose
docker compose run --rm backend alembic upgrade head
```

#### Apply Specific Migration

```bash
# Upgrade to specific version
alembic upgrade l1m2n3o4p5q6
```

#### Rollback Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade k1j2h3g4f5d6
```

### Migration Verification

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Verify table structure
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db -c "\d token_budgets"
```

### Data Migration

If migrating from existing token tracking:

```python
"""Migrate existing token usage data."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    """Migrate existing token usage data."""
    
    # Get database connection
    connection = op.get_bind()
    
    # Migrate existing llm_usage records
    connection.execute("""
        INSERT INTO token_budgets (name, scope_type, scope_id, total_tokens, used_tokens, period_start, period_end)
        SELECT 
            'Legacy Budget' as name,
            'organization' as scope_type,
            1 as scope_id,
            10000000 as total_tokens,
            COALESCE(SUM(total_tokens), 0) as used_tokens,
            '2026-06-01' as period_start,
            '2026-06-30' as period_end
        FROM llm_usage
    """)
```

## Configuration Options

### Service Configuration

Configure token limitation services in `platform/backend/app/core/config.py`:

```python
class TokenLimitationConfig:
    """Token limitation system configuration."""
    
    # Budget Settings
    BUDGET_DEFAULT_LIMIT = 1000000  # Default budget limit (tokens)
    BUDGET_DEFAULT_PERIOD = "monthly"  # Default period type
    BUDGET_DEFAULT_ENFORCEMENT = "soft"  # Default enforcement mode
    
    # Quota Settings
    QUOTA_DEFAULT_LIMIT = 50000  # Default daily quota (tokens)
    QUOTA_DEFAULT_PERIOD = "daily"  # Default quota period
    QUOTA_DEFAULT_RESET = "calendar"  # Default reset strategy
    
    # Alert Settings
    ALERT_DEFAULT_THRESHOLDS = {
        "warning": 80,
        "critical": 90,
        "emergency": 95
    }
    
    # Notification Settings
    ALERT_EMAIL_ENABLED = True
    ALERT_WEBHOOK_ENABLED = False
    ALERT_WEBHOOK_URL = None
    
    # Caching Settings
    CACHE_ENABLED = True
    CACHE_TTL = 300  # 5 minutes
    
    # Monitoring Settings
    METRICS_ENABLED = True
    METRICS_EXPORT_INTERVAL = 60  # seconds
```

### Repository Configuration

Configure repository factories in `platform/backend/app/repositories/repository_factory.py`:

```python
class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def get_token_budget_repository() -> ITokenBudgetRepository:
        """Get token budget repository instance."""
        from app.repositories.token_budget_repository import TokenBudgetRepository
        return TokenBudgetRepository()
    
    @staticmethod
    def get_token_quota_repository() -> ITokenQuotaRepository:
        """Get token quota repository instance."""
        from app.repositories.token_quota_repository import TokenQuotaRepository
        return TokenQuotaRepository()
    
    @staticmethod
    def get_token_alert_repository() -> ITokenAlertRepository:
        """Get token alert repository instance."""
        from app.repositories.token_alert_repository import TokenAlertRepository
        return TokenAlertRepository()
```

## Environment Variables

### Required Variables

Configure in `platform/.env`:

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=cc_test_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=cc_test_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=

# LLM Configuration
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-plus

# Application Configuration
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
DEBUG=True

# Token Limitation Configuration
TOKEN_BUDGET_DEFAULT_LIMIT=1000000
TOKEN_QUOTA_DEFAULT_LIMIT=50000
TOKEN_ALERT_EMAIL_ENABLED=True
TOKEN_CACHE_ENABLED=True
```

### Optional Variables

```bash
# Alert Configuration
TOKEN_ALERT_WEBHOOK_ENABLED=False
TOKEN_ALERT_WEBHOOK_URL=https://hooks.company.com/alerts
TOKEN_ALERT_SLACK_ENABLED=False
TOKEN_ALERT_SLACK_TOKEN=xoxb-your-token
TOKEN_ALERT_SLACK_CHANNEL=#alerts

# Notification Configuration
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=alerts@company.com
SMTP_PASSWORD=smtp_password
SMTP_FROM=noreply@company.com

# Monitoring Configuration
TOKEN_METRICS_ENABLED=True
TOKEN_METRICS_EXPORT_INTERVAL=60
TOKEN_METRICS_RETENTION_DAYS=30

# Performance Configuration
TOKEN_CACHE_ENABLED=True
TOKEN_CACHE_TTL=300
TOKEN_BATCH_SIZE=100
```

### Docker Compose Environment

Configure in `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  redis:
    image: redis:6
    ports:
      - "6380:6379"

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379
      - LLM_API_KEY=${LLM_API_KEY}
      - TOKEN_BUDGET_DEFAULT_LIMIT=${TOKEN_BUDGET_DEFAULT_LIMIT}
    depends_on:
      - postgres
      - redis
    ports:
      - "8011:8011"

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  postgres_data:
```

## Health Checks

### API Health Endpoints

```bash
# General health check
curl http://localhost:8080/api/v1/health

# Detailed health check
curl http://localhost:8080/api/v1/health/detailed
```

### Database Health Check

```bash
# Check database connectivity
docker exec cc-test-postgres pg_isready -U cc_test_user

# Check database size
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "
    SELECT 
        pg_size_pretty(pg_database_size('cc_test_db')) as size;
"

# Check table row counts
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "
    SELECT 
        'token_budgets' as table_name, COUNT(*) as row_count 
    FROM token_budgets
    UNION ALL
    SELECT 
        'token_quotas' as table_name, COUNT(*) as row_count 
    FROM token_quotas
    UNION ALL
    SELECT 
        'token_alerts' as table_name, COUNT(*) as row_count 
    FROM token_alerts;
"
```

### Service Health Check

```bash
# Check backend service
curl http://localhost:8011/health

# Check token service availability
curl http://localhost:8011/api/v1/token/budgets \
  -H "Authorization: Bearer $TEST_TOKEN"

# Check Redis connectivity
docker exec cc-test-redis redis-cli ping
```

### Custom Health Checks

Create custom health check script:

```bash
#!/bin/bash
# health_check.sh

echo "=== Token Limitation System Health Check ==="

# Check database
echo "Checking database..."
if docker exec cc-test-postgres pg_isready -U cc_test_user; then
    echo "✓ Database is ready"
else
    echo "✗ Database is not ready"
    exit 1
fi

# Check backend service
echo "Checking backend service..."
if curl -f http://localhost:8011/health > /dev/null 2>&1; then
    echo "✓ Backend service is healthy"
else
    echo "✗ Backend service is not healthy"
    exit 1
fi

# Check token API
echo "Checking token API..."
if curl -f http://localhost:8011/api/v1/token/budgets > /dev/null 2>&1; then
    echo "✓ Token API is responding"
else
    echo "✗ Token API is not responding"
    exit 1
fi

echo "=== All checks passed ==="
```

## Monitoring Setup

### Application Monitoring

#### Prometheus Metrics

Configure Prometheus metrics in `platform/backend/app/core/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

# Token metrics
token_budget_check_total = Counter(
    'token_budget_check_total',
    'Total number of budget checks',
    ['scope_type', 'result']
)

token_usage_recorded_total = Counter(
    'token_usage_recorded_total',
    'Total number of usage recordings',
    ['scope_type']
)

token_request_duration = Histogram(
    'token_request_duration_seconds',
    'Token request duration',
    ['endpoint']
)

token_budget_remaining = Gauge(
    'token_budget_remaining',
    'Remaining tokens in budget',
    ['budget_id', 'scope_type']
)
```

#### Grafana Dashboards

Create Grafana dashboard JSON:

```json
{
  "dashboard": {
    "title": "Token Limitation Monitoring",
    "panels": [
      {
        "title": "Token Usage Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(token_usage_recorded_total[5m])"
          }
        ]
      },
      {
        "title": "Budget Status",
        "type": "stat",
        "targets": [
          {
            "expr": "token_budget_remaining"
          }
        ]
      },
      {
        "title": "Alert Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(token_alerts_created_total[1h])"
          }
        ]
      }
    ]
  }
}
```

### Log Monitoring

#### Structured Logging

Configure structured logging:

```python
import structlog

logger = structlog.get_logger()

# Log token events
logger.info(
    "token_usage_recorded",
    scope_type="test",
    scope_id=123,
    tokens_used=5000,
    budget_remaining=95000,
    user_id=5
)

# Log alert events
logger.warning(
    "token_alert_triggered",
    alert_type="budget_warning",
    budget_id=1,
    threshold_value=80,
    current_value=85,
    severity="warning"
)
```

#### Log Aggregation

Configure log aggregation:

```yaml
# docker-compose.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml
```

### Alert Monitoring

#### Configure Alertmanager

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

receivers:
  - name: 'default'
    email_configs:
      - to: 'alerts@company.com'
        from: 'noreply@company.com'
        smarthost: 'smtp.company.com:587'
    
    webhook_configs:
      - url: 'https://hooks.company.com/alerts'
```

#### Alert Rules

```yaml
# alert_rules.yml
groups:
  - name: token_limitation
    interval: 30s
    rules:
      - alert: HighTokenUsageRate
        expr: rate(token_usage_recorded_total[5m]) > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High token usage rate detected"
      
      - alert: BudgetNearExhaustion
        expr: token_budget_remaining < 10000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Budget near exhaustion"
```

## Rollback Procedures

### Database Rollback

#### Rollback Migration

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade k1j2h3g4f5d6

# Verify rollback
alembic current
```

#### Data Restoration

```bash
# Restore from backup
pg_restore -U cc_test_user -d cc_test_db backup.dump

# Or using Docker
docker exec -i cc-test-postgres pg_restore -U cc_test_user -d cc_test_db < backup.dump
```

### Application Rollback

#### Docker Compose Rollback

```bash
# Stop current services
docker compose down

# Checkout previous version
git checkout previous-tag

# Rebuild and start
docker compose up -d --build

# Verify rollback
curl http://localhost:8080/api/v1/health
```

#### Manual Rollback

```bash
# Stop backend
pkill -f "uvicorn app.main:app"

# Switch to previous version
cd /path/to/previous/version

# Start previous version
uvicorn app.main:app --host 0.0.0.0 --port 8011
```

### Emergency Procedures

#### Disable Token Enforcement

```bash
# Set enforcement to monitoring mode
docker exec cc-test-backend python -c "
from app.core.database import get_db
from app.repositories.repository_factory import RepositoryFactory

db = get_db().__aenter__()
budget_repo = RepositoryFactory.get_token_budget_repository()

# Update all budgets to monitoring mode
budgets = budget_repo.list_all(db)
for budget in budgets:
    budget.enforcement_mode = 'monitoring'
    await budget_repo.update(budget.id, {'enforcement_mode': 'monitoring'}, db)
"
```

#### Increase Limits Temporarily

```bash
# Double all budget limits
docker exec cc-test-backend python -c "
from app.core.database import get_db
from app.repositories.repository_factory import RepositoryFactory

db = get_db().__aenter__()
budget_repo = RepositoryFactory.get_token_budget_repository()

budgets = await budget_repo.list_all(db)
for budget in budgets:
    new_limit = budget.total_tokens * 2
    await budget_repo.update(budget.id, {'total_tokens': new_limit}, db)
"
```

## Performance Tuning

### Database Optimization

#### Index Optimization

```sql
-- Create additional indexes for performance
CREATE INDEX CONCURRENTLY ix_token_budgets_usage_percentage 
ON token_budgets ((used_tokens::float / NULLIF(total_tokens, 0)) * 100);

CREATE INDEX CONCURRENTLY ix_token_alerts_created_at_severity 
ON token_alerts (created_at DESC, severity);

-- Analyze tables
ANALYZE token_budgets;
ANALYZE token_quotas;
ANALYZE token_alerts;
```

#### Query Optimization

```python
# Optimize batch queries
async def get_budgets_with_performance(budget_ids: list[int], db: AsyncSession):
    """Get multiple budgets efficiently."""
    
    # Use IN clause instead of multiple queries
    budgets = await db.execute(
        select(TokenBudget)
        .where(TokenBudget.id.in_(budget_ids))
        .options(selectinload(TokenBudget.child_budgets))
    )
    
    return budgets.scalars().all()
```

### Caching Configuration

#### Redis Caching

```python
# Configure Redis caching
import redis

redis_client = redis.Redis(
    host='localhost',
    port=6380,
    db=0,
    decode_responses=True
)

# Cache budget status
def get_budget_status_cached(budget_id: int) -> dict:
    cache_key = f"budget_status:{budget_id}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Get fresh data
    status = get_budget_status_from_db(budget_id)
    
    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(status))
    
    return status
```

### Connection Pooling

```python
# Configure database connection pool
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Number of connections to maintain
    max_overflow=40,        # Additional connections allowed
    pool_timeout=30,         # Connection timeout
    pool_recycle=3600,       # Recycle connections after 1 hour
    pool_pre_ping=True       # Verify connections before using
)
```

### Batch Processing

```python
# Process usage recordings in batches
async def batch_record_usage(records: list[dict], db: AsyncSession):
    """Record multiple usage records efficiently."""
    
    BATCH_SIZE = 100
    
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        
        # Batch update
        await db.execute(
            insert(TokenBudget.__table__)
            .values([
                {
                    'id': r['budget_id'],
                    'used_tokens': TokenBudget.used_tokens + r['tokens_used']
                }
                for r in batch
            ])
            .on_conflict_do_update(
                index_elements=['id'],
                set_={'used_tokens': TokenBudget.used_tokens +.excluded.tokens_used}
            )
        )
        
        await db.commit()
```

---

**Next:** See [Configuration Reference](TOKEN_LIMITATION_CONFIG.md) for detailed configuration options.