# Deep Agents Implementation Guide

## Overview

This guide documents the Deep Agents test runner implementation, which replaces the previous LangGraph-based test runner. The migration reduced code complexity by ~54%.

### Key Improvements

| Metric | LangGraph | DeepAgents | Change |
|--------|-----------|-------------|--------|
| **Lines of Code** | 2,519 | 1,164 | -54% |
| **Routing Functions** | 6 (~150 lines) | 0 | Eliminated |
| **Configuration** | Manual graph building | Preset-based | Simplified |
| **Sub-Agent Coordination** | Custom implementation | Built-in `task()` tool | Native |
| **Planning** | Custom planner node | Built-in `write_todos` | Native |

## Architecture

### DeepAgents Implementation

```
orchestrator_agent (DeepAgents)
├── Workflow prompt (declarative)
├── Planner subagent (via task())
├── Executor subagent (via task())
└── Reviewer subagent (via task())
```

## Configuration

### Verification

Run the validation script:

```bash
cd platform/backend
python scripts/validate_deepagents_migration.py --run-id <existing_run_id> --test-id <test_definition_id>
```

## Configuration Options

### Presets

Configure agent behavior via presets:

| Preset | Model | Description |
|--------|-------|-------------|
| `fast` | Haiku 4.5 | Quickest execution, suitable for smoke tests |
| `balanced` | Sonnet 4.6 | Default balance of speed and quality |
| `thorough` | Opus 4.7 | Maximum analysis, suitable for critical flows |

```bash
DEEPAGENTS_PRESET=thorough
```

### Model Selection

Use any Claude model:

```bash
DEEPAGENTS_MODEL=anthropic:claude-opus-4-7
```

### Retry Configuration

Max retries for failed steps:

```bash
DEEPAGENTS_MAX_RETRIES=5
```

## Verification Procedures

### 1. Database Consistency

```bash
# Connect to PostgreSQL
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db

# Check test_runs records
SELECT run_id, status, total_tests, passed, failed 
FROM test_runs 
ORDER BY created_at DESC 
LIMIT 5;

# Check test_cases details
SELECT run_id, step_number, description, status 
FROM test_cases 
WHERE run_id = '<your_run_id>' 
ORDER BY step_number;
```

### 2. Filesystem Output

```bash
# Check generated files
ls -la /tmp/test_runs/<run_id>/

# Should contain:
# - test_plan.json (planner output)
# - test_results.json (final results)
# - step_N.json (individual step results)
# - step_N.png (screenshots, if any)
```

### 3. LLM Usage Tracking

```bash
# Query token usage
curl http://localhost:8080/api/v1/llm-usage/by-test-run/<run_id>
```

## Testing Guidelines

### Unit Tests

```bash
cd platform/backend
pytest app/tests/test_deepagents_integration.py -v
```

### Integration Tests

```bash
# Run with feature flag enabled
DEEPAGENTS_ENABLED=true pytest app/tests/test_deepagents_integration.py -v
```

### E2E Tests

Execute full test suite via dashboard:

1. Navigate to Studio
2. Create test definition
3. Execute test run
4. Verify results in Dashboard

## Troubleshooting

### Issue: Import errors for DeepAgents modules

**Symptom:** `ModuleNotFoundError: No module named 'app.agents.deepagents_test_runner'`

**Solution:**
```bash
cd platform/backend
pip install -e .
```

### Issue: Results inconsistent between implementations

**Symptom:** Validation script shows differences

**Solution:**
1. Check orchestrator workflow prompt matches expected phases
2. Verify sub-agent tools are properly registered
3. Review logs for agent execution errors

### Issue: Filesystem permissions

**Symptom:** `PermissionError: /tmp/test_runs/<run_id>`

**Solution:**
```bash
sudo mkdir -p /tmp/test_runs
sudo chmod 777 /tmp/test_runs
```

### Issue: Agent timeouts

**Symptom:** `TimeoutError` during execution

**Solution:**
1. Increase `API_TIMEOUT_MS` in `.env`
2. Switch to faster preset (`fast` or `balanced`)
3. Check network connectivity to LLM API

## Performance Comparison

Based on initial testing:

| Metric | LangGraph | DeepAgents |
|--------|-----------|-------------|
| **Cold Start** | ~3s | ~2s |
| **Plan Generation** | ~8s | ~6s |
| **Step Execution** | ~2s/step | ~2s/step |
| **Result Review** | ~4s | ~3s |
| **Total (10 steps)** | ~35s | ~31s |

*Times vary by test complexity and model selection.*

## Support

For issues or questions:

1. Check logs: `docker compose logs -f backend`
2. Run validation: `python scripts/validate_deepagents_migration.py`
3. Review test results: `platform/backend/app/tests/test_deepagents_integration.py`

## References

- DeepAgents Documentation: [Internal docs]
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Claude API Documentation: https://docs.anthropic.com/
