# CLAUDE.md

AI-powered E2E testing framework using GLM LLM + LangGraph + Playwright for browser automation.

## Quick Start

```bash
./start-dev.sh     # Start dev environment
./start-prod.sh    # Start prod environment
# Stop with corresponding stop scripts
```

## Architecture

```
Frontend (React/Vite :5173) → Nginx (:8080) → Unified Backend (FastAPI :8011)
                                                    ↓
                              PostgreSQL (:5432) ← Celery Worker + Beat ← Redis
```

## Project Rules

Detailed guidance is organized in `.claude/rules/`:

| Rule File | Content |
|-----------|---------|
| `development.md` | Docker commands, database operations |
| `database.md` | Schema, relationships, timestamp handling |
| `frontend.md` | Design system, routing, state management |
| `i18n.md` | Internationalization requirements |
| `backend.md` | API structure, LLM integration, services |
| `test-execution.md` | LangGraph pipeline, execution flow |
| `troubleshooting.md` | Common issues and solutions |
| `config.md` | Environment variables, port mappings |
| `performance.md` | Query optimization, worker scaling |

## Key Points

- **Hot-reload**: `backend/app/` and `frontend/src/` auto-refresh
- **Design System**: Read DESIGN.md before UI changes (IBM Carbon-inspired)
- **LLM**: GLM via OpenAI-compatible API (`app/core/agent_config.py`)
- **Token Monitoring**: Per-call LLM token usage tracked via LangChain callback (`app/core/llm_usage_callback.py`), persisted to `llm_usage` table, analytics at `/api/v1/llm-usage/`
- **Timestamps**: PostgreSQL naive datetime, use `datetime.utcnow()`
- **Feedback**: All save/submit/delete ops must show success/failure messages
