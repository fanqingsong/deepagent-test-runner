# Tests

This directory contains the test suite for the unified backend service.

## Test Files

- **conftest.py** - Pytest configuration and fixtures
- **test_api.py** - API endpoint tests
- **test_execution_service.py** - Test execution service tests
- **test_models.py** - Database model tests
- **test_schedule_manager.py** - Schedule manager tests
- **test_schedule_sync.py** - Schedule synchronization tests
- **test_schemas.py** - Pydantic schema validation tests
- **test_test_generation.py** - Test generation service tests

## Running Tests

### Inside Docker Container

```bash
# Run all tests
docker exec -it cc-test-unified-backend pytest app/tests/

# Run specific test file
docker exec -it cc-test-unified-backend pytest app/tests/test_api.py -v

# Run with coverage
docker exec -it cc-test-unified-backend pytest app/tests/ --cov=app --cov-report=html
```

### Locally

```bash
cd docker-compose

# Ensure dependencies are installed
pip install -r unified-backend-service/requirements.txt

# Run all tests
cd unified-backend-service
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_api.py -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=html
```

## Test Coverage

The test suite covers:
- API endpoints (authentication, users, tests, schedules)
- Database models and relationships
- Service layer (execution, scheduling, test generation)
- Schema validation

## Notes

- Tests use pytest and pytest-asyncio for async test support
- Database tests use SQLite in-memory database for speed
- Some integration tests may require PostgreSQL and Redis to be running
