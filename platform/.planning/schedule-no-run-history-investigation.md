---
status: investigating
trigger: 创建了一个调度条目，设置为每分钟执行，但是在测试仪表盘页面，看不到运行历史
created: 2026-05-01T12:46:00Z
updated: 2026-05-01T12:46:00Z
---

## Symptoms

**Expected behavior:**
调度任务应该按设定的 cron 表达式（每分钟）执行，执行结果应该显示在测试仪表盘的运行历史中

**Actual behavior:**
创建了调度条目（每分钟执行），但在测试仪表盘页面看不到运行历史

**Error messages:**
No errors reported

**Timeline:**
Just created the schedule

**Reproduction:**
1. Created a schedule with cron expression for every minute
2. Expected to see test runs in dashboard history
3. No test runs appearing in dashboard

## Current Focus

**Hypothesis:** Schedule exists and Celery is executing, but test runs are not being created
**Test:** Verified schedule in database, checked worker logs
**Expecting:** Should see test_runs records being created every minute
**Next action:** Investigate why execute_scheduled_tests succeeds but creates no test runs

## Evidence

- timestamp: 2026-05-01T12:47:00Z
  source: Database query
  finding: Schedule exists (id=4, name="每分钟测试", cron="0 * * * *", is_active=true)
  details: Schedule is active and should execute every minute at the top of the hour

- timestamp: 2026-05-01T12:47:00Z
  source: Worker logs
  finding: execute_scheduled_tests task runs every minute
  details: |
    Logs show: "Task app.tasks.schedule_sync.execute_scheduled_tests[...] succeeded"
    Last executions: 13:17, 13:18, 13:19 (every minute as expected)

- timestamp: 2026-05-01T12:47:00Z
  source: Test runs query
  finding: Only 1 test run in last 10 minutes (created at 13:14:14)
  details: |
    Query: SELECT COUNT(*) FROM test_runs WHERE created_at > NOW() - INTERVAL '10 minutes'
    Result: 1 run
    Expected: Should have ~8-9 runs (one per minute since schedule created)

## Eliminated

- ~~Schedule not created~~ - Schedule exists in database with is_active=true
- ~~Celery worker not running~~ - Worker logs show regular execution
- ~~Cron expression issue~~ - Expression "0 * * * *" is valid (every hour at minute 0)

## Resolution

**Root cause:** TBD - needs further investigation
**Investigation needed:**
1. Check if schedule has test_definition_id assigned (may be null)
2. Verify execute_scheduled_tests task logic - why it succeeds but creates no runs
3. Check scheduler-service logs for errors during execution
4. Verify test_execution task is being called by worker

**Fix:** TBD - pending root cause identification
**Verification:** TBD
**Files changed:** TBD
