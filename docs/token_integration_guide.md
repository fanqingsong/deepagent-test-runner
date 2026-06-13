# Token Integration in Test Execution Workflows

## Overview

This guide explains how token checking and tracking has been integrated into the test execution workflows using a **hybrid approach** combining decorators, direct service calls, and enhanced activities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Execution Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Schedule Triggered                                       │
│     └─> Check token availability (optional)                  │
│                                                              │
│  2. Prepare Test                                             │
│     ├─> Load test definition                                │
│     └─> Check tokens before execution (if enabled)         │
│                                                              │
│  3. Execute Browser Automation                               │
│     ├─> Run Playwright script                               │
│     └─> Track token usage (if enabled)                      │
│                                                              │
│  4. Save Results                                             │
│     ├─> Save test results                                    │
│     └─> Include token metadata                              │
│                                                              │
│  5. Handle Errors                                            │
│     ├─> Token limit exceeded → Mark failed                  │
│     └─> Token errors → Graceful degradation                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. TokenIntegrationService

**Location:** `/app/services/token_integration_service.py`

**Purpose:** Centralized service for token management in workflows.

**Key Methods:**
- `check_before_llm_call()` - Check token availability before operations
- `track_after_llm_call()` - Track token usage after operations
- `check_and_track_workflow()` - Combined workflow for complete token lifecycle
- `create_token_metadata()` - Create metadata for tracking
- `get_workflow_token_status()` - Get current token status

**Usage Example:**
```python
token_service = TokenIntegrationService()

# Before execution
check_result = await token_service.check_before_llm_call(
    scope_type="test",
    scope_id=123,
    prompt="Generate test cases",
    model="glm-4-plus",
    db=db_session
)

if not check_result["allowed"]:
    return error_response

# Execute LLM call...
# After execution
await token_service.track_after_llm_call(
    scope_type="test",
    scope_id=123,
    tokens_used=1500,
    db=db_session,
    metadata={"test_run_id": "abc123"}
)
```

### 2. Enhanced Activities

**Location:** `/app/temporal/activities/test_activities_with_tokens.py`

**New Activities:**
- `prepare_test_with_tokens` - Prepare test with token checking
- `run_browser_automation_with_tokens` - Execute with token tracking
- `save_results_with_tokens` - Save results with token metadata
- `mark_run_failed_with_tokens` - Mark failed with token error info

**Enhanced Features:**
- Token availability checking before execution
- Token usage tracking after execution
- Token error information in results
- Graceful handling of token limit errors

**Usage Example:**
```python
@activity.defn
async def prepare_test_with_tokens(input: PrepareTestInput) -> PrepareTestOutput:
    # Load test definition
    test_def = await load_test_definition(input.test_definition_id, db)

    # Check token availability
    if input.check_tokens:
        token_service = TokenIntegrationService()
        check_result = await token_service.check_before_llm_call(
            scope_type=input.scope_type,
            scope_id=int(input.test_definition_id),
            prompt=test_def.playwright_script[:1000],
            db=db
        )

        if not check_result["allowed"]:
            # Handle token limit exceeded
            pass

    return PrepareTestOutput(
        token_check_result=check_result,
        # ... other fields
    )
```

### 3. Enhanced Workflows

**Location:** `/app/temporal/workflows/test_execution_with_tokens.py`

**New Workflows:**
- `TestExecutionWorkflowWithTokens` - Test execution with token integration
- `ScriptGenerationWorkflowWithTokens` - Script generation with token tracking

**Features:**
- Integrated token checking in workflow pipeline
- Token error handling and recovery
- Token metadata in results
- Support for different enforcement modes

**Usage Example:**
```python
@workflow.defn(sandboxed=False)
class TestExecutionWorkflowWithTokens:
    @workflow.run
    async def run(self, test_definition_id: str, run_id: str) -> Dict[str, Any]:
        # Prepare with token check
        prepare_output = await workflow.execute_activity(
            "prepare_test_with_tokens",
            PrepareTestInput(
                test_definition_id=test_definition_id,
                run_id=run_id,
                check_tokens=True,
                scope_type="test"
            )
        )

        # Check if blocked
        if not prepare_output.token_check_result["allowed"]:
            return {"status": "blocked", "reason": "Token budget exceeded"}

        # Execute with token tracking
        automation_output = await workflow.execute_activity(
            "run_browser_automation_with_tokens",
            BrowserAutomationInput(track_tokens=True)
        )

        # Save with token metadata
        await workflow.execute_activity(
            "save_results_with_tokens",
            SaveResultsInput(
                run_id=run_id,
                results={
                    **automation_output,
                    "token_tracking_result": automation_output.token_tracking_result
                }
            )
        )
```

### 4. Enhanced Execution Service

**Location:** `/app/services/execution_service_with_tokens.py`

**New Methods:**
- `create_test_run_with_token_check()` - Create run with token checking
- `save_test_results_with_token_tracking()` - Save with token tracking
- `check_execution_token_availability()` - Check token availability
- `track_execution_token_usage()` - Track token usage
- `handle_token_limit_error()` - Handle token limit errors

**Usage Example:**
```python
service = ExecutionServiceWithTokens(db_session)

# Create run with token check
result = await service.create_test_run_with_token_check(
    run_id="test123",
    test_definition_ids=[1, 2, 3],
    environment={},
    db=db,
    check_tokens=True,
    scope_type="test"
)

if result.is_error():
    # Handle token budget exceeded
    error_details = result.error_details
    return error_response

# Save results with token tracking
await service.save_test_results_with_token_tracking(
    run_id="test123",
    results={
        "status": "passed",
        "tokens_used": 1500,
        # ... other fields
    },
    db=db,
    track_tokens=True
)
```

## Integration Approaches

### Approach 1: Decorator Approach (Recommended for LLM Services)

Use the `@enforce_token_limits` decorator for automatic token management.

**When to use:**
- LLM service methods
- Functions that make direct LLM calls
- When you want automatic checking and tracking

**Example:**
```python
from app.core.decorators.token_decorators import enforce_token_limits

@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id",
    enforcement_mode="soft"
)
async def generate_test_script(
    prompt: str,
    scope_type: str,
    scope_id: int,
    user_id: int,
    **kwargs
):
    # Function body - token checking and tracking is automatic
    llm_response = await llm_client.generate(prompt)
    return llm_response
```

### Approach 2: Direct Integration (Recommended for Workflows)

Use `TokenIntegrationService` directly in workflows and activities.

**When to use:**
- Temporal workflows and activities
- Complex multi-step operations
- When you need fine-grained control

**Example:**
```python
async def workflow_with_tokens(test_id: int, run_id: str):
    token_service = TokenIntegrationService()

    # Check before
    check = await token_service.check_before_llm_call(
        scope_type="test",
        scope_id=test_id,
        prompt="Execute test",
        db=db
    )

    if not check["allowed"]:
        return {"error": "Token budget exceeded"}

    # Execute
    result = await execute_test()

    # Track after
    await token_service.track_after_llm_call(
        scope_type="test",
        scope_id=test_id,
        tokens_used=result.tokens_used,
        db=db
    )

    return result
```

### Approach 3: Enhanced Services (Recommended for Business Logic)

Use enhanced service classes with built-in token management.

**When to use:**
- High-level business logic
- Service layer integration
- When you want consistent token handling across methods

**Example:**
```python
service = ExecutionServiceWithTokens(db)

# Create with token check
run_result = await service.create_test_run_with_token_check(
    run_id="test123",
    test_definition_ids=[1],
    environment={},
    db=db,
    check_tokens=True
)

# Save with token tracking
save_result = await service.save_test_results_with_token_tracking(
    run_id="test123",
    results=test_results,
    db=db,
    track_tokens=True
)
```

## Error Handling

### Token Budget Exceeded

**Error Type:** `TokenBudgetExceeded`

**Handling:**
```python
from app.core.exceptions.token_exceptions import TokenBudgetExceeded

try:
    result = await execute_with_tokens()
except TokenBudgetExceeded as e:
    logger.error(f"Token budget exceeded: {e}")
    # Handle error - mark run as failed, notify user, etc.
    await handle_token_error(e)
```

**Response Format:**
```python
{
    "error": "token_budget_exceeded",
    "message": "Token budget exceeded for test:123",
    "budget_id": 1,
    "scope_type": "test",
    "scope_id": 123,
    "requested_tokens": 5000,
    "available_tokens": 1000,
    "enforcement_mode": "hard"
}
```

### Token Quota Exceeded

**Error Type:** `TokenQuotaExceeded`

**Handling:**
```python
from app.core.exceptions.token_exceptions import TokenQuotaExceeded

try:
    result = await execute_with_tokens()
except TokenQuotaExceeded as e:
    logger.error(f"User quota exceeded: {e}")
    # Handle quota exceeded error
    await handle_quota_error(e)
```

**Response Format:**
```python
{
    "error": "token_quota_exceeded",
    "message": "User quota exceeded for user 456",
    "user_id": 456,
    "tokens_used": 50000,
    "quota_limit": 100000
}
```

## Configuration

### Environment Variables

```bash
# Token enforcement mode (hard, soft, monitoring)
TOKEN_ENFORCEMENT_MODE=soft

# Default token limits
DEFAULT_TEST_TOKEN_LIMIT=10000
DEFAULT_SUITE_TOKEN_LIMIT=100000
DEFAULT_ORGANIZATION_TOKEN_LIMIT=1000000

# Alert thresholds
TOKEN_ALERT_THRESHOLD=80
TOKEN_WARNING_THRESHOLD=90
```

### Enforcement Modes

**Hard Mode:**
- Blocks operations when budget exceeded
- Requires manual intervention
- Use for strict cost control

**Soft Mode:**
- Warns when budget exceeded
- Allows operations to continue
- Use for monitoring without blocking

**Monitoring Mode:**
- Only tracks usage
- Never blocks operations
- Use for analytics and reporting

## Testing

### Unit Tests

```python
import pytest
from app.services.token_integration_service import TokenIntegrationService

@pytest.mark.asyncio
async def test_check_before_llm_call():
    service = TokenIntegrationService()

    result = await service.check_before_llm_call(
        scope_type="test",
        scope_id=123,
        prompt="Test prompt",
        db=test_db
    )

    assert result["allowed"] == True
    assert result["estimated_tokens"] > 0

@pytest.mark.asyncio
async def test_track_after_llm_call():
    service = TokenIntegrationService()

    result = await service.track_after_llm_call(
        scope_type="test",
        scope_id=123,
        tokens_used=1500,
        db=test_db
    )

    assert result["tracked"] == True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_workflow_with_tokens():
    # Create workflow
    workflow = TestExecutionWorkflowWithTokens()

    # Execute with token checking
    result = await workflow.run(
        test_definition_id="1",
        run_id="test123",
        check_tokens=True,
        track_tokens=True
    )

    # Verify token information in results
    assert "token_check_result" in result
    assert "token_tracking_result" in result
```

## Monitoring

### Metrics to Track

1. **Token Usage Metrics**
   - Tokens used per test execution
   - Tokens used per test suite
   - Tokens used per organization

2. **Budget Status Metrics**
   - Budget exhaustion rate
   - Budget warning triggers
   - Budget recovery events

3. **Error Metrics**
   - Token budget exceeded errors
   - Token quota exceeded errors
   - Token check failures

### Logging

```python
logger.info(
    f"Token check passed for test {test_id}: "
    f"requested={requested_tokens}, "
    f"available={available_tokens}, "
    f"percentage={usage_percentage}%"
)

logger.warning(
    f"Token budget exceeded for test {test_id}: "
    f"enforcement={enforcement_mode}, "
    f"action={enforcement_action}"
)
```

## Best Practices

### 1. Always Check Before LLM Calls

```python
# Good
check = await token_service.check_before_llm_call(...)
if not check["allowed"]:
    return error_response
result = await llm_call(...)

# Bad
result = await llm_call(...)  # No token check
```

### 2. Always Track After LLM Calls

```python
# Good
result = await llm_call(...)
await token_service.track_after_llm_call(
    tokens_used=result.tokens_used
)

# Bad
result = await llm_call(...)  # No tracking
```

### 3. Use Appropriate Enforcement Modes

```python
# For critical production tests
enforcement_mode="hard"

# For development/testing
enforcement_mode="soft"

# For analytics only
enforcement_mode="monitoring"
```

### 4. Include Token Metadata

```python
metadata = {
    "operation": "test_execution",
    "test_run_id": run_id,
    "test_definition_id": test_id,
    "model": "glm-4-plus",
    "timestamp": datetime.utcnow().isoformat()
}

await token_service.track_after_llm_call(
    metadata=metadata
)
```

## Migration Guide

### From Legacy ExecutionService

**Before:**
```python
service = ExecutionService(db)
run = await service.create_test_run(run_id, test_ids, env, db)
```

**After:**
```python
service = ExecutionServiceWithTokens(db)
result = await service.create_test_run_with_token_check(
    run_id, test_ids, env, db,
    check_tokens=True
)
if result.is_error():
    handle_error(result)
run = result.data
```

### From Legacy Activities

**Before:**
```python
@activity.defn
async def prepare_test(input: PrepareTestInput):
    # Load and return test data
    return prepare_output
```

**After:**
```python
@activity.defn
async def prepare_test_with_tokens(input: PrepareTestInput):
    # Check tokens first
    if input.check_tokens:
        check_result = await check_tokens(input.test_definition_id)

    # Load and return test data
    return PrepareTestOutput(
        token_check_result=check_result
    )
```

## Troubleshooting

### Token Checks Blocking Execution

**Issue:** Tests being blocked due to token limits

**Solutions:**
1. Check enforcement mode (use "soft" for development)
2. Increase token budget limits
3. Review token estimation accuracy
4. Check budget hierarchy and inheritance

### Token Tracking Not Working

**Issue:** Token usage not being tracked

**Solutions:**
1. Verify database session is passed correctly
2. Check token_service is initialized
3. Verify metadata is being passed
4. Check for errors in service logs

### Performance Impact

**Issue:** Token checks slowing down execution

**Solutions:**
1. Use monitoring mode for critical paths
2. Cache token availability checks
3. Use async token checking
4. Batch token tracking operations

## Future Enhancements

1. **Real-time Token Monitoring**
   - WebSocket-based token updates
   - Live dashboard for token usage
   - Predictive token exhaustion alerts

2. **Smart Token Allocation**
   - Dynamic token budget adjustment
   - Priority-based token allocation
   - Token borrowing between budgets

3. **Advanced Analytics**
   - Token usage patterns
   - Cost optimization recommendations
   - Token efficiency metrics

## Summary

The token integration provides a comprehensive solution for managing LLM token usage in test execution workflows. By using the hybrid approach of decorators, direct service calls, and enhanced services, you can:

- **Control costs** through budget limits and enforcement modes
- **Monitor usage** with comprehensive tracking and analytics
- **Handle errors** gracefully with proper error handling
- **Maintain performance** with minimal overhead
- **Scale easily** with flexible architecture

Choose the integration approach that best fits your use case, and always ensure proper token checking and tracking for LLM operations.
