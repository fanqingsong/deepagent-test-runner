---
name: test-results-summary
description: Use this skill when the user asks to summarize, explain, or analyze test execution results. Triggers on requests like "summarize my last test run", "how did the tests go", "show test results summary", "compare test runs", or "what failed in the latest run". Provides structured test result analysis with pass/fail breakdown, duration stats, and actionable insights.
module: helpers.ts
---

# test-results-summary

## Overview

This skill helps the agent produce well-structured summaries of test execution results from the E2E testing platform. Use it whenever the user wants to understand what happened during a test run.

## Instructions

### 1. Gather the data

Query the relevant test run data using the available database tools. You typically need:

- **test_runs** — overall run status, timestamps, totals
- **test_cases** — individual step results linked by `run_id`
- **test_definitions** — test names for context

Key fields to collect:
- `status` (passed / failed / error)
- `total_tests`, `passed_tests`, `failed_tests`
- `total_duration_ms` (convert to human-readable: `ms → s`)
- `created_at` for timestamp context

### 2. Compute summary metrics

Use the helper from this skill module to format durations and compute pass rates:

```typescript
const { formatDuration, passRate } = await import("@/skills/test-results-summary");

const duration = formatDuration(run.total_duration_ms);
const rate = passRate(run.passed_tests, run.total_tests);
```

### 3. Structure the response

Present results in this order:

1. **Header** — test definition name + run timestamp
2. **Status badge** — PASSED (green) or FAILED (red)
3. **Metrics** — pass rate, total duration, step count
4. **Failed steps** — list each failed step with its error message (if any)
5. **Recommendation** — suggest next action (re-run, review definition, check environment)

### 4. Keep it concise

- Don't dump raw database rows
- Round durations to 1 decimal place
- Show at most 5 failed steps; summarize the rest as "N more failures"
- Use the user's language (Chinese if they asked in Chinese)
