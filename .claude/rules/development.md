# Development Commands

## Microservices Development

Working directory: `platform/`

```bash
# Start/stop environments (preferred)
./start-dev.sh                # Start dev environment with hot-reload
./stop-dev.sh                 # Stop dev environment
./start-prod.sh               # Start prod environment
./stop-prod.sh                # Stop prod environment

# Direct docker compose (fallback)
cd platform
docker compose ps             # Check service status
docker compose logs -f [service]  # View logs
docker compose restart [service]  # Restart specific service
```

**Hot-reload enabled for:**
- `backend/app:/app/app` (API backend)
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
