# Database Schema

## Core Tables

- `test_definitions`: Test case definitions (the "what")
- `test_steps`: Sequential steps for each test definition
- `test_runs`: Execution instances with status and timestamps
- `test_cases`: Individual test step results (linked to test_runs)
- `schedules`: Cron-based test scheduling configurations
- `test_suites`: Collections of test definitions

## Important Relationships

```
test_runs.test_definition_id → test_definitions.id
test_cases.run_id → test_runs.id (execution details)
test_cases.test_definition_id → test_definitions.id
schedules.test_definition_id → test_definitions.id (single test)
schedules.test_suite_id → test_suites.id (multiple tests)
```

## Critical Field Distinctions

- `test_runs.total_tests`: Number of test steps in this run (cumulative)
- `test_runs.total_duration_ms`: Execution duration in milliseconds
- `test_cases.duration`: Individual step duration in milliseconds
- For "test case总数" use `COUNT(*) FROM test_definitions`, NOT `SUM(total_tests) FROM test_runs`

## Timestamp Handling

- All timestamps in PostgreSQL are naive datetime (no timezone)
- Use `datetime.utcnow()` for consistency, not `datetime.now(timezone.utc)`
- JavaScript timestamps are milliseconds, PostgreSQL timestamps are seconds
- Use `new Date(parseInt(timestamp))` in JavaScript to convert
