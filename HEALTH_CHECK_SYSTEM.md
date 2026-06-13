# Health Check System Documentation

## Overview

The Health Check System provides comprehensive monitoring of all system components with real-time health status, performance metrics, and historical trending.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Health Check System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────────┐                  │
│  │   Frontend   │────│   Health API     │                  │
│  │ Health Page  │    │   Endpoints      │                  │
│  └──────────────┘    └────────┬─────────┘                  │
│                               │                              │
│                               ▼                              │
│                      ┌─────────────────┐                    │
│                      │ Health Check    │                    │
│                      │ Service         │                    │
│                      └────────┬────────┘                    │
│                               │                              │
│              ┌────────────────┼────────────────┐            │
│              ▼                ▼                ▼            │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│     │ Database    │  │   Redis     │  │    LLM      │     │
│     │ Checker     │  │  Checker    │  │  Checker    │     │
│     └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Health Check Interface

**File:** `app/core/interfaces/health_check_interface.py`

The `IHealthChecker` interface defines the contract for all health checkers:

```python
class IHealthChecker(ABC):
    @abstractmethod
    async def check_health(self) -> ComponentHealth:
        """Perform health check for this component."""

    @abstractmethod
    def get_check_type(self) -> str:
        """Get the type/identifier of this health checker."""

    @abstractmethod
    def is_critical(self) -> bool:
        """Determine if this component is critical for system operation."""
```

### 2. Health Check Types

**File:** `app/core/health_check_types.py`

Data models and enums for health checks:

- **HealthStatus**: Enum (HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN)
- **ComponentHealth**: Individual component health result
- **HealthCheckResult**: Overall health check result
- **SystemHealth**: Extended result with aggregation logic
- **HealthCheckConfig**: Configuration for health check execution
- **HealthHistory**: Historical health data for trending

### 3. Health Checkers

Individual health checkers for each system component:

#### Database Health Checker
- **File:** `app/health/checkers/database_health_checker.py`
- **Critical:** Yes
- **Checks:** PostgreSQL connectivity, query execution, connection pool
- **Timeout:** 5 seconds

#### Redis Health Checker
- **File:** `app/health/checkers/redis_health_checker.py`
- **Critical:** Yes
- **Checks:** Redis connectivity, PING, memory usage, connections
- **Timeout:** 3 seconds

#### LLM Health Checker
- **File:** `app/health/checkers/llm_health_checker.py`
- **Critical:** No
- **Checks:** LLM API connectivity, model availability, response time
- **Timeout:** 10 seconds

#### Temporal Health Checker
- **File:** `app/health/checkers/temporal_health_checker.py`
- **Critical:** No
- **Checks:** Temporal server connectivity, namespace access
- **Timeout:** 5 seconds

#### File System Health Checker
- **File:** `app/health/checkers/filesystem_health_checker.py`
- **Critical:** Yes
- **Checks:** Disk space, directory permissions, file system access
- **Timeout:** 2 seconds
- **Warning threshold:** 80% disk usage

### 4. Health Check Service

**File:** `app/services/health_check_service.py`

Orchestrates health checks with features:

- **Parallel execution** for performance
- **Result caching** with configurable TTL
- **Critical-only checks** for quick status
- **Historical tracking** for trending
- **Safe error handling** with automatic status conversion

### 5. Health Check API

**File:** `app/api/v1/endpoints/health.py`

RESTful API endpoints:

- `GET /health` - Simple health check (200 if healthy)
- `GET /health/detailed` - Detailed health check with all components
- `GET /health/{component}` - Check specific component
- `GET /health/critical` - Check only critical components
- `GET /health/summary` - Quick status summary
- `GET /health/history` - Historical health data
- `POST /health/cache/clear` - Clear health check cache

### 6. Health Check Scheduler

**File:** `app/services/health_check_scheduler.py`

Background task for periodic health checks:

- Configurable check interval (default: 5 minutes)
- Automatic health status trending
- Alert on degraded/unhealthy status
- Status change logging

### 7. Health Check UI

**Files:** `frontend/src/pages/HealthPage.jsx/css`

React component for health monitoring:

- Overall system health status
- Individual component health
- Health check history
- Component status visualization
- Auto-refresh every 30 seconds

## Usage

### Basic Health Check

```bash
curl http://localhost:8080/api/v1/health
```

### Detailed Health Check

```bash
curl http://localhost:8080/api/v1/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-12T10:30:00Z",
  "components": {
    "database": {
      "component_name": "database",
      "status": "healthy",
      "response_time_ms": 5.23,
      "details": "Database connection successful",
      "metadata": {
        "database_size": "250MB",
        "active_connections": 5
      },
      "is_critical": true
    },
    "redis": {
      "component_name": "redis",
      "status": "healthy",
      "response_time_ms": 2.15,
      "details": "Redis connection successful",
      "metadata": {
        "redis_version": "7.0.0",
        "used_memory_human": "100MB"
      },
      "is_critical": true
    }
  },
  "total_components": 2,
  "healthy_components": 2,
  "degraded_components": 0,
  "unhealthy_components": 0
}
```

### Check Specific Component

```bash
curl http://localhost:8080/api/v1/health/database
```

### Critical Components Only

```bash
curl http://localhost:8080/api/v1/health/critical
```

### Skip Cache

```bash
curl "http://localhost:8080/api/v1/health/detailed?skip_cache=true"
```

## Health Status Levels

### HEALTHY
- All components are operational
- Response times within normal ranges
- No errors or warnings

### DEGRADED
- System is operational but with issues
- Non-critical components unhealthy
- Critical components have slow response times
- Resource usage elevated but not critical

### UNHEALTHY
- Critical components are down
- System cannot operate normally
- Immediate attention required

## Configuration

### Environment Variables

No specific environment variables required. Uses existing configuration:

- `DATABASE_URL` - For database health checks
- `REDIS_URL` - For Redis health checks
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` - For LLM health checks
- `TEMPORAL_HOST_URL`, `TEMPORAL_NAMESPACE` - For Temporal health checks

### Health Check Configuration

```python
from app.core.health_check_types import HealthCheckConfig

config = HealthCheckConfig(
    timeout_seconds=5.0,          # Timeout for each check
    parallel_execution=True,      # Execute checks in parallel
    cache_ttl_seconds=60,        # Cache time-to-live
    include_non_critical=True,   # Include non-critical components
    critical_only=False,         # Only check critical components
)
```

## Testing

### Run Health Check Tests

```bash
# From platform directory
docker compose exec backend pytest tests/health/ -v
```

### Test Coverage

- Type validation and data models
- Individual health checker implementations
- Service orchestration and caching
- API endpoint functionality
- Error handling and edge cases

## Monitoring Integration

### Prometheus Metrics

Health check results can be exported as Prometheus metrics:

```python
from prometheus_client import Gauge

health_status_gauge = Gauge('health_component_status', 'Health status', ['component'])
health_response_time = Gauge('health_response_time_ms', 'Health check response time', ['component'])
```

### Alerting

Integrate with alerting systems:

```python
# Send alert on unhealthy status
if result.status == HealthStatus.UNHEALTHY:
    send_alert(
        severity="critical",
        message=f"System unhealthy: {result.details}"
    )
```

## Best Practices

1. **Run Regular Health Checks**
   - Use the scheduler for periodic checks
   - Set appropriate check intervals (5 minutes recommended)
   - Monitor health check history

2. **Handle Degraded State**
   - System can operate with degraded non-critical components
   - Monitor degraded components and plan fixes
   - Set up alerts for degraded status

3. **Cache Management**
   - Use default cache TTL (60 seconds)
   - Clear cache when making infrastructure changes
   - Monitor cache hit rates

4. **Custom Health Checkers**
   - Implement `IHealthChecker` interface
   - Mark critical components appropriately
   - Set appropriate timeouts
   - Include useful metadata

5. **Response Time Monitoring**
   - Track component response times over time
   - Investigate sudden changes in response times
   - Set performance thresholds

## Troubleshooting

### Health Check Timeouts

**Problem:** Health checks timing out
**Solutions:**
- Increase timeout in health checker configuration
- Check network connectivity
- Verify component is running
- Check component logs

### All Components Unhealthy

**Problem:** All components showing as unhealthy
**Solutions:**
- Check network connectivity
- Verify environment variables
- Check component logs
- Restart services

### High Response Times

**Problem:** Health checks showing slow response times
**Solutions:**
- Check resource usage (CPU, memory, disk)
- Optimize database queries
- Scale components
- Check for network latency

### Cache Issues

**Problem:** Stale health check data
**Solutions:**
- Clear cache: `POST /health/cache/clear`
- Use `skip_cache=true` parameter
- Reduce cache TTL
- Check service logs

## Future Enhancements

- [ ] Advanced alerting with multiple channels
- [ ] Integration with monitoring dashboards (Grafana)
- [ ] Historical data persistence in database
- [ ] Performance trend analysis
- [ ] Automatic remediation triggers
- [ ] Dependency graph visualization
- [ ] Health check SLA monitoring
- [ ] Multi-region health checks

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [IBM Carbon Design System](https://carbondesignsystem.com/)
