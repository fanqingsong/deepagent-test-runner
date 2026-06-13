# Token Limitation User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Budget Configuration](#budget-configuration)
3. [Quota Management](#quota-management)
4. [Alert Setup](#alert-setup)
5. [Analytics Interpretation](#analytics-interpretation)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Getting Started

### Understanding the Token Limitation System

The Token Limitation System helps you manage and control LLM token usage across your organization. It provides:

- **Budgets**: Hierarchical limits for organizations, test suites, and individual tests
- **Quotas**: Personal limits for each user
- **Alerts**: Notifications when approaching or exceeding limits
- **Analytics**: Insights into usage patterns and trends

### Key Concepts

#### Token Budget

A budget represents a pool of tokens allocated to a specific scope:

- **Organization Budget**: Company-wide limit (highest level)
- **Suite Budget**: Limit for a test suite
- **Test Budget**: Limit for an individual test
- **User Budget**: Personal limit (via Quota)

#### Token Quota

A quota is a time-based limit for a specific user:

- **Daily Quota**: Resets every day
- **Weekly Quota**: Resets every week
- **Monthly Quota**: Resets every month

#### Enforcement Modes

- **Soft Mode**: Warn when exceeded, but allow usage
- **Hard Mode**: Block usage when exceeded
- **Monitoring Mode**: Track only, no enforcement

### First Steps

1. **Check Your Current Quota**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/my-quota" \
  -H "Authorization: Bearer $TOKEN"
```

2. **View Active Alerts**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/my-alerts" \
  -H "Authorization: Bearer $TOKEN"
```

3. **Check Your Usage Summary**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/summary" \
  -H "Authorization: Bearer $TOKEN"
```

## Budget Configuration

### Creating a Budget

#### Step 1: Define Budget Parameters

Before creating a budget, determine:

- **Scope**: What level (organization, suite, test, user)?
- **Period**: How long (daily, weekly, monthly, custom)?
- **Limit**: How many tokens?
- **Enforcement**: What happens when exceeded?

#### Step 2: Create the Budget

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Suite 1 Monthly Budget",
    "description": "Monthly token budget for Test Suite 1",
    "scope_type": "suite",
    "scope_id": 1,
    "period_type": "monthly",
    "period_start": "2026-06-01T00:00:00Z",
    "period_end": "2026-06-30T23:59:59Z",
    "total_tokens": 1000000,
    "priority": 5,
    "enforcement_mode": "soft",
    "alert_thresholds": {
      "warning": 80,
      "critical": 90,
      "emergency": 95
    }
  }'
```

#### Step 3: Verify Creation

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Understanding Budget Hierarchy

Budgets can be nested to create a hierarchy:

```
Organization Budget (10M tokens)
├── Suite A Budget (3M tokens)
│   ├── Test 1 Budget (500K tokens)
│   └── Test 2 Budget (500K tokens)
└── Suite B Budget (5M tokens)
    ├── Test 3 Budget (1M tokens)
    └── Test 4 Budget (1M tokens)
```

**Parent Budget Creation**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Organization Monthly Budget",
    "scope_type": "organization",
    "scope_id": 1,
    "total_tokens": 10000000,
    "enforcement_mode": "soft"
  }'
```

**Child Budget Creation**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Suite A Budget",
    "scope_type": "suite",
    "scope_id": 1,
    "parent_budget_id": 1,
    "total_tokens": 3000000,
    "enforcement_mode": "soft"
  }'
```

### Updating Budget Configuration

You can update budget settings at any time:

```bash
curl -X PUT "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_tokens": 1500000,
    "enforcement_mode": "hard",
    "alert_thresholds": {
      "warning": 70,
      "critical": 85,
      "emergency": 95
    }
  }'
```

### Checking Budget Status

Monitor your budget status regularly:

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/status/suite/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response Interpretation:**

```json
{
  "budget_id": 1,
  "name": "Test Suite 1 Budget",
  "status": "active",
  "total_tokens": 1000000,
  "used_tokens": 850000,
  "remaining_tokens": 150000,
  "usage_percentage": 85.0,
  "is_exhausted": false,
  "is_near_limit": true,
  "days_remaining": 17
}
```

- **usage_percentage**: How much of the budget has been used
- **is_near_limit**: True if usage ≥ warning threshold (80% by default)
- **is_exhausted**: True if usage = 100%
- **days_remaining**: Days until budget period ends

### Resetting a Budget

Manually reset a budget period:

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets/1/reset" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Use Cases:**

- Correcting errors in usage tracking
- Starting a new period early
- Testing budget configurations

## Quota Management

### Understanding User Quotas

Each user can have a personal quota that operates independently from budgets:

- **Scope**: Always user-specific
- **Period**: Time-based (daily, weekly, monthly)
- **Reset Strategy**: Calendar or rolling

### Creating a User Quota

**Step 1: Create Quota (Admin Only)**

```bash
curl -X POST "http://localhost:8080/api/v1/token/quotas" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "name": "Daily Developer Quota",
    "description": "Daily token limit for developers",
    "period_type": "daily",
    "reset_strategy": "calendar",
    "total_tokens": 50000,
    "priority": 5,
    "enforcement_mode": "soft",
    "alert_thresholds": {
      "warning": 80,
      "critical": 90,
      "emergency": 95
    }
  }'
```

**Step 2: User Checks Their Quota**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/my-quota" \
  -H "Authorization: Bearer $USER_TOKEN"
```

### Reset Strategies

#### Calendar Reset

Resets on calendar boundaries:

- **Daily**: Midnight (00:00:00)
- **Weekly**: Monday 00:00:00
- **Monthly**: 1st of month 00:00:00

```json
{
  "reset_strategy": "calendar",
  "period_type": "daily",
  "period_start": "2026-06-13T00:00:00Z",
  "period_end": "2026-06-13T23:59:59Z"
}
```

#### Rolling Reset

Resets based on first use:

- **Daily**: 24 hours after first use
- **Weekly**: 7 days after first use
- **Monthly**: 30 days after first use

```json
{
  "reset_strategy": "rolling",
  "period_type": "daily",
  "period_start": "2026-06-13T09:15:00Z",
  "period_end": "2026-06-14T09:15:00Z"
}
```

### Monitoring Your Quota

Check your quota status regularly:

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/1/status" \
  -H "Authorization: Bearer $TOKEN"
```

**Understanding the Response:**

```json
{
  "quota_id": 1,
  "user_id": 5,
  "name": "Daily Developer Quota",
  "total_tokens": 50000,
  "used_tokens": 42000,
  "remaining_tokens": 8000,
  "usage_percentage": 84.0,
  "status": "active",
  "is_near_limit": true,
  "period_start": "2026-06-13T00:00:00Z",
  "period_end": "2026-06-13T23:59:59Z",
  "last_reset_at": "2026-06-13T00:00:00Z"
}
```

### Updating Quota Settings

Administrators can update quota settings:

```bash
curl -X PUT "http://localhost:8080/api/v1/token/quotas/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_tokens": 75000,
    "enforcement_mode": "hard"
  }'
```

### Resetting a Quota

Manually reset a quota period:

```bash
curl -X POST "http://localhost:8080/api/v1/token/quotas/1/reset" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Alert Setup

### Understanding Alert Thresholds

Alerts are automatically generated when usage exceeds configured thresholds:

```json
{
  "alert_thresholds": {
    "warning": 80,    // Alert at 80% usage
    "critical": 90,   // Alert at 90% usage
    "emergency": 95   // Alert at 95% usage
  }
}
```

### Alert Types

1. **budget_warning**: Budget usage exceeded warning threshold
2. **budget_critical**: Budget usage exceeded critical threshold
3. **budget_emergency**: Budget usage exceeded emergency threshold
4. **quota_warning**: Quota usage exceeded warning threshold
5. **quota_critical**: Quota usage exceeded critical threshold
6. **quota_emergency**: Quota usage exceeded emergency threshold

### Viewing Active Alerts

**All Active Alerts:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Your Alerts Only:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/my-alerts" \
  -H "Authorization: Bearer $TOKEN"
```

**Filter by Severity:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts?severity=critical" \
  -H "Authorization: Bearer $TOKEN"
```

### Understanding Alert Details

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response Interpretation:**

```json
{
  "id": 1,
  "alert_type": "budget_warning",
  "severity": "warning",
  "budget_id": 1,
  "user_id": 5,
  "threshold_value": 80.0,
  "current_value": 85.0,
  "metrics_snapshot": {
    "budget_id": 1,
    "budget_name": "Test Suite 1",
    "usage_percentage": 85.0,
    "total_tokens": 1000000,
    "used_tokens": 850000
  },
  "message": "Budget 'Test Suite 1' exceeded warning threshold",
  "is_acknowledged": false,
  "created_at": "2026-06-13T10:00:00Z"
}
```

- **threshold_value**: The threshold that was triggered
- **current_value**: Current usage percentage
- **metrics_snapshot**: State at time of alert
- **is_acknowledged**: Whether alert has been acknowledged

### Acknowledging Alerts

Acknowledge alerts to indicate you've seen them:

```bash
curl -X POST "http://localhost:8080/api/v1/token/alerts/1/acknowledge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged": true}'
```

### Viewing Alert History

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/history?days_back=30" \
  -H "Authorization: Bearer $TOKEN"
```

**Use Cases:**

- Identify patterns in alert generation
- Review historical threshold breaches
- Analyze alert resolution times

### Configuring Alert Notifications

Configure how alerts are delivered:

```bash
curl -X PUT "http://localhost:8080/api/v1/token/alerts/config?enable_email=true&enable_webhook=true&webhook_url=https://hooks.company.com/alerts" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Notification Channels:**

- **Email**: Sent to user's email address
- **Webhook**: POST to configured URL
- **In-App**: Displayed in notification center

## Analytics Interpretation

### Understanding Usage Summaries

Get overall usage statistics:

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/summary" \
  -H "Authorization: Bearer $TOKEN"
```

**Key Metrics:**

```json
{
  "overview": {
    "total_tokens": 1500000,
    "total_requests": 375,
    "average_tokens_per_request": 4000,
    "total_cost": 45.00
  },
  "by_scope_type": {
    "organization": {
      "tokens": 500000,
      "requests": 50,
      "percentage": 33.3
    },
    "suite": {
      "tokens": 600000,
      "requests": 150,
      "percentage": 40.0
    }
  }
}
```

- **average_tokens_per_request**: Average tokens consumed per LLM call
- **total_cost**: Estimated cost based on token usage
- **by_scope_type**: Distribution across different scopes

### Analyzing Usage Trends

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/trends?period=daily&days_back=30" \
  -H "Authorization: Bearer $TOKEN"
```

**Trend Analysis:**

```json
{
  "trend": {
    "direction": "increasing",
    "rate": 0.15,
    "change_percentage": 15.0
  },
  "statistics": {
    "average_daily": 50000,
    "median_daily": 48000,
    "max_daily": 85000,
    "min_daily": 25000
  }
}
```

- **direction**: increasing, decreasing, or stable
- **rate**: Rate of change per period
- **change_percentage**: Percentage change over period

### Forecasting Usage

Predict when budgets will be exhausted:

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/forecasts?budget_id=1&forecast_days=30" \
  -H "Authorization: Bearer $TOKEN"
```

**Forecast Interpretation:**

```json
{
  "current_usage": {
    "usage_percentage": 85.0,
    "remaining_tokens": 150000
  },
  "forecast": {
    "average_daily_usage": 28000,
    "days_until_exhaustion": 5,
    "exhaustion_date": "2026-06-18T00:00:00Z",
    "confidence": 0.85
  },
  "recommendations": [
    "Budget will be exhausted in 5 days",
    "Consider increasing budget limit"
  ]
}
```

- **days_until_exhaustion**: Estimated days until budget runs out
- **confidence**: Confidence level in forecast (0-1)
- **recommendations**: Actionable suggestions

### Comparing Budget Performance

Compare multiple budgets:

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/comparisons?budget_ids=1,2,3" \
  -H "Authorization: Bearer $TOKEN"
```

**Use Cases:**

- Compare different test suites
- Identify high-consumption areas
- Allocate resources effectively

## Common Workflows

### Workflow 1: Setting Up a New Test Suite

**Scenario:** Creating a new test suite with budget controls

**Step 1: Create Suite Budget**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Test Suite Budget",
    "scope_type": "suite",
    "scope_id": 5,
    "period_type": "monthly",
    "total_tokens": 2000000,
    "enforcement_mode": "soft",
    "alert_thresholds": {
      "warning": 70,
      "critical": 85,
      "emergency": 95
    }
  }'
```

**Step 2: Create Individual Test Budgets**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Login Test Budget",
    "scope_type": "test",
    "scope_id": 10,
    "parent_budget_id": 5,
    "total_tokens": 500000,
    "enforcement_mode": "soft"
  }'
```

**Step 3: Assign User Quotas**

```bash
curl -X POST "http://localhost:8080/api/v1/token/quotas" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 8,
    "name": "Developer Quota",
    "period_type": "daily",
    "total_tokens": 25000,
    "enforcement_mode": "soft"
  }'
```

**Step 4: Monitor Initial Usage**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/by-scope/suite?start_date=2026-06-01" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Workflow 2: Responding to Alerts

**Scenario:** Received a critical alert about budget exhaustion

**Step 1: Check Alert Details**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/15" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 2: Review Current Usage**

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/status/suite/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 3: Analyze Usage Trends**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/trends?period=daily&days_back=7" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 4: Take Action**

Option A: Increase Budget (if justified)

```bash
curl -X PUT "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"total_tokens": 3000000}'
```

Option B: Identify High-Consumption Tests

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/by-scope/test?start_date=2026-06-01" \
  -H "Authorization: Bearer $TOKEN"
```

Option C: Acknowledge Alert (if addressed)

```bash
curl -X POST "http://localhost:8080/api/v1/token/alerts/15/acknowledge" \
  -H "Authorization: Bearer $TOKEN"
```

### Workflow 3: Monthly Budget Review

**Scenario:** Review and adjust budgets for the next month

**Step 1: Review Past Month's Usage**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/summary?start_date=2026-05-01&end_date=2026-05-31" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Step 2: Check Budget Performance**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/budget-performance?budget_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Step 3: Review Alert History**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/stats/summary?days_back=30" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Step 4: Adjust Budgets Based on Insights**

```bash
curl -X PUT "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_tokens": 2500000,
    "period_start": "2026-06-01T00:00:00Z",
    "period_end": "2026-06-30T23:59:59Z"
  }'
```

**Step 5: Reset Budget Periods**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets/1/reset" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Workflow 4: Cost Optimization

**Scenario:** Identify opportunities to reduce token consumption

**Step 1: Analyze Model Usage**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/model-usage?start_date=2026-05-01" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 2: Identify High-Cost Agents**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/agent-usage?start_date=2026-05-01" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 3: Find Inefficient Tests**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/by-scope/test?start_date=2026-05-01" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 4: Compare with Similar Tests**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/comparisons?budget_ids=10,11,12" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 5: Implement Optimizations**

Based on analysis:
- Switch to more efficient models where appropriate
- Optimize prompts to reduce token count
- Cache common queries
- Batch similar requests

## Troubleshooting

### Issue: "Token budget exceeded" Error

**Symptoms:**

```json
{
  "error": "token_budget_exceeded",
  "message": "Token budget exceeded for suite:1",
  "requested_tokens": 15000,
  "available_tokens": 5000
}
```

**Causes:**

1. Budget limit reached
2. Insufficient remaining tokens
3. Hard enforcement mode blocking usage

**Solutions:**

1. Check current status:

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/status/suite/1" \
  -H "Authorization: Bearer $TOKEN"
```

2. Wait for budget reset (check `days_remaining`)

3. Request budget increase (contact admin):

```bash
# Admin action
curl -X PUT "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"total_tokens": 2000000}'
```

4. Reduce requested tokens (optimize prompts)

### Issue: Alerts Not Received

**Symptoms:**

- No alerts generated despite exceeding thresholds
- Alerts not visible in my-alerts endpoint

**Causes:**

1. Alert configuration not enabled
2. Notification channels not configured
3. Thresholds not triggered

**Solutions:**

1. Check alert configuration:

```bash
curl -X PUT "http://localhost:8080/api/v1/token/alerts/config?enable_email=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

2. Verify threshold settings:

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $TOKEN"
```

3. Check alert history:

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/history?days_back=7" \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: Usage Not Tracking

**Symptoms:**

- Token usage not increasing
- Analytics showing zero usage
- Budget/quota not updating

**Causes:**

1. LLM calls not wrapped with decorators
2. Token usage not being tracked
3. Database connection issues

**Solutions:**

1. Verify decorator usage:

```python
# Ensure decorators are applied
@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id"
)
async def generate_test_plan(...):
    pass
```

2. Check database connectivity:

```bash
# Check if service is running
docker ps | grep cc-test-postgres
```

3. Review logs for errors:

```bash
docker logs cc-test-backend --tail 100
```

### Issue: Incorrect Usage Calculations

**Symptoms:**

- Usage percentage seems wrong
- Tokens don't match actual LLM usage

**Causes:**

1. Token estimation vs actual usage
2. Cached calculations not updating
3. Multiple budget/quota sources

**Solutions:**

1. Check actual LLM usage:

```bash
curl -X GET "http://localhost:8080/api/v1/llm-usage/?start_date=2026-06-01" \
  -H "Authorization: Bearer $TOKEN"
```

2. Compare with budget service:

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/summary?start_date=2026-06-01" \
  -H "Authorization: Bearer $TOKEN"
```

3. Force recalculation (reset budget):

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets/1/reset" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Best Practices

### 1. Budget Planning

**Start Conservative**

- Begin with lower limits and increase as needed
- Monitor usage patterns before committing to large budgets
- Use soft enforcement initially to understand usage

**Plan for Growth**

- Allocate 20-30% buffer above expected usage
- Consider seasonal variations in testing activity
- Plan for new test suites and features

**Use Hierarchy Effectively**

```
Organization (10M) ──┬── Suite A (3M)
                      ├── Suite B (5M)
                      └── Suite C (2M)
```

- Ensure parent budgets accommodate all children
- Leave headroom for new child budgets
- Monitor parent vs. child usage ratios

### 2. Quota Management

**Fair Distribution**

- Base quotas on role requirements (developers > testers > viewers)
- Consider daily vs. weekly vs. monthly patterns
- Provide reasonable limits that don't hinder productivity

**Calendar vs. Rolling**

- **Use Calendar** for consistent, predictable resets
- **Use Rolling** for usage-based periods

**Example Quotas:**

| Role | Daily | Weekly | Monthly |
|------|-------|--------|---------|
| Senior Developer | 75K | 500K | 2M |
| Developer | 50K | 350K | 1.5M |
| Tester | 25K | 150K | 600K |
| Viewer | 10K | 50K | 200K |

### 3. Alert Configuration

**Progressive Thresholds**

```json
{
  "warning": 70,     // Early warning
  "critical": 85,    // Action needed
  "emergency": 95    // Immediate attention
}
```

- **70-80%**: Warning (review usage)
- **85-90%**: Critical (plan action)
- **95%+**: Emergency (immediate action required)

**Response Times**

- **Warning**: Review within 24 hours
- **Critical**: Address within 4 hours
- **Emergency**: Address immediately

**Acknowledgment Workflow**

1. Receive alert
2. Review details and impact
3. Take corrective action
4. Acknowledge alert
5. Monitor for recurrence

### 4. Monitoring and Review

**Daily Checks**

- Check your quota status
- Review any new alerts
- Acknowledge resolved alerts

**Weekly Reviews**

- Analyze usage trends
- Compare with previous weeks
- Identify anomalous patterns

**Monthly Audits**

- Review budget performance
- Analyze cost breakdown
- Adjust thresholds and limits
- Plan for next month

**Quarterly Planning**

- Evaluate overall token strategy
- Adjust hierarchy and allocations
- Review alert effectiveness
- Plan for growth and changes

### 5. Cost Optimization

**Model Selection**

- Use smaller models for simple tasks
- Reserve large models for complex operations
- Cache repeated queries

**Prompt Engineering**

- Optimize prompts for conciseness
- Remove unnecessary context
- Use system messages effectively

**Batch Processing**

- Combine multiple small requests
- Process tests in batches
- Reduce overhead

**Example Savings:**

- Optimized prompts: 20-30% reduction
- Model selection: 40-60% cost reduction
- Caching: 50-90% reduction for repeated queries

### 6. Team Communication

**Alert Notifications**

- Configure email for critical alerts
- Use webhooks for team communication
- Set up escalation procedures

**Usage Reports**

- Share weekly summaries with team
- Highlight cost-saving opportunities
- Recognize efficient usage

**Documentation**

- Document budget decisions
- Share quota policies
- Maintain runbooks for common issues

---

**Next:** See [Developer Guide](TOKEN_LIMITATION_DEVELOPER.md) for integration examples and code samples.