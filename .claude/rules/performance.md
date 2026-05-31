# Performance Considerations

## Dashboard Queries

- Use `created_at` for filtering (always populated), not `start_time` (often NULL)
- Index on `test_runs.created_at` for time-based queries
- Join with test_definitions to get test names (add test_definition_id to queries)

## Temporal Workers

- Scheduling handled by Temporal Server natively
- Scale Temporal workers as needed based on test execution load
