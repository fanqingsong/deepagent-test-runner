# Operations Guide - Claude Code Tests Microservices

Daily operations and maintenance procedures for running Claude Code Tests in production.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring Dashboards](#monitoring-dashboards)
3. [Incident Response](#incident-response)
4. [Performance Tuning](#performance-tuning)
5. [Capacity Planning](#capacity-planning)
6. [Disaster Recovery](#disaster-recovery)

## Daily Operations

### Morning Checklist

**1. Health Check (5 minutes)**

```bash
# Quick health check
cd docker-compose
docker-compose ps

# Check all services are "Up"
# Expected output:
# test-case-service    Up (healthy)
# scheduler-service    Up (healthy)
# scheduler-worker     Up
# dashboard-service    Up (healthy)
# postgres             Up (healthy)
# redis                Up (healthy)
```

**2. Review Logs (5 minutes)**

```bash
# Check for errors in last 100 lines
docker-compose logs --tail=100 | grep -i error

# Check specific service
docker-compose logs --tail=100 test-case-service | grep -i error
```

**3. Check Resources (2 minutes)**

```bash
# Monitor resource usage
docker stats --no-stream

# Look for:
# - Memory usage > 80%
# - CPU usage > 90%
# - Unusual spikes
```

**4. Verify Backups (3 minutes)**

```bash
# Check last backup exists
ls -lth /backups/postgres/ | head -1

# Verify backup size is reasonable (should be > 0)
du -sh /backups/postgres/backup_*.sql.gz
```

### Weekly Tasks

**1. Review Performance (15 minutes)**

```bash
# Check dashboard for trends
open http://localhost:8003

# Look for:
# - Increasing failure rates
# - Slowing test execution times
# - Unusual patterns
```

**2. Clean Up Old Data (10 minutes)**

```bash
# Remove old test runs (> 90 days)
docker exec -it cc-test-postgres psql -U cc_test_user -d claude_code_tests -c \
  "DELETE FROM test_runs WHERE start_time < $(date -d '90 days ago' +%s)000;"
```

**3. Review Disk Space (5 minutes)**

```bash
# Check disk usage
df -h

# Check Docker space
docker system df

# Clean up if needed (> 80% used)
docker system prune -a --volumes
```

### Monthly Tasks

**1. Security Updates (30 minutes)**

```bash
# Update all images
docker-compose pull

# Recreate containers
docker-compose up -d

# Verify services work
./test-service-tests.sh
```

**2. Performance Review (1 hour)**

- Review metrics for the month
- Identify slow tests
- Optimize database queries
- Update indexes if needed

**3. Capacity Planning (30 minutes)**

- Review growth trends
- Plan for scaling needs
- Budget for additional resources

## Monitoring Dashboards

### Key Metrics to Monitor

**1. Service Health**
- Uptime percentage
- Response time
- Error rate
- Request rate

**2. Test Execution**
- Tests per day
- Average duration
- Pass rate
- Flaky test rate

**3. Database**
- Connection pool usage
- Query performance
- Disk I/O
- Table size

**4. Infrastructure**
- CPU usage
- Memory usage
- Disk space
- Network I/O

### Setting Up Alerts

**Critical Alerts (Page Immediately):**
- All services down
- Database connection lost
- Disk space > 90%
- Memory > 95%

**Warning Alerts (Email within 1 hour):**
- High error rate (> 10%)
- Slow performance (> 2x normal)
- Single service down
- Disk space > 80%

## Incident Response

### Severity Levels

**P1 - Critical**
- All services down
- Data loss
- Security breach
- Response time: < 15 minutes

**P2 - High**
- Single service down
- Performance degraded
- Response time: < 1 hour

**P3 - Medium**
- Minor issues
- Workaround available
- Response time: < 4 hours

**P4 - Low**
- Cosmetic issues
- No impact
- Response time: < 24 hours

### Incident Procedure

**1. Detection**

```bash
# Identify the issue
docker-compose ps
docker-compose logs --tail=50
```

**2. Assessment**

- Determine severity
- Identify affected services
- Estimate impact

**3. Resolution**

**Quick Fixes:**
```bash
# Restart service
docker-compose restart [service]

# Restart all services
docker-compose restart

# Rebuild if needed
docker-compose up -d --build [service]
```

**4. Communication**

- Notify stakeholders
- Provide updates
- Confirm resolution

**5. Post-Incident**

- Document root cause
- Update procedures
- Prevent recurrence

## Performance Tuning

### Database Optimization

**1. Add Indexes**

```sql
-- Analyze slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Add appropriate indexes
CREATE INDEX CONCURRENTLY idx_name ON table(column);
```

**2. Update Statistics**

```sql
ANALYZE test_runs;
ANALYZE test_cases;
VACUUM ANALYZE;
```

**3. Connection Pooling**

```python
# In services, tune pool size
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Increase for high load
    max_overflow=40,     # Allow surge capacity
    pool_timeout=30,
)
```

### Celery Optimization

**1. Worker Configuration**

```python
# In celery_app.py
worker_prefetch_multiplier=4,  # Process multiple tasks
worker_concurrency=8,           # More concurrent tasks
task_acks_late=True,           # Better reliability
```

**2. Queue Priorities**

```python
# Route important tasks first
task_routes = {
    'critical.tasks': {'queue': 'critical'},
    'normal.tasks': {'queue': 'normal'},
}
```

### Caching Strategy

```python
# Cache test definitions (rarely change)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_test_definition(test_id):
    # Implementation
    pass
```

## Capacity Planning

### Scaling Triggers

**Add Celery Workers When:**
- Task queue > 100 pending
- Average wait time > 30 seconds
- Workers consistently at 100% CPU

**Scale API Services When:**
- Response time > 2 seconds
- Error rate increases
- CPU > 80% sustained

**Scale Database When:**
- Connection pool exhausted
- Query performance degrades
- Disk I/O saturated

### Growth Planning

**Monthly Growth Formula:**

```
Projected Tests = Current Tests × (1 + Growth Rate)^Months

Example: 1000 tests/month, 20% growth
Month 6: 1000 × (1.2)^6 = 2,985 tests/month
```

**Resource Requirements:**

```
CPU Cores = (Tests Per Day / 1000) × 2
RAM GB = (Tests Per Day / 1000) × 4
Disk GB = Base + (Tests Per Day × 0.1)
```

## Disaster Recovery

### Backup Strategy

**3-2-1 Rule:**
- 3 copies of data
- 2 different media types
- 1 off-site backup

**Implementation:**

```bash
# Local backup (daily)
./backup.sh

# Remote backup (weekly)
rsync -avz /backups/ user@remote-server:/backups/

# Cloud backup (monthly)
aws s3 sync /backups/ s3://bucket-name/
```

### Recovery Procedures

**1. Service Recovery**

```bash
# Restore from backup
gunzip < /backups/backup_latest.sql.gz | \
  docker exec -i cc-test-postgres psql -U cc_test_user claude_code_tests

# Restart services
docker-compose up -d

# Verify
./test-service-tests.sh
```

**2. Complete System Recovery**

```bash
# On new server
git clone [repo]
cd docker-compose
cp .env.production .env
docker-compose up -d

# Restore database
# Restore Redis
# Verify all services
```

### Testing Recovery

**Monthly Test:**

```bash
# Simulate failure
docker-compose down

# Restore from backup
# [Recovery procedure]

# Verify
./test-service-tests.sh
```

## Runbooks

### Service Down

```bash
# Symptom: Service shows "Exit" or not running
docker-compose ps

# Diagnosis
docker-compose logs [service]

# Resolution
docker-compose restart [service]

# If persistent
docker-compose up -d --build [service]
```

### Database Slow

```bash
# Symptom: Queries > 5 seconds
docker exec cc-test-postgres psql -U cc_test_user -d claude_code_tests

# Check active queries
SELECT pid, query, state, wait_event
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;

# Kill long-running queries if needed
SELECT pg_cancel_backend(pid);

# Resolution
VACUUM ANALYZE;
REINDEX DATABASE claude_code_tests;
```

### High Memory Usage

```bash
# Symptom: Container OOM killed
docker stats

# Diagnosis
docker exec [container] ps aux

# Resolution
docker-compose restart [service]

# Permanent: Increase memory limit in docker-compose.yml
```

### Disk Full

```bash
# Symptom: Cannot write files
df -h

# Diagnosis
du -sh /var/lib/docker/* | sort -h

# Resolution
docker system prune -a --volumes

# Permanent: Add more disk or clean old data
```

## Maintenance Windows

**Schedule:**
- Frequency: Monthly
- Duration: 1 hour
- Time: Low-traffic period (e.g., Sunday 2 AM)

**Procedure:**

1. Notify users 1 week in advance
2. Create pre-maintenance backup
3. Stop services: `docker-compose down`
4. Perform maintenance
5. Test services
6. Start services: `docker-compose up -d`
7. Verify functionality
8. Notify users completion

**Rollback Plan:**

```bash
# If issues occur
docker-compose down
# [Restore previous version]
docker-compose up -d
```

## On-Call Procedures

### Rotation

- Primary on-call: 1 week rotations
- Backup on-call: For escalations
- On-call hours: Business hours or 24/7

### Escalation Path

1. **Level 1**: On-call engineer
2. **Level 2**: Engineering lead
3. **Level 3**: CTO/VP Engineering

### Handoff Procedure

**Start of Shift:**
- Review incidents
- Check system status
- Review upcoming changes

**End of Shift:**
- Document incidents
- Update handoff notes
- Alert next on-call

## Change Management

### Change Request Process

1. **Submit**: Create change request
2. **Review**: Engineering lead approves
3. **Schedule**: Plan maintenance window
4. **Test**: Test in staging
5. **Deploy**: Deploy to production
6. **Verify**: Confirm success
7. **Document**: Update runbooks

### Rollback Criteria

Rollback if:
- Error rate > 5%
- Response time > 3x baseline
- Any service down
- Data integrity issues

## Compliance and Auditing

### Logging Requirements

**Retention:**
- Application logs: 30 days
- Database logs: 90 days
- Audit logs: 1 year

**Content:**
- All API requests
- Authentication events
- Configuration changes
- Data access

### Audit Trail

```sql
-- Enable PostgreSQL logging
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_duration = on;

-- View logs
SELECT * FROM pg_stat_statements;
```

## Support Contacts

**Internal:**
- Engineering Lead: [email]
- DevOps: [email]
- Security: [email]

**External:**
- Docker Support: https://www.docker.com/support
- PostgreSQL: https://www.postgresql.org/support/
- Redis: https://redis.io/support
