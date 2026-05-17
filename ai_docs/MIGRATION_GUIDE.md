# SQLite to PostgreSQL Migration Guide

This guide explains how to migrate your existing Claude Code Tests data from SQLite to PostgreSQL.

## Prerequisites

1. **Backup your SQLite database**
   ```bash
   cp claude_code_tests.db claude_code_tests.db.backup
   ```

2. **Install Python dependencies**
   ```bash
   pip install psycopg2-binary
   ```

3. **Start PostgreSQL container**
   ```bash
   cd docker-compose
   docker-compose up -d postgres
   ```

## Migration Steps

### 1. Set Environment Variables

Create a `.env` file in the `docker-compose` directory:

```bash
# Database
POSTGRES_DB=claude_code_tests
POSTGRES_USER=cc_test_user
POSTGRES_PASSWORD=your_secure_password_here

# Security
SECRET_KEY=your-secret-key-here
```

### 2. Run the Migration Script

The migration script is located at `docker-compose/scripts/migrate_sqlite_to_postgres.py`.

**Option A: Dry Run (Recommended First)**
```bash
cd docker-compose
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../claude_code_tests.db \
  --dry-run
```

This will show you what data will be migrated without actually migrating it.

**Option B: Full Migration**
```bash
cd docker-compose
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../claude_code_tests.db \
  --postgres-host localhost \
  --postgres-port 5432 \
  --postgres-db claude_code_tests \
  --postgres-user cc_test_user \
  --postgres-password your_password
```

Or use environment variables:
```bash
export POSTGRES_PASSWORD=your_password
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path ../claude_code_tests.db
```

### 3. Verify Migration

Connect to PostgreSQL and verify the data:

```bash
# Connect to PostgreSQL
docker exec -it cc-test-postgres psql -U cc_test_user -d claude_code_tests

# Check test_definitions
SELECT COUNT(*) FROM test_definitions;

# Check test_runs
SELECT COUNT(*) FROM test_runs;

# Check test_cases
SELECT COUNT(*) FROM test_cases;

# Exit
\q
```

## What Gets Migrated

The migration script transfers the following data:

1. **test_definitions** - Test case definitions with metadata
2. **test_steps** - Individual test steps
3. **test_runs** - Test execution runs
4. **test_cases** - Individual test case results

## Data Mapping

| SQLite Field | PostgreSQL Field | Notes |
|--------------|------------------|-------|
| `id` | `id` | Auto-incremented, may change |
| `test_definition_id` (string) | `test_definition_id` (int) | Mapped via test_id lookup |
| `run_id` (string) | `run_id` (internal int) | Mapped via run_id string lookup |

## Rollback

If you need to rollback:

1. **Stop PostgreSQL services**
   ```bash
   docker-compose down
   ```

2. **Restore SQLite database**
   ```bash
   cp claude_code_tests.db.backup claude_code_tests.db
   ```

3. **Clear PostgreSQL data** (if needed)
   ```bash
   docker-compose down -v
   docker-compose up -d postgres
   ```

## Troubleshooting

### Issue: "relation does not exist"

**Solution**: Ensure the PostgreSQL schema has been initialized. The schema is automatically created when the PostgreSQL container starts via `init-db.sql`.

### Issue: "test_definition_id not found"

**Solution**: This occurs when test_cases reference test_definitions that don't exist. The migration script will log warnings and skip these records.

### Issue: "run_id not found"

**Solution**: Similar to above, test_cases may reference test_runs that don't exist. The migration script will skip these records.

### Issue: Permission Denied

**Solution**: Ensure the PostgreSQL user has proper permissions:
```bash
docker exec -it cc-test-postgres psql -U cc_test_user -d claude_code_tests
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cc_test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cc_test_user;
```

## Post-Migration Steps

After successful migration:

1. **Update your CLI configuration** to use PostgreSQL instead of SQLite
2. **Start all microservices**
   ```bash
   docker-compose up -d
   ```
3. **Verify dashboard** at `http://localhost:8003`
4. **Test API endpoints**:
   - Test Case Service: `http://localhost:8001/api/docs`
   - Scheduler Service: `http://localhost:8002/api/docs`
   - Dashboard Service: `http://localhost:8003`

## Performance Considerations

PostgreSQL offers significant performance improvements over SQLite:

- **Concurrent access**: Multiple services can read/write simultaneously
- **Complex queries**: Advanced aggregation and analytics
- **Scalability**: Handles much larger datasets
- **ACID compliance**: Reliable transactions at scale

## Next Steps

After migration:
1. Review the [Deployment Guide](./DEPLOYMENT.md) for production setup
2. Configure scheduled test runs using the scheduler service
3. Set up monitoring and alerting
4. Archive your SQLite backup for safekeeping
