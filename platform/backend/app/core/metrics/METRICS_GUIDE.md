# Performance Metrics Collection System

## Overview

This document describes the comprehensive performance metrics collection system implemented for the SOLID architecture. The system provides automatic instrumentation of code execution, HTTP request tracking, and health monitoring.

## Architecture

### Components

1. **Metrics Interface** (`IMetricsCollector`)
   - Abstraction for metrics collection
   - Supports multiple implementations (in-memory, Redis, Prometheus)
   - Defines standard metrics operations

2. **In-Memory Implementation** (`InMemoryMetricsCollector`)
   - Thread-safe metrics storage
   - Timing statistics with percentiles
   - Counter and gauge tracking
   - Error aggregation

3. **Metrics Decorators**
   - `@track_timing`: Track function execution time
   - `@track_errors`: Track function errors
   - `@track_metrics`: Track both timing and errors
   - `@track_counter`: Track function call counts
   - `track_operation()`: Context manager for manual timing

4. **Metrics Middleware**
   - HTTP request timing by endpoint
   - Request counts and status codes
   - Active request tracking
   - Error tracking by endpoint

5. **Metrics API**
   - `/api/v1/metrics/summary`: Get comprehensive metrics
   - `/api/v1/metrics/timing`: Get timing statistics
   - `/api/v1/metrics/counters`: Get counter values
   - `/api/v1/metrics/errors`: Get error counts
   - `/api/v1/metrics/health`: Get system health

## Installation

The metrics system is integrated into the DI container. No additional installation required.

## Configuration

Metrics collector is registered as a singleton in the DI container:

```python
# In container.py
metrics_collector = providers.Singleton(InMemoryMetricsCollector)
```

## Usage

### Basic Usage

```python
from app.core.container import get_container

# Get metrics collector
container = get_container()
metrics = container.metrics_collector()

# Record metrics
metrics.record_timing("database.query", 45.2)
metrics.record_counter("http.requests.total", 1)
metrics.record_gauge("database.connections.active", 5)
metrics.record_error("service.process", "ValueError", "Test error")

# Get statistics
stats = metrics.get_timing_stats("database.query")
print(f"Average query time: {stats.avg_ms}ms")
```

### Using Decorators

```python
from app.core.metrics.metrics_decorators import track_timing, track_metrics

@track_timing("database.user.create")
async def create_user(user_data):
    # ... implementation
    pass

@track_metrics("service.execution.create_test_run")
async def create_test_run(test_definition_id):
    # ... implementation
    pass
```

### Using Context Manager

```python
from app.core.metrics.metrics_decorators import track_operation

async def complex_operation():
    with track_operation("custom.complex_operation"):
        # ... code to time
        result = await process_data()
        return result
```

### Repository Instrumentation

```python
from app.core.metrics.metrics_decorators import track_timing, track_errors

class TestRunRepository:
    @track_timing("database.test_run.create")
    async def create(self, test_run_data):
        @track_errors("database.test_run.create")
        async def _create():
            # ... implementation
            pass

        return await _create()
```

### Service Instrumentation

```python
from app.core.metrics.metrics_decorators import track_metrics

class ExecutionService:
    @track_metrics("service.execution.create_test_run")
    async def create_test_run_v2(self, run_id, test_definition_ids, environment):
        # ... implementation
        pass
```

## Metrics Collected

### Timing Metrics

Track execution time for operations:
- Database operations (queries, inserts, updates)
- Service method execution
- LLM API calls
- Script execution
- External API calls

**Metric Names:**
- `database.{entity}.{operation}`: Database operations
- `service.{service}.{method}`: Service methods
- `llm.{model}.{operation}`: LLM calls
- `script.{operation}`: Script operations

### Counter Metrics

Track occurrences and counts:
- HTTP requests by method and endpoint
- Test runs created/completed
- Error occurrences
- Successful operations

**Metric Names:**
- `http.requests.total`: Total HTTP requests
- `http.requests.active`: Currently active requests
- `test.runs.started`: Test runs started
- `test.cases.passed`: Passed test cases

### Gauge Metrics

Track current values:
- Active database connections
- Queue sizes
- Memory usage
- Thread pool sizes

**Metric Names:**
- `database.connections.active`: Active DB connections
- `queue.execution.pending`: Pending executions

### Error Metrics

Track errors by type and operation:
- Database errors (connection, query)
- LLM API errors (timeout, rate limit)
- Validation errors
- Business logic errors

**Error Types:**
- `ValueError`: Validation errors
- `TimeoutError`: Timeout occurrences
- `ConnectionError`: Connection failures
- `RateLimitError`: Rate limit exceeded

## Statistics

### Timing Statistics

For each operation, the following statistics are calculated:

- **count**: Number of recordings
- **min_ms**: Minimum duration
- **max_ms**: Maximum duration
- **avg_ms**: Average duration
- **p50_ms**: 50th percentile (median)
- **p95_ms**: 95th percentile
- **p99_ms**: 99th percentile

### Error Statistics

Errors are aggregated by:
- Operation name
- Error type
- Total count

## API Endpoints

### Get Metrics Summary

```bash
GET /api/v1/metrics/summary
```

Returns comprehensive metrics summary including all timing, counters, gauges, and errors.

### Get Timing Metrics

```bash
GET /api/v1/metrics/timing?operation=database.query
```

Get timing statistics for specific operation or all operations.

### Get Health Metrics

```bash
GET /api/v1/metrics/health
```

Returns system health including:
- Active requests
- Total requests
- Error rates
- System status

### Get Slowest Operations

```bash
GET /api/v1/metrics/slowest?limit=10
```

Returns operations with highest average execution time.

## Health Checks

The metrics system provides health checks for:

### Database Health
- Connection pool status
- Query performance
- Error rates

### Redis Health
- Connection status
- Operation latency
- Memory usage

### LLM API Health
- API availability
- Response times
- Rate limit status

### Temporal Health
- Workflow execution rates
- Activity performance
- Error rates

## Thread Safety

The `InMemoryMetricsCollector` is thread-safe and uses locks for:
- Timing data access
- Counter updates
- Gauge modifications
- Error recording

Concurrent access from multiple threads is safe.

## Performance Impact

The metrics system is designed to have minimal performance impact:

- **Lock-free reads**: Statistics calculated on-demand
- **Efficient storage**: Lists for timings, dictionaries for counters
- **Batch operations**: Multiple recordings in single operation
- **Optional tracking**: Can be disabled for performance-critical paths

## Testing

Comprehensive tests are provided in `tests/test_metrics_collector.py`:

```bash
# Run metrics tests
pytest app/tests/test_metrics_collector.py -v
```

Test coverage includes:
- Timing recording and statistics
- Counter and gauge operations
- Error tracking
- Decorator functionality
- Thread safety
- Integration scenarios

## Best Practices

### 1. Naming Conventions

Use consistent metric naming:

```python
# Good
"database.test_run.create"
"service.execution.create_test_run"
"http.requests.get"

# Bad
"create"
"operation1"
"test"
```

### 2. Granularity

Choose appropriate granularity:

```python
# Too granular
@track_timing("database.test_run.create.transaction.flush")

# Too broad
@track_timing("database")

# Just right
@track_timing("database.test_run.create")
```

### 3. Error Context

Include error context in error tracking:

```python
try:
    await operation()
except Exception as e:
    metrics.record_error(
        "service.process",
        type(e).__name__,
        f"Failed to process {item_id}: {str(e)}"
    )
    raise
```

### 4. Percentile Monitoring

Focus on p95 and p99 percentiles rather than averages:

```python
stats = metrics.get_timing_stats("database.query")
if stats.p99_ms > 1000:
    logger.warning("Database queries exceeding 1s (p99)")
```

## Troubleshooting

### Metrics Not Recording

1. Check DI container is initialized
2. Verify metrics_collector is wired
3. Check decorator syntax
4. Review application logs

### High Memory Usage

1. Reset metrics periodically: `metrics.reset_metrics()`
2. Reduce operation granularity
3. Implement time-based data expiration
4. Consider external metrics storage (Redis, Prometheus)

### Slow Statistics Calculation

1. Reduce number of timing recordings
2. Use sampling for high-frequency operations
3. Calculate statistics on schedule rather than on-demand
4. Consider streaming percentiles algorithm

## Future Enhancements

Potential improvements for the metrics system:

1. **External Storage**: Redis, Prometheus, Graphite
2. **Time-based Expiration**: Automatic data cleanup
3. **Aggregation**: Time-window aggregation
4. **Alerting**: Automatic alert generation
5. **Dashboards**: Real-time visualization
6. **Distributed Tracing**: Request correlation
7. **Metrics Export**: Standard formats (Prometheus, StatsD)

## References

- SOLID Principles
- Dependency Injection
- Performance Monitoring Best Practices
- Observability Patterns
