# Deep Agents Test Runner

Complete AI-powered test execution system using the [Deep Agents](https://github.com/langchain-ai/deepagents) framework from LangChain.

## Overview

This implementation provides the complete test execution framework with:

- **Built-in planning** via `write_todos` tool
- **Automatic sub-agent coordination** via `task` tool  
- **Filesystem state management** via `FilesystemBackend`
- **Standalone planner** for autonomous/conversation features
- **Playwright script generation** for deterministic execution

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Deep Agents Test Runner                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Orchestrator Agent                         │  │
│  │       Coordinates test execution workflow               │  │
│  └────────────┬──────────────────────────────────────────┘  │
│               │                                                │
│     ┌─────────┼─────────┬──────────────┬──────────────┐    │
│     │         │         │              │              │    │
│  ┌──▼────┐ ┌──▼────┐ ┌──▼────┐   ┌───▼────┐   ┌───▼────┐│
│  │Planner│ │Executor│ │Reviewer│   │Standalone│ │Script  ││
│  │ Sub-  │ │ Sub-   │ │ Sub-   │   │ Planner  │ │Generation││
│  │ Agent  │ │ Agent  │ │ Agent  │   │          │ │        ││
│  └───────┘ └────────┘ └────────┘   └──────────┘   └────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Shared Tools                         │  │
│  │  Playwright Tools │ Test Tools │ File Tools          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Main Modules

| File | Purpose |
|------|---------|
| `__init__.py` | Main entry point with unified exports |
| `config.py` | Orchestrator agent configuration |
| `planner_agent.py` | Standalone planner for conversations |
| `script_generator.py` | Playwright script generation |
| `script_executor.py` | Playwright script execution |
| `page_fetcher.py` | Page context extraction |
| `playwright_tools.py` | Browser automation tools |
| `test_tools.py` | Test management tools |
| `tools.py` | File I/O tools |
| `subagents/planner.py` | Orchestrator planner sub-agent |
| `subagents/executor.py` | Orchestrator executor sub-agent |
| `subagents/reviewer.py` | Orchestrator reviewer sub-agent |

### Usage

#### Test Execution (Orchestrator)

```python
from app.agents.deepagents_test_runner import execute_test_run

# Full pipeline execution (plan + execute + review)
result = await execute_test_run(
    goal="Test the user login flow",
    url="https://example.com/login",
    run_id="test-123",
    mode="full_pipeline",
    page=playwright_page,
)
```

#### Standalone Planning (for Conversations)

```python
from app.agents.deepagents_test_runner.planner_agent import generate_test_plan

plan = await generate_test_plan(
    goal="Test checkout flow",
    url="https://example.com/checkout",
)
```

#### Script Generation

```python
from app.agents.deepagents_test_runner import generate_playwright_script, execute_script

# Generate Playwright script
result = await generate_playwright_script(
    goal="Fill login form",
    url="https://example.com/login",
    page_context=page_content,
)

# Execute generated script
result = await execute_script(script, page)
```

## Execution Modes

| Mode | Description | Steps |
|------|-------------|-------|
| `full_pipeline` | Complete test execution | Plan → Execute → Review |
| `execute_only` | Execute pre-defined steps | Execute → Review |
| `plan_and_execute` | Generate and execute | Plan → Execute |

## File Structure

During execution, files are created in `/tmp/test_runs/{run_id}/`:

```
/tmp/test_runs/{run_id}/
├── test_plan.json           # Generated test plan
├── test_results.json        # Execution results
└── execution_summary.json   # Final summary
```

## Code Reduction

Compared to LangGraph implementation:

| Metric | LangGraph | DeepAgents | Change |
|--------|-----------|-------------|--------|
| Lines of Code | 2,519 | 1,164 | -54% |
| Routing Functions | 6 (~150 lines) | 0 | Eliminated |
| Configuration | Manual graph | Preset-based | Simplified |

## Integration

### Temporal Activity

```python
from app.temporal.activities.deepagents_activities import run_deepagents_automation

# Automatically used by test_activities.py
```

### API Endpoints

- **Test Execution**: `/api/v1/test-executions/execute`
- **Script Generation**: `/api/v1/script-generation/*`
- **Autonomous Planning**: `/api/v1/autonomous-planning/*`
- **Conversations**: `/api/v1/conversations/*`

## Troubleshooting

### Filesystem Permissions

Ensure `/tmp/test_runs/` is writable:
```bash
mkdir -p /tmp/test_runs
chmod 777 /tmp/test_runs
```

### Playwright Page Context

Ensure page is set before execution:
```python
from app.agents.deepagents_test_runner import set_executor_page

set_executor_page(playwright_page)
```
