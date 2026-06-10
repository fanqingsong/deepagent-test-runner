# Daily Monitoring Agent Design

**Date:** 2025-01-15
**Status:** Approved
**Phase:** Implementation Planning

## Overview

A comprehensive monitoring agent that tracks system health, LLM performance, and operational metrics. Generates intelligent reports with AI-powered insights and delivers critical alerts to administrators.

## Goals

1. **Health & Reliability** — Detect problems early (test failures, slow agents, scheduling issues, resource constraints)
2. **Cost & Performance** — Track LLM token usage, optimize spending, measure execution times
3. **Business Intelligence** — Generate insights about test coverage, success trends, and system utilization over time
4. **Comprehensive Coverage** — All of the above with configurable alerts and reporting

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Agent System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Temporal    │    │   DeepAgent  │    │   FastAPI    │     │
│  │  Scheduler   ├───→│  Collector   ├───→│   Endpoints  │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                   │               │
│         ↓                   ↓                   ↓               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Activities  │    │   AI Report  │    │  Dashboard   │     │
│  │              │    │   Generator  │    │   API        │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Backend

**`agents/monitoring_agent/`**
- `collector.py` — Gathers metrics from all sources (DB, Redis, Temporal)
- `analyzer.py` — Analyzes metrics, detects anomalies, triggers alerts
- `reporter_agent.py` — DeepAgent that generates natural language summaries
- `tools.py` — Agent tools for data access

**`temporal/workflows/monitoring.py`**
- `MonitoringWorkflow` — Orchestrates monitoring tasks
- Activities: `collect_metrics`, `analyze_health`, `generate_report`, `send_alerts`

**`services/alert_service.py`**
- Evaluates alert rules against metrics
- Manages alert cooldowns and acknowledgments
- Sends emails and webhooks

**`api/v1/monitoring.py`**
- Status, history, reports, and configuration endpoints

### Frontend

**`pages/MonitoringPage.jsx`**
- Current status display with AI summary
- Metric charts and trend visualizations
- Alert center with acknowledge actions

**`components/AlertCenter.jsx`**
- List of alerts with filtering
- Acknowledge and resolve actions

**`components/AlertConfigForm.jsx`**
- Form to create/edit alert rules

## Metrics Collection

### A. Test Execution Health
- Test runs in last 24h (total, passed, failed, pass rate)
- Average test duration
- Failing tests with failure rates
- Schedule status (active, last run, missed schedules)

### B. LLM Agent Performance
- Token usage (total, by agent type)
- Estimated cost calculation
- Average response time by agent
- Slowest operations

### C. System Resources
- Database connection pool status
- Slow query count
- Temporal worker status
- Redis job store size

### D. User Activity
- Active users in last 24h
- API call volume
- Most accessed features

All metrics stored in `agent_monitoring` table with timestamps for trend analysis.

## Alert Rules

### Pre-configured Rules

| Alert Type | Condition | Severity | Delivery |
|------------|-----------|----------|----------|
| `high_failure_rate` | Test failure rate > 20% in 1 hour | Critical | Email + Webhook |
| `agent_slow_response` | Avg LLM response > 3000ms | Warning | In-app |
| `token_budget_alert` | Daily token usage > 500,000 | Critical | Email |
| `schedule_missed` | Scheduled test didn't run | Warning | In-app |
| `database_slow` | Slow queries > 10/hour | Warning | In-app |
| `worker_down` | Temporal worker not responding | Critical | Email + Webhook |

### Alert Flow

```
Metric Collection → Rule Evaluation → Alert Generation → Cooldown Check → Delivery
```

- **Critical alerts** → Email + optional webhook (Slack, Teams)
- **Warning alerts** → Dashboard notification center
- **Cooldown** → Prevent alert spam (configurable per rule, default 1 hour)
- **Acknowledgment** → Admins can acknowledge alerts, tracked in `agent_alerts` table

## AI-Powered Reports

The `reporter_agent` (DeepAgent) generates intelligent summaries:

### Input
- Collected metrics for current period
- Historical context (trends over time)
- Previous alerts and resolutions

### Output Structure

```json
{
  "status": "normal",
  "summary": "System is healthy. All 42 test runs passed successfully in the last 24 hours.",
  "highlights": [
    "✓ 100% test pass rate (42/42 tests passed)",
    "✓ Token usage decreased 15% compared to yesterday",
    "⚠ Planner agent response time increased by 200ms"
  ],
  "recommendations": [
    "Consider scaling planner agent — response times trending upward",
    "Schedule 'Login Flow' test for review — showing intermittent failures"
  ],
  "metrics": { /* full metrics JSON */ }
}
```

### AI Analysis Capabilities
- Trend detection (improving vs declining metrics)
- Anomaly identification (sudden spikes or drops)
- Root cause suggestions (correlating related metrics)
- Actionable recommendations

## Scheduling & Configuration

### Default Schedule
- Check interval: Every 6 hours
- Report time: Daily at 9:00 AM

### Admin Configurable
- `check_interval`: 1-24 hours
- `report_time`: HH:MM format
- `alert_cooldown`: Per-rule cooldown seconds

### Storage
- Settings stored in `alert_configurations` table
- Applied by Temporal Schedule at next trigger

## API Endpoints

### Monitoring Status
- `GET /api/v1/monitoring/status` — Current system status
- `GET /api/v1/monitoring/history?days=7` — Historical snapshots

### Reports
- `GET /api/v1/monitoring/reports` — List generated reports
- `GET /api/v1/monitoring/reports/{id}` — Specific report details

### Alerts
- `GET /api/v1/monitoring/alerts` — List alerts with filtering
- `POST /api/v1/monitoring/alerts/{id}/acknowledge` — Acknowledge alert
- `POST /api/v1/monitoring/alerts/{id}/resolve` — Resolve alert

### Configuration
- `GET /api/v1/monitoring/alert-configs` — List alert rules
- `POST /api/v1/monitoring/alert-configs` — Create alert rule
- `PUT /api/v1/monitoring/alert-configs/{id}` — Update alert rule
- `DELETE /api/v1/monitoring/alert-configs/{id}` — Delete alert rule

## Database Schema

Uses existing tables:
- `agent_monitoring` — Status snapshots
- `agent_alerts` — Alert history
- `alert_configurations` — Alert rule definitions

## Implementation Phases

### Phase 1: Core Infrastructure
- Metric collection service
- Temporal workflow + activities
- Basic database storage

### Phase 2: Alert System
- Alert rule evaluation
- Email delivery
- In-app notifications

### Phase 3: AI Reports
- DeepAgent reporter
- Natural language summaries
- Trend analysis

### Phase 4: Dashboard UI
- Monitoring status page
- Alert center
- Configuration forms

## Tech Stack

- **LLM**: GLM-4-plus (via existing `get_llm()`)
- **Orchestration**: Temporal (existing server)
- **Database**: PostgreSQL (existing database)
- **Email**: Existing `services/email_service.py`
- **Frontend**: React + Vite (existing framework)

## Success Criteria

1. Admins can view current system status at any time
2. Critical alerts are delivered within 5 minutes of detection
3. Daily reports are generated and stored automatically
4. AI summaries provide actionable insights
5. Configurable alert rules meet operational needs
