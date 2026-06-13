# Token Limitation System Testing Guide

## Overview

This document describes the comprehensive test suite for the token limitation system. The tests cover all components from repositories to API endpoints, ensuring reliable token budget and quota management.

## Test Structure

```
tests/
├── conftest.py                          # Main test configuration and fixtures
├── repositories/
│   └── test_token_repositories.py      # Repository layer tests
├── services/
│   └── test_token_services.py           # Service layer tests
├── core/
│   └── test_token_decorators.py        # Decorator and utility tests
├── api/
│   └── test_token_endpoints.py         # API endpoint tests
└── integration/
    ├── test_token_workflows.py          # Workflow integration tests
    └── test_token_system.py            # System integration tests
```

## Test Categories

### 1. Repository Tests (`test_token_repositories.py`)

Tests for database operations across all three repositories:

**TokenBudgetRepository:**
- CRUD operations (create, read, update, delete)
- Scope-based queries
- Hierarchy navigation (parents, children)
- Status-based queries (active, exhausted)
- Usage threshold queries
- Period reset operations
- Transaction handling

**TokenQuotaRepository:**
- User-based quota management
- Period tracking and reset
- Active quota queries
- Usage recording
- Status management

**TokenAlertRepository:**
- Alert creation and tracking
- Budget/quota alert association
- Acknowledgment workflow
- Critical alert queries
- Notification status tracking

### 2. Service Tests (`test_token_services.py`)

Tests for business logic in all four services:

**TokenBudgetService:**
- Token availability checking
- Usage recording and tracking
- Budget status reporting
- Hierarchy navigation
- Usage forecasting
- Period reset management
- Exhaustion detection

**TokenQuotaService:**
- Quota availability checking
- Usage recording per user
- User quota summaries
- Period reset operations
- Quota status tracking

**TokenAlertService:**
- Alert creation from thresholds
- Alert acknowledgment
- Critical alert monitoring
- Notification status tracking
- Budget/quota alert checking

**TokenReportingService:**
- Budget report generation
- User report generation
- System overview reports
- Usage trend analysis
- Top consumer identification
- Forecast data generation

### 3. Decorator Tests (`test_token_decorators.py`)

Tests for token limitation decorators:

**@check_token_budget:**
- Pre-call token availability checking
- Enforcement mode handling (hard, soft, monitoring)
- Exception raising vs. returning vs. warning
- Parameter extraction and validation
- Error handling

**@track_token_usage:**
- Post-call token usage tracking
- Budget and quota recording
- Token extraction from results
- Error handling and logging

**@enforce_token_limits:**
- Combined checking and tracking
- Integration with both services
- Complete token lifecycle

**TokenLimiter:**
- Context manager functionality
- Availability checking
- Usage tracking
- Error handling

### 4. API Endpoint Tests (`test_token_endpoints.py`)

Tests for all REST API endpoints:

**Budget Endpoints (9 endpoints):**
- POST /budgets/ - Create budget
- GET /budgets/{id} - Get budget by ID
- GET /budgets/ - List budgets
- PUT /budgets/{id} - Update budget
- DELETE /budgets/{id} - Delete budget
- GET /budgets/{id}/status - Get budget status
- POST /budgets/{id}/reset - Reset budget period
- GET /budgets/active - List active budgets
- GET /budgets/exhausted - List exhausted budgets

**Quota Endpoints (9 endpoints):**
- POST /quotas/ - Create quota
- GET /quotas/{id} - Get quota by ID
- GET /quotas/user/{user_id} - List user quotas
- PUT /quotas/{id} - Update quota
- DELETE /quotas/{id} - Delete quota
- GET /quotas/{id}/status - Get quota status
- POST /quotas/{id}/reset - Reset quota period
- GET /quotas/active/list - List active quotas
- POST /quotas/user/{user_id}/reset-all - Reset all user quotas

**Alert Endpoints (8 endpoints):**
- GET /alerts/ - List all alerts
- GET /alerts/{id} - Get alert by ID
- POST /alerts/{id}/acknowledge - Acknowledge alert
- GET /alerts/unacknowledged - List unacknowledged alerts
- GET /alerts/critical - List critical alerts
- GET /alerts/budget/{budget_id} - List budget alerts
- GET /alerts/quota/{quota_id} - List quota alerts
- POST /alerts/{id}/notification - Mark notification sent

**Analytics Endpoints (9 endpoints):**
- GET /analytics/system-overview - System overview
- GET /analytics/budget/{id}/report - Budget report
- GET /analytics/user/{user_id}/report - User report
- GET /analytics/trends - Usage trends
- GET /analytics/top-consumers - Top consumers
- GET /analytics/budget/{id}/forecast - Forecast data
- GET /analytics/exhausted-budgets - Exhausted budgets
- GET /analytics/near-limit - Budgets near limit
- GET /analytics/alerts/summary - Alert summary

### 5. Workflow Integration Tests (`test_token_workflows.py`)

Tests for token limitation in actual workflows:

**Test Generation with Tokens:**
- Availability checking before generation
- Usage recording after generation
- Budget enforcement in generation workflow

**Script Generation with Tokens:**
- Decorator-based token management
- Budget and quota tracking
- Error handling in script generation

**Test Execution with Tokens:**
- Pre-execution availability checks
- Hard vs. soft enforcement
- Execution blocking when budget exhausted

**Alert Generation Workflow:**
- Automatic alert creation on thresholds
- Multiple alerts for different thresholds
- Alert acknowledgment in workflows

**End-to-End Lifecycle:**
- Complete token lifecycle from creation to reset
- All phases: creation, usage, exhaustion, reset
- Integration across all services

### 6. System Integration Tests (`test_token_system.py`)

Comprehensive integration tests for the complete system:

**Complete Token Lifecycle:**
- Full lifecycle testing
- Multi-phase operations
- Service integration

**Budget Exhaustion Scenarios:**
- Hard enforcement blocking
- Soft enforcement with warnings
- Monitoring mode tracking only

**Quota Reset Scenarios:**
- Calendar-based reset at midnight
- Rolling reset from first use
- Period boundary handling

**Alert Generation Scenarios:**
- Warning alerts at thresholds
- Critical alerts at high thresholds
- Alert acknowledgment workflow

**Multi-User Scenarios:**
- Separate quotas per user
- User isolation
- Concurrent user operations

**Concurrent Operations:**
- Concurrent token updates
- Concurrent availability checks
- Race condition prevention

**Performance Under Load:**
- Token check performance (< 5ms target)
- Token update performance (< 10ms target)
- Concurrent operations performance
- Load testing with 100+ concurrent operations

## Running the Tests

### Run All Token Tests

```bash
# From project root
cd platform
pytest tests/repositories/test_token_repositories.py -v
pytest tests/services/test_token_services.py -v
pytest tests/core/test_token_decorators.py -v
pytest tests/api/test_token_endpoints.py -v
pytest tests/integration/test_token_workflows.py -v
pytest tests/integration/test_token_system.py -v
```

### Run Specific Test Categories

```bash
# Repository tests only
pytest tests/repositories/test_token_repositories.py -v

# Service tests only
pytest tests/services/test_token_services.py -v

# API tests only
pytest tests/api/test_token_endpoints.py -v

# Integration tests only
pytest tests/integration/test_token_system.py -v
```

### Run with Coverage

```bash
# Run with coverage report
pytest tests/ -v --cov=app/models/token_budget --cov=app/models/token_quota --cov=app/models/token_alert --cov=app/repositories/token_budget_repository --cov=app/services/token_budget_service --cov-report=html

# Generate coverage report
pytest tests/ -v --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test Cases

```bash
# Run specific test class
pytest tests/repositories/test_token_repositories.py::TestTokenBudgetRepository -v

# Run specific test method
pytest tests/repositories/test_token_repositories.py::TestTokenBudgetRepository::test_create_budget -v

# Run tests matching pattern
pytest tests/ -k "test_create_budget" -v
```

## Test Fixtures

The following fixtures are available in `conftest.py`:

### Database Fixtures
- `test_db_session` - In-memory database session
- `event_loop` - Async event loop

### User Fixtures
- `test_user` - Regular test user
- `test_admin_user` - Admin test user

### Model Fixtures
- `sample_token_budget_data` - Sample budget data dictionary
- `sample_token_budget` - Sample budget in database
- `sample_token_quota_data` - Sample quota data dictionary
- `sample_token_quota` - Sample quota in database
- `sample_token_alert_data` - Sample alert data dictionary
- `sample_token_alert` - Sample alert in database

## Coverage Goals

The test suite aims for:

- **Line Coverage**: > 80%
- **Branch Coverage**: > 70%
- **Integration Coverage**: All critical paths
- **Performance Benchmarks**: All performance tests passing

## Performance Benchmarks

The tests include performance benchmarks with the following targets:

- **Token Check**: < 5ms average
- **Token Update**: < 10ms average
- **Concurrent Operations**: 100+ concurrent requests
- **Database Queries**: Optimized with proper indexing

## Mock Strategy

The tests use the following mocking strategies:

1. **External LLM API**: Mocked to avoid actual API calls
2. **Token Services**: Mocked for unit tests
3. **Database**: Test database for integration tests
4. **Time**: Mocked for quota reset testing
5. **Webhooks**: Mocked for alert testing

## Test Data

The tests use comprehensive test data:

- Multiple budget types (organization, suite, test, user)
- Various quota configurations (daily, weekly, monthly)
- Different alert scenarios (warning, critical, emergency)
- Sample users with different roles
- Realistic token amounts and thresholds

## Success Criteria

The test suite is considered successful when:

- ✅ All test categories covered
- ✅ Repository tests comprehensive
- ✅ Service tests comprehensive
- ✅ LLM client tests working
- ✅ API endpoint tests complete
- ✅ Workflow integration tests passing
- ✅ Decorator tests functional
- ✅ Integration tests end-to-end
- ✅ Performance tests passing
- ✅ Coverage goals met
- ✅ Documentation complete

## Troubleshooting

### Common Issues

**Import Errors:**
- Ensure all dependencies are installed
- Check that `PYTHONPATH` includes `platform/backend`

**Database Errors:**
- Verify test database configuration
- Check that migrations are applied

**Async Test Errors:**
- Ensure pytest-asyncio is installed
- Use proper async/await patterns

**Performance Failures:**
- Check system load
- Verify database indexing
- Ensure proper database connection pooling

## Continuous Integration

The tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run token limitation tests
  run: |
    cd platform
    pytest tests/repositories/test_token_repositories.py -v
    pytest tests/services/test_token_services.py -v
    pytest tests/core/test_token_decorators.py -v
    pytest tests/api/test_token_endpoints.py -v
    pytest tests/integration/test_token_workflows.py -v
    pytest tests/integration/test_token_system.py -v
```

## Future Enhancements

Planned improvements to the test suite:

1. **Stress Tests**: Higher load testing (1000+ concurrent operations)
2. **Edge Case Tests**: More boundary condition testing
3. **Security Tests**: Authorization and permission testing
4. **Monitoring Tests**: Metrics and monitoring validation
5. **Documentation Tests**: API documentation validation
