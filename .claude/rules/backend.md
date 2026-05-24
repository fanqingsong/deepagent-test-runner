# Backend Development

## Unified Backend Structure (FastAPI)

```
backend/app/
├── api/          # REST endpoints (organized by domain)
├── services/     # Business logic (execution, schedules, sessions)
├── tasks/        # Celery tasks (test_execution, schedule_sync)
├── models/       # SQLAlchemy ORM models
├── agents/       # LangGraph agent pipeline (supervisor_graph, executor_agent, nodes)
├── agent_tools/  # Playwright tools for browser automation
├── core/         # Configuration and security (agent_config, job_store, security)
├── schemas/      # Pydantic schemas for request/response validation
└── middleware/   # Custom middleware (auth, CORS)
```

## Critical Service Methods

- `ExecutionService.save_test_results()`: Saves both test_runs summary AND test_cases details
- `ScheduleManager.parse_cron_expression()`: Validates cron expressions

## LLM Integration

All AI features use GLM via OpenAI-compatible API (`ChatOpenAI` from `langchain_openai`)

- Config: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` env vars
- Factory: `app/core/agent_config.py` → `get_llm()`

## Service Interactions

- **Unified Backend**: test definitions, schedules, jobs, analytics, sessions
- **Celery Workers**: execute tests via LangGraph + Playwright; load test data from PostgreSQL (not HTTP self-calls)
- **Job metadata**: stored in Redis (`app/core/job_store.py`) for status polling across API restarts
