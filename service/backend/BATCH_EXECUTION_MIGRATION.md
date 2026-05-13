# Service Batch Execution Migration

## Summary

Refactored service backend to match CLI architecture: **all test steps now execute in a single Claude Code session** instead of per-step API calls.

## Changes

### 1. `claude_interpreter.py`

**New Method: `interpret_and_execute_batch()`**
```python
async def interpret_and_execute_batch(
    page: Page,
    test_steps: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute all test steps in a single Claude Code session"""
```

**New Method: `_execute_batch_with_agent_sdk()`**
- Executes all steps in one session
- Tracks step completion through Claude's responses
- Returns results for all steps

**New Method: `_build_batch_execution_prompt()`**
- System prompt matches CLI architecture
- Lists all steps for Claude to execute sequentially
- Instructs Claude to continue until all steps complete or fail

**Legacy Method: `interpret_and_execute()`**
- Kept for backward compatibility
- Now wraps `interpret_and_execute_batch()` with single-step array

### 2. `test_execution.py`

**New Function: `_execute_all_steps_with_ai()`**
```python
async def _execute_all_steps_with_ai(
    page: Page,
    test_steps: List[Dict[str, Any]],
    environment: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Execute ALL steps in a single Claude Code session"""
```

**Deprecated Function: `_execute_step_with_ai()`**
- Marked as DEPRECATED
- Kept for backward compatibility
- Not used in main execution flow

**Modified: `_execute_test_async()`**
- Replaced loop calling `_execute_step_with_ai()`
- Now calls `_execute_all_steps_with_ai()` once

## Token Efficiency

**Before (Per-Step):**
```
5 steps × 1 API call each = 5 API calls
5 × (system prompt + step prompt) tokens
```

**After (Batch):**
```
5 steps × 1 API call = 1 API call
1 × (system prompt + all steps prompt) tokens
```

**Estimated Savings:**
- 80% reduction in API calls
- 60-70% reduction in token usage
- Faster execution (less network overhead)

## Architecture Comparison

| Aspect | CLI | Service (Before) | Service (After) |
|--------|-----|------------------|-----------------|
| Call Granularity | Per test case | Per step | Per test case ✓ |
| SDK | `@anthropic-ai/claude-code` | `claude-agent-sdk` | `claude-agent-sdk` |
| Steps per Session | All steps | 1 step | All steps ✓ |
| Token Efficiency | High | Low | High ✓ |

## Testing

To test the refactored implementation:

```bash
# Start services
cd service/docker-compose
docker-compose up -d backend scheduler-worker

# Run a scheduled test
docker-compose exec scheduler-worker celery -A app.core.celery_app call app.tasks.schedule_sync.execute_scheduled_tests

# Check logs for "Executing X test steps in a single Claude Code session"
docker-compose logs -f scheduler-worker
```

## Backward Compatibility

- Old code using `_execute_step_with_ai()` still works
- `interpret_and_execute()` still accepts single description
- Database schema unchanged
- API endpoints unchanged

## Migration Notes

- **No database migrations required**
- **No API changes required**
- **Celery task signature unchanged**
- Pure internal refactoring for efficiency

## Future Improvements

1. Add step-by-step progress tracking during batch execution
2. Implement proper MCP server for state management (like CLI)
3. Add early termination on step failure (currently continues)
4. Collect per-step timing metrics
