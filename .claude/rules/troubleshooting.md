# Common Issues and Solutions

## Scheduled tests not executing

**Solution:** Check Temporal Server logs, verify schedule is_active=true, ensure cron expression is valid

## Test results not showing in dashboard

**Solution:** Verify `test_cases` records are created (check `run_id` foreign key), ensure JOIN includes test_definitions table

## Hot-reload not working

**Solution:** Volume mounts are in docker-compose.yml, changes should auto-apply. If not, restart the specific service.

## "测试用例总数" mismatch (72 vs 4)

**Solution:** Use `COUNT(*) FROM test_definitions` for test count, not `SUM(total_tests) FROM test_runs`

## Invalid Date in frontend

**Solution:** Database timestamps are milliseconds, use `new Date(parseInt(timestamp))` in JavaScript

## Schedule executing infinitely

**Solution:** Check `next_run_time` is properly updated after execution, verify `is_active` status
