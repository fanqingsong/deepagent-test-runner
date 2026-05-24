# Development Commands

## Microservices Development

Working directory: `service/`

```bash
cd service
docker compose up -d          # Start all services with hot-reload
docker compose ps             # Check service status
docker compose logs -f [service]  # View logs
docker compose restart [service]  # Restart specific service
```

**Hot-reload enabled for:**
- `backend/app:/app/app` (API and Celery worker)
- `frontend/src:/app/frontend` (Vite dev server)

Changes to these directories are automatically reflected without rebuilding.

**IMPORTANT:** Use `docker compose` (not `docker-compose`).

## Database Operations

```bash
# Connect to PostgreSQL
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db

# Check specific table
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "\d test_runs"
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "SELECT COUNT(*) FROM test_cases"

# Backup
docker exec cc-test-postgres pg_dump -U cc_test_user cc_test_db > backup.sql
```
