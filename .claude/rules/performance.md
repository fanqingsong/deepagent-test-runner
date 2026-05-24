# Performance Considerations

## Dashboard Queries

- Use `created_at` for filtering (always populated), not `start_time` (often NULL)
- Index on `test_runs.created_at` for time-based queries
- Join with test_definitions to get test names (add test_definition_id to queries)

## Celery Workers

- Default concurrency: 2 workers
- Scale with: `docker compose up -d --scale celery-worker=4`
- Task routing: test_execution tasks go to workers, schedule_sync to beat
