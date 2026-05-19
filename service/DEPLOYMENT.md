# Deployment Guide - AI Tests Microservices

This guide covers deploying the AI Tests microservices architecture to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Deployment Strategies](#deployment-strategies)
4. [Production Setup](#production-setup)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Backup and Recovery](#backup-and-recovery)
7. [Scaling](#scaling)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Git**: For cloning the repository
- **SSL/TLS certificates**: For HTTPS (recommended)

### Hardware Requirements

**Minimum (Development):**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 50+ GB SSD

## Environment Configuration

### 1. Create Production .env File

```bash
cd docker-compose
cp .env.example .env.production
```

### 2. Configure Secure Values

Edit `.env.production` with production values:

```bash
# Database
POSTGRES_DB=claude_code_tests
POSTGRES_USER=cc_test_user
POSTGRES_PASSWORD=<GENERATE_SECURE_32_CHAR_PASSWORD>

# Security
SECRET_KEY=<GENERATE_SECURE_RANDOM_STRING>
ADMIN_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Redis
REDIS_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Environment
ENVIRONMENT=production
```

### 3. Generate Secure Passwords

```bash
# Generate random passwords
openssl rand -base64 32
```

## Deployment Strategies

### Option 1: Docker Compose (Single Host)

**Best for:** Small teams, single-server deployments

```bash
# Start all services
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Verify services are running
docker-compose ps
```

**Pros:**
- Simple setup
- All services on one host
- Easy to manage

**Cons:**
- Single point of failure
- Limited scalability

### Option 2: Docker Swarm (Multi-Host)

**Best for:** Medium deployments, high availability

```bash
# Initialize Swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml claude-tests

# Scale services
docker service scale claude-tests_scheduler-worker=4
```

**Pros:**
- High availability
- Easy scaling
- Built-in load balancing

**Cons:**
- More complex setup
- Requires multiple nodes

### Option 3: Kubernetes (Enterprise)

**Best for:** Large-scale, enterprise deployments

Create Kubernetes manifests (not included in this repository).

**Pros:**
- Maximum scalability
- Advanced features
- Industry standard

**Cons:**
- Complex setup
- Steep learning curve

## Production Setup

### 1. SSL/TLS Configuration

**Using Nginx Reverse Proxy:**

```nginx
# /etc/nginx/sites-available/claude-tests
server {
    listen 80;
    server_name tests.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tests.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/tests.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tests.yourdomain.com/privkey.pem;

    # Test Case Service
    location /api/v1/test-definitions {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Scheduler Service
    location /api/v1/jobs {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Dashboard Service
    location / {
        proxy_pass http://localhost:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Database Optimization

**PostgreSQL Tuning:**

Add to `docker-compose.yml`:

```yaml
postgres:
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=128MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c work_mem=2621kB
    -c min_wal_size=1GB
    -c max_wal_size=4GB
```

### 3. Resource Limits

```yaml
services:
  test-case-service:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  scheduler-service:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '1'
          memory: 512M
```

### 4. Health Checks

All services include health checks. Monitor them:

```bash
# Watch service health
watch -n 5 'docker-compose ps'
```

## Monitoring and Logging

### 1. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f test-case-service

# Last 100 lines
docker-compose logs --tail=100
```

### 2. Log Aggregation (Optional)

**Using ELK Stack:**

```yaml
# Add to docker-compose.yml
elasticsearch:
  image: elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
  ports:
    - "9200:9200"

logstash:
  image: logstash:8.11.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

kibana:
  image: kibana:8.11.0
  ports:
    - "5601:5601"
```

### 3. Metrics Collection

**Using Prometheus:**

```yaml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

### 4. Alerting

Set up alerts for:
- Service down time
- High error rates
- Database connection issues
- Disk space low
- High memory usage

## Backup and Recovery

### 1. Database Backups

**Automated Backup Script:**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec cc-test-postgres pg_dump -U cc_test_user claude_code_tests | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Keep last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

**Add to crontab:**

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

### 2. Redis Backups

```bash
# Trigger Redis snapshot
docker exec cc-test-redis redis-cli BGSAVE

# Copy RDB file
docker cp cc-test-redis:/data/dump.rdb /backups/redis/
```

### 3. Restore Database

```bash
# Stop services
docker-compose down

# Restore PostgreSQL
gunzip < /backups/postgres/backup_20240101_020000.sql.gz | \
  docker exec -i cc-test-postgres psql -U cc_test_user claude_code_tests

# Restart services
docker-compose up -d
```

## Scaling

### Horizontal Scaling

**Scale Celery Workers:**

```bash
# Add more workers
docker-compose up -d --scale scheduler-worker=4
```

**Scale API Services:**

Requires load balancer (nginx, traefik):

```bash
docker-compose up -d --scale test-case-service=3
```

### Vertical Scaling

Increase resource limits in `docker-compose.yml`:

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
```

## Security

### 1. Network Security

```yaml
# Create isolated network
networks:
  test-network:
    driver: bridge
    internal: false  # Set to true for complete isolation
```

### 2. Secrets Management

**Use Docker Secrets (Swarm):**

```bash
echo "your_password" | docker secret create postgres_password -
```

### 3. Firewall Rules

```bash
# Only allow necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

### 4. Regular Updates

```bash
# Update images monthly
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Service Won't Start

1. Check logs: `docker-compose logs [service]`
2. Verify ports: `lsof -i :[port]`
3. Check resources: `docker stats`
4. Verify environment: `docker-compose config`

### Database Connection Issues

1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Test connection: `docker exec -it cc-test-postgres psql -U cc_test_user`
3. Verify credentials in `.env`

### High Memory Usage

1. Check stats: `docker stats`
2. Restart bloated services: `docker-compose restart [service]`
3. Consider increasing limits
4. Check for memory leaks

### Slow Performance

1. Check database: `docker exec cc-test-postgres pg_stat_activity`
2. Add more workers: `--scale scheduler-worker=4`
3. Optimize PostgreSQL (see Database Optimization)
4. Check disk I/O: `iostat -x 1`

## Maintenance

### Regular Tasks

**Daily:**
- Check service health
- Review error logs

**Weekly:**
- Review disk space
- Check backup completion
- Review performance metrics

**Monthly:**
- Update Docker images
- Review and rotate logs
- Security audit
- Performance tuning

### Updating Services

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d

# Remove old images
docker image prune -a
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this guide
3. Check main project README
4. Review GitHub issues

## Appendix

### Useful Commands

```bash
# Service status
docker-compose ps

# Resource usage
docker stats

# Execute command in container
docker exec -it [container] bash

# Copy files from container
docker cp [container]:/path/file ./localfile

# Rebuild service
docker-compose build [service]
docker-compose up -d [service]

# Clean up
docker-compose down -v  # Remove volumes
docker system prune -a   # Remove all unused data
```

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| POSTGRES_DB | Database name | claude_code_tests | Yes |
| POSTGRES_USER | Database user | cc_test_user | Yes |
| POSTGRES_PASSWORD | Database password | - | Yes |
| SECRET_KEY | JWT secret | - | Yes |
| REDIS_PASSWORD | Redis password | - | No |
| ENVIRONMENT | Environment | development | No |
