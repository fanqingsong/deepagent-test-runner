# Observability Stack - Docker Compose Deployment

This guide explains how to deploy the observability stack using Docker Compose when you don't have a Kubernetes cluster.

## Prerequisites

- Docker and Docker Compose installed
- Running backend service (from `service/docker-compose.yml`)
- Ports 3000, 9090, 3100, 16686, 4318 available

## Quick Start

### 1. Start Observability Stack

```bash
cd service

# Start main services (if not already running)
docker compose up -d postgres redis backend nginx

# Start observability stack
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

### 2. Verify Services

```bash
# Check all services are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "prometheus|loki|promtail|jaeger|grafana"

# Expected output:
# cc-test-prometheus    Up    0.0.0.0:9090->9090/tcp
# cc-test-loki         Up    0.0.0.0:3100->3100/tcp
# cc-test-promtail     Up
# cc-test-jaeger        Up    0.0.0.0:16686->16686/tcp, ...
# cc-test-grafana       Up    0.0.0.0:3000->3000/tcp
```

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686
- **Loki**: Accessible via Grafana datasource

## Configuration

### Backend Environment Variables

Add to `service/.env`:

```bash
# Enable observability
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
LOKI_ENABLED=true
LOKI_ENDPOINT=http://loki:3100/loki/api/v1/push
JAEGER_ENABLED=false  # Set to true to enable tracing
JAEGER_AGENT_HOST=jaeger
JAEGER_AGENT_PORT=6831
TRACE_SAMPLE_RATE=0.1
LOG_FORMAT=json
LOG_LEVEL=INFO
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Grafana | 3000 | Visualization dashboards |
| Prometheus | 9090 | Metrics collection and querying |
| Loki | 3100 | Log aggregation (internal) |
| Jaeger | 16686 | Distributed tracing UI |
| Jaeger OTLP | 4318 | OTLP HTTP endpoint |

## Usage

### Viewing Metrics in Grafana

1. Login to Grafana (http://localhost:3000)
2. Navigate to **Dashboards** → **Browse**
3. Open one of the pre-configured dashboards:
   - **Claude Test Runner - Overview**: System-wide metrics
   - **Claude Test Runner - API Performance**: API latency and throughput
   - **Claude Test Runner - Database Metrics**: Database performance

### Querying Logs

1. In Grafana, go to **Explore** → Select **Loki** datasource
2. Example queries:
   ```
   # All backend logs
   {job="backend"}

   # Error logs only
   {job="backend"} |= "error"

   # Filter by correlation ID
   {job="backend"} |~ "correlation_id"

   # Filter by HTTP method
   {job="backend", method="GET"}
   ```

### Enabling Distributed Tracing

1. Set `JAEGER_ENABLED=true` in `service/.env`
2. Restart backend service:
   ```bash
   docker compose restart backend
   ```
3. Make API requests to generate traces
4. View traces in Jaeger UI: http://localhost:16686

### Prometheus Queries

Useful PromQL queries for Prometheus UI or Grafana:

```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000

# Error rate
rate(http_requests_total{status_code!~"2.."}[5m])

# Active connections
active_connections
```

## Management

### View Logs

```bash
# All observability services
docker compose -f docker-compose.observability.yml logs -f

# Specific service
docker logs -f cc-test-prometheus
docker logs -f cc-test-grafana
docker logs -f cc-test-loki
```

### Restart Services

```bash
# Restart all observability
docker compose -f docker-compose.observability.yml restart

# Restart specific service
docker compose -f docker-compose.observability.yml restart prometheus
docker compose -f docker-compose.observability.yml restart grafana
```

### Stop Observability Stack

```bash
# Stop but keep data
docker compose -f docker-compose.observability.yml stop

# Stop and remove containers (keeps volumes)
docker compose -f docker-compose.observability.yml down

# Stop and remove everything including data
docker compose -f docker-compose.observability.yml down -v
```

### Update Configuration

1. Edit configuration files in `infrastructure/observability/`
2. Restart affected services:
   ```bash
   docker compose -f docker-compose.observability.yml up -d --force-recreate <service>
   ```

## Data Persistence

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep claude

# Backup data
docker run --rm -v cc-test_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz -C /data .
docker run --rm -v cc-test_grafana_data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz -C /data .
docker run --rm -v cc-test_loki_data:/data -v $(pwd):/backup alpine tar czf /backup/loki-backup.tar.gz -C /data .
```

## Troubleshooting

### Prometheus not scraping metrics

1. Check backend has metrics endpoint:
   ```bash
   curl http://localhost:8080/metrics
   ```

2. Verify Prometheus configuration:
   ```bash
   docker exec cc-test-prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

3. Check Prometheus targets:
   - Go to http://localhost:9090/targets
   - Verify `backend-service` is **UP**

### Logs not appearing in Loki

1. Check Promtail is running:
   ```bash
   docker logs cc-test-promtail
   ```

2. Verify Promtail can reach Loki:
   ```bash
   docker exec cc-test-promtail wget -qO- http://loki:3100/ready
   ```

3. Check Promtail configuration:
   ```bash
   docker exec cc-test-promtail promtail --config.file=/etc/promtail/config.yml --check-config
   ```

### Grafana dashboards not loading

1. Verify datasources are configured:
   - Go to http://localhost:3000/datasources
   - Test each datasource connection

2. Check dashboard provisioning:
   ```bash
   ls -la infrastructure/observability/grafana/dashboards/
   ```

3. Restart Grafana:
   ```bash
   docker compose -f docker-compose.observability.yml restart grafana
   ```

### High memory usage

1. Reduce Prometheus retention:
   ```yaml
   # In prometheus/prometheus.yml
   global:
     scrape_interval: 30s  # Increase from 15s
   ```

2. Limit Loki retention:
   ```yaml
   # In loki/loki-config.yml
   limits_config:
     retention_period: 24h  # Add this
   ```

3. Restart services after configuration changes.

## Architecture

```
┌─────────────────┐
│   Nginx :8080   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Backend :8011  │────▶│  Prometheus  │
└────────┬────────┘     └──────────────┘
         │                      │
         │                      ▼
         │               ┌──────────────┐
         │               │   Grafana    │
         │               └──────────────┘
         │                      ▲
         │                      │
         ▼               ┌──────┴───────┐
┌─────────────────┐     │              │
│  Docker Logs    │────▶│     Loki     │
└─────────────────┘     │              │
         │               └──────┬───────┘
         ▼                      │
┌─────────────────┐              │
│    Promtail     │──────────────┘
└─────────────────┘

┌─────────────────┐
│     Jaeger      │ (optional, enable when needed)
│   :16686/:6831  │
└─────────────────┘
```

## Next Steps

1. **Set up alerts**: Configure Prometheus alerting rules
2. **Customize dashboards**: Modify dashboards for your needs
3. **Long-term storage**: Configure persistent volume mounts
4. **Production deployment**: Consider resource limits and security

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
