# AI Tests - Microservices Architecture

This directory contains the Docker Compose configuration for running AI Tests as microservices.

## Architecture Overview

The system consists of 4 microservices sharing a PostgreSQL database:

```
┌─────────────────┐      ┌─────────────────┐
│ Test Case API   │      │ Scheduler API   │
│   (FastAPI)     │      │   (FastAPI)     │
│   Port: 8001    │      │   Port: 8002    │
└────────┬────────┘      └─┬───────────┬──┘
         │                  │           │
         └──────────┬───────┘           │
                    │                   │
         ┌──────────▼───────────┐       │
         │   PostgreSQL         │       │
         │   Database           │       │
         │   Port: 5432         │       │
         └──────────┬───────────┘       │
                    │                   │
         ┌──────────▼───────────┐       │
         │   Dashboard Service  │       │
         │   (Express.js)       │       │
         │   Port: 8003         │       │
         └──────────────────────┘       │
                                       │
                    ┌──────────────────▼──────┐
                    │   Redis Queue            │
                    │   Port: 6379             │
                    │   (Celery Broker)        │
                    └──────────────────────────┘
```

## Services

### 1. Test Case Service (Port 8001)
FastAPI-based REST API for managing test definitions and test steps.

**Features:**
- CRUD operations for test definitions
- Test step management
- Test versioning and history
- JWT authentication

**API Docs:** http://localhost:8001/api/docs

### 2. Scheduler Service (Port 8002)
FastAPI-based service for test execution scheduling with Celery workers.

**Features:**
- Async test execution with Playwright
- Job management and monitoring
- Scheduled test runs
- Real-time status updates

**API Docs:** http://localhost:8002/api/docs

### 3. Dashboard Service (Port 8003)
Express.js-based dashboard for test analytics and visualization.

**Features:**
- Real-time test metrics
- Historical trends
- Flaky test detection
- Performance analysis

**Dashboard:** http://localhost:8003

### 4. PostgreSQL Database (Port 5432)
Centralized database for all services.

**Schema:**
- `test_definitions` - Test case definitions
- `test_steps` - Test execution steps
- `test_versions` - Test version history
- `test_runs` - Test execution runs
- `test_cases` - Individual test results
- `test_step_results` - Step execution results
- `schedules` - Scheduled test configurations
- `webhooks` - Webhook configurations
- `users` - User authentication

### 5. Redis (Port 6379)
Message broker for Celery task queue.

## Quick Start

### 1. Configure Environment

```bash
cd docker-compose
cp .env.example .env
# Edit .env with your configuration
```

**Required settings in `.env`:**
```bash
POSTGRES_DB=claude_code_tests
POSTGRES_USER=cc_test_user
POSTGRES_PASSWORD=your_secure_password_here
SECRET_KEY=your-secret-key-here
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access Services

- **Dashboard**: http://localhost:8003
- **Test Case API**: http://localhost:8001/api/docs
- **Scheduler API**: http://localhost:8002/api/docs

### 4. Migrate Existing Data (Optional)

If you have existing SQLite data:

```bash
# Run migration script
./migrate.sh

# Or manually
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../claude_code_tests.db
```

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for details.

## Service Management

### Start All Services
```bash
docker-compose up -d
```

### Stop All Services
```bash
docker-compose down
```

### Restart a Specific Service
```bash
docker-compose restart test-case-service
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f scheduler-service
```

### Scale Celery Workers
```bash
docker-compose up -d --scale scheduler-worker=4
```

## Database Management

### Connect to PostgreSQL
```bash
docker exec -it cc-test-postgres psql -U cc_test_user -d claude_code_tests
```

### Backup Database
```bash
docker exec cc-test-postgres pg_dump -U cc_test_user claude_code_tests > backup.sql
```

### Restore Database
```bash
docker exec -i cc-test-postgres psql -U cc_test_user claude_code_tests < backup.sql
```

## Monitoring

### Health Checks
```bash
# Test Case Service
curl http://localhost:8001/health

# Scheduler Service
curl http://localhost:8002/health

# Dashboard Service
curl http://localhost:8003/health

# PostgreSQL
docker exec cc-test-postgres pg_isready -U cc_test_user

# Redis
docker exec cc-test-redis redis-cli ping
```

### View Celery Worker Status
```bash
docker exec cc-test-scheduler-worker celery -A app.core.celery_app inspect active
```

## Troubleshooting

### Service Won't Start

1. Check if ports are already in use:
   ```bash
   lsof -i :8001
   lsof -i :8002
   lsof -i :8003
   ```

2. Check service logs:
   ```bash
   docker-compose logs [service-name]
   ```

### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Check database credentials in `.env`

3. Test connection:
   ```bash
   docker exec cc-test-postgres psql -U cc_test_user -d claude_code_tests
   ```

### Redis Connection Issues

1. Verify Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Test connection:
   ```bash
   docker exec cc-test-redis redis-cli ping
   ```

## Development

### Rebuild Services

After making changes to service code:

```bash
# Rebuild specific service
docker-compose build test-case-service

# Rebuild all services
docker-compose build

# Rebuild and start
docker-compose up -d --build
```

### Run Tests

```bash
# Test Case Service
docker-compose exec test-case-service pytest

# Scheduler Service
docker-compose exec scheduler-service pytest
```

## Production Deployment

For production deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md).

Key considerations:
- Use strong passwords and SECRET_KEY
- Enable HTTPS/TLS
- Configure proper resource limits
- Set up monitoring and logging
- Use managed PostgreSQL/Redis services
- Configure backups

## Architecture Benefits

**Microservices Advantages:**
- **Independent scaling**: Scale each service based on load
- **Technology flexibility**: Use best tools for each service
- **Fault isolation**: Failure in one service doesn't affect others
- **Team autonomy**: Different teams can own different services
- **Deployment flexibility**: Deploy services independently

**PostgreSQL Advantages:**
- **Concurrent access**: Multiple services read/write simultaneously
- **Complex queries**: Advanced analytics and reporting
- **Data integrity**: ACID transactions at scale
- **Scalability**: Handle much larger datasets than SQLite

## Support

For issues or questions:
1. Check [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for data migration
2. Review service logs: `docker-compose logs -f`
3. Check health endpoints for each service
4. Review the main project README
