# Token Limitation Developer Guide

## Table of Contents

1. [Integration Overview](#integration-overview)
2. [Service Usage](#service-usage)
3. [Decorator Integration](#decorator-integration)
4. [LLM Client Integration](#llm-client-integration)
5. [Testing Strategies](#testing-strategies)
6. [Extension Points](#extension-points)
7. [Code Examples](#code-examples)
8. [Performance Optimization](#performance-optimization)

## Integration Overview

The Token Limitation System provides multiple integration patterns for managing token usage:

### Integration Methods

1. **Decorator-Based**: Automatic token checking and tracking
2. **Service-Based**: Direct service calls for fine-grained control
3. **Context Manager**: Explicit token management with context
4. **Middleware**: Global token enforcement

### Choosing an Integration Method

| Method | Use Case | Complexity | Control |
|--------|----------|------------|---------|
| Decorator | Standard LLM calls | Low | Automatic |
| Service | Custom workflows | Medium | Manual |
| Context Manager | Complex flows | High | Explicit |
| Middleware | Global enforcement | High | Global |

## Service Usage

### Direct Service Integration

Use services directly for maximum control:

```python
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.core.database import get_db

async def generate_test_with_token_check(
    prompt: str,
    test_id: int,
    user_id: int
):
    """Generate test with manual token checking."""
    
    # Get database session
    db = await get_db().__aenter__()
    
    try:
        # Initialize services
        budget_service = TokenBudgetService()
        quota_service = TokenQuotaService()
        
        # Estimate tokens needed
        from app.core.llm.token_estimator import TokenEstimator
        estimator = TokenEstimator()
        estimated = estimator.estimate_prompt_tokens(
            prompt=prompt,
            model="glm-4-plus",
            max_tokens=4096
        )
        
        # Check budget availability
        budget_check = await budget_service.check_token_availability(
            scope_type="test",
            scope_id=test_id,
            requested_tokens=estimated["total_estimated_tokens"],
            db=db
        )
        
        if not budget_check.get("available", True):
            raise Exception(f"Budget exceeded: {budget_check}")
        
        # Check quota availability
        quota_check = await quota_service.check_quota_availability(
            user_id=user_id,
            requested_tokens=estimated["total_estimated_tokens"],
            db=db
        )
        
        if not quota_check.get("available", True):
            raise Exception(f"Quota exceeded: {quota_check}")
        
        # Make LLM call
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        
        # Get actual token usage
        tokens_used = response.usage_metadata.get("total_tokens", 0)
        
        # Record usage
        await budget_service.record_token_usage(
            scope_type="test",
            scope_id=test_id,
            tokens_used=tokens_used,
            db=db,
            metadata={"test_id": test_id, "model": "glm-4-plus"}
        )
        
        await quota_service.record_quota_usage(
            user_id=user_id,
            tokens_used=tokens_used,
            db=db,
            metadata={"test_id": test_id, "model": "glm-4-plus"}
        )
        
        return response
        
    finally:
        await db.close()
```

### Error Handling

Implement comprehensive error handling:

```python
from app.core.exceptions.token_exceptions import (
    TokenBudgetExceeded,
    TokenQuotaExceeded
)

async def handle_llm_call_with_token_management(
    prompt: str,
    scope_type: str,
    scope_id: int,
    user_id: int
):
    """Handle LLM call with comprehensive error handling."""
    
    try:
        # Attempt LLM call with token management
        result = await generate_test_with_token_check(
            prompt, scope_id, user_id
        )
        return result
        
    except TokenBudgetExceeded as e:
        # Handle budget exceeded
        logger.warning(f"Budget exceeded: {e.message}")
        
        # Send notification
        await notify_user(
            user_id=user_id,
            message=f"Token budget exceeded: {e.scope_type}:{e.scope_id}",
            severity="error"
        )
        
        # Return error response
        return {
            "error": "token_budget_exceeded",
            "message": e.message,
            "available_tokens": e.available_tokens,
            "requested_tokens": e.requested_tokens
        }
        
    except TokenQuotaExceeded as e:
        # Handle quota exceeded
        logger.warning(f"Quota exceeded: {e.message}")
        
        # Send notification
        await notify_user(
            user_id=user_id,
            message=f"Token quota exceeded for user {e.user_id}",
            severity="error"
        )
        
        # Return error response
        return {
            "error": "token_quota_exceeded",
            "message": e.message,
            "available_tokens": e.available_tokens,
            "requested_tokens": e.requested_tokens
        }
        
    except Exception as e:
        # Handle other errors
        logger.error(f"Unexpected error: {e}")
        raise
```

## Decorator Integration

### Basic Decorator Usage

Apply decorators for automatic token management:

```python
from app.core.decorators.token_decorators import enforce_token_limits

@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id",
    prompt_param="prompt",
    enforcement_mode="soft"
)
async def generate_test_script(
    prompt: str,
    scope_type: str,
    scope_id: int,
    user_id: int,
    **kwargs
):
    """Generate test script with automatic token management."""
    
    # Get LLM client
    from app.core.agent_config import get_llm
    llm = get_llm()
    
    # Make LLM call
    response = await llm.ainvoke(prompt)
    
    # Return response with token usage
    return {
        "script": response.content,
        "tokens_used": response.usage_metadata.get("total_tokens", 0)
    }
```

### Decorator Parameters

```python
@enforce_token_limits(
    # Parameter mapping
    scope_type_param="scope_type",      # Function parameter for scope
    scope_id_param="scope_id",          # Function parameter for scope ID
    user_id_param="user_id",            # Function parameter for user ID
    prompt_param="prompt",              # Function parameter for prompt
    model_param="model",                # Function parameter for model
    max_tokens_param="max_tokens",      # Function parameter for max tokens
    
    # Enforcement settings
    enforcement_mode="soft",             # soft, hard, monitoring
    on_exceeded="raise"                 # raise, return, warn
)
async def my_llm_function(...):
    pass
```

### Enforcement Modes

**Soft Mode (Warning Only)**

```python
@enforce_token_limits(
    enforcement_mode="soft",
    on_exceeded="warn"  # Log warning but allow execution
)
async def generate_with_soft_limit(...):
    # Will execute even if exceeded, with warning logged
    pass
```

**Hard Mode (Block on Exceed)**

```python
@enforce_token_limits(
    enforcement_mode="hard",
    on_exceeded="raise"  # Raise exception if exceeded
)
async def generate_with_hard_limit(...):
    # Will raise TokenBudgetExceeded if exceeded
    pass
```

**Monitoring Mode (Track Only)**

```python
@enforce_token_limits(
    enforcement_mode="monitoring",  # No enforcement, just track
    on_exceeded="warn"
)
async def generate_with_monitoring(...):
    # Always executes, usage tracked for analytics
    pass
```

### Individual Decorators

Use decorators separately for more control:

```python
from app.core.decorators.token_decorators import (
    check_token_budget,
    track_token_usage
)

@check_token_budget(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    prompt_param="prompt",
    enforcement_mode="hard"
)
@track_token_usage(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id"
)
async def generate_with_separate_checks(...):
    # Pre-check: Budget availability checked
    # Execution: Function runs
    # Post-track: Usage recorded
    pass
```

## LLM Client Integration

### LangChain Integration

Integrate with LangChain LLM calls:

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from app.core.decorators.token_decorators import enforce_token_limits

@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id",
    prompt_param="prompt_text"
)
async def generate_with_langchain(
    prompt_text: str,
    scope_type: str,
    scope_id: int,
    user_id: int
):
    """Generate using LangChain with token management."""
    
    # Get LLM
    from app.core.agent_config import get_llm
    llm = get_llm()
    
    # Create chain
    prompt = PromptTemplate(
        template="Generate test: {prompt_text}",
        input_variables=["prompt_text"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Execute
    result = await chain.aprompt(prompt_text=prompt_text)
    
    # Return with token usage
    return {
        "result": result["text"],
        "tokens_used": llm.get_num_tokens(result["text"])
    }
```

### OpenAI-Compatible Integration

Use with OpenAI-compatible APIs:

```python
from openai import AsyncOpenAI
from app.core.decorators.token_decorators import enforce_token_limits

@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id",
    prompt_param="prompt"
)
async def generate_with_openai_client(
    prompt: str,
    scope_type: str,
    scope_id: int,
    user_id: int
):
    """Generate using OpenAI client with token management."""
    
    # Get LLM configuration
    from app.core.agent_config import get_llm
    llm = get_llm()
    
    # Create client
    client = AsyncOpenAI(
        api_key=llm.api_key,
        base_url=llm.base_url
    )
    
    # Make call
    response = await client.chat.completions.create(
        model=llm.model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096
    )
    
    # Return with token usage
    return {
        "result": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens
    }
```

### Custom LLM Integration

Integrate with custom LLM implementations:

```python
class CustomLLMClient:
    """Custom LLM client with token tracking."""
    
    def __init__(self):
        from app.core.agent_config import get_llm
        self.base_llm = get_llm()
    
    async def generate(
        self,
        prompt: str,
        scope_type: str,
        scope_id: int,
        user_id: int
    ):
        """Generate with token management."""
        
        # Get database session
        from app.core.database import get_db
        db = await get_db().__aenter__()
        
        try:
            # Initialize services
            from app.services.token_budget_service import TokenBudgetService
            budget_service = TokenBudgetService()
            
            # Estimate tokens
            from app.core.llm.token_estimator import TokenEstimator
            estimator = TokenEstimator()
            estimated = estimator.estimate_prompt_tokens(
                prompt=prompt,
                model=self.base_llm.model_name,
                max_tokens=4096
            )
            
            # Check availability
            available = await budget_service.check_token_availability(
                scope_type=scope_type,
                scope_id=scope_id,
                requested_tokens=estimated["total_estimated_tokens"],
                db=db
            )
            
            if not available.get("available", True):
                raise Exception("Token budget exceeded")
            
            # Make LLM call
            response = await self.base_llm.ainvoke(prompt)
            
            # Record usage
            tokens_used = response.usage_metadata.get("total_tokens", 0)
            await budget_service.record_token_usage(
                scope_type=scope_type,
                scope_id=scope_id,
                tokens_used=tokens_used,
                db=db,
                metadata={"custom_client": True}
            )
            
            return response
            
        finally:
            await db.close()
```

## Testing Strategies

### Unit Testing

Test token management in isolation:

```python
import pytest
from app.services.token_budget_service import TokenBudgetService
from app.core.database import get_db

@pytest.mark.asyncio
async def test_budget_check():
    """Test budget availability checking."""
    
    # Setup
    db = await get_db().__aenter__()
    service = TokenBudgetService()
    
    try:
        # Test available budget
        result = await service.check_token_availability(
            scope_type="test",
            scope_id=1,
            requested_tokens=1000,
            db=db
        )
        
        assert result.get("available", True) == True
        assert result.get("available_tokens", 0) > 1000
        
        # Test exceeded budget
        result = await service.check_token_availability(
            scope_type="test",
            scope_id=1,
            requested_tokens=10000000,  # Excessive request
            db=db
        )
        
        assert result.get("available", True) == False
        
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_usage_recording():
    """Test token usage recording."""
    
    # Setup
    db = await get_db().__aenter__()
    service = TokenBudgetService()
    
    try:
        # Record usage
        await service.record_token_usage(
            scope_type="test",
            scope_id=1,
            tokens_used=5000,
            db=db,
            metadata={"test": "unit_test"}
        )
        
        # Verify recording
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()
        budget = await budget_repo.get_by_scope("test", 1, db)
        
        assert budget.used_tokens >= 5000
        
    finally:
        await db.close()
```

### Integration Testing

Test full workflow integration:

```python
@pytest.mark.asyncio
async def test_llm_call_with_token_management():
    """Test complete LLM call with token management."""
    
    # Setup
    from app.core.decorators.token_decorators import enforce_token_limits
    from app.core.database import get_db
    
    db = await get_db().__aenter__()
    
    try:
        # Create test function with decorator
        @enforce_token_limits(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id",
            prompt_param="prompt"
        )
        async def test_llm_function(
            prompt: str,
            scope_type: str,
            scope_id: int,
            user_id: int,
            db: AsyncSession
        ):
            # Mock LLM call
            return {
                "result": "test response",
                "tokens_used": 1000
            }
        
        # Execute with parameters
        result = await test_llm_function(
            prompt="test prompt",
            scope_type="test",
            scope_id=1,
            user_id=1,
            db=db
        )
        
        # Verify result
        assert result["result"] == "test response"
        assert result["tokens_used"] == 1000
        
        # Verify usage was recorded
        from app.repositories.repository_factory import RepositoryFactory
        budget_repo = RepositoryFactory.get_token_budget_repository()
        budget = await budget_repo.get_by_scope("test", 1, db)
        
        assert budget.used_tokens >= 1000
        
    finally:
        await db.close()
```

### Mock Testing

Mock services for testing without database:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_token_check_with_mock():
    """Test token checking with mocked services."""
    
    # Mock services
    budget_service = AsyncMock()
    budget_service.check_token_availability.return_value = {
        "available": True,
        "available_tokens": 10000
    }
    
    quota_service = AsyncMock()
    quota_service.check_quota_availability.return_value = {
        "available": True,
        "available_tokens": 5000
    }
    
    # Test with mocked services
    with patch('app.services.token_budget_service.TokenBudgetService', return_value=budget_service):
        with patch('app.services.token_quota_service.TokenQuotaService', return_value=quota_service):
            result = await budget_service.check_token_availability(
                scope_type="test",
                scope_id=1,
                requested_tokens=1000,
                db=AsyncMock()
            )
            
            assert result["available"] == True
            budget_service.check_token_availability.assert_called_once()
```

### Load Testing

Test token management under load:

```python
import asyncio
from app.core.decorators.token_decorators import enforce_token_limits

async def test_concurrent_requests():
    """Test token management with concurrent requests."""
    
    @enforce_token_limits(
        scope_type_param="scope_type",
        scope_id_param="scope_id",
        user_id_param="user_id",
        prompt_param="prompt"
    )
    async def llm_function(prompt: str, scope_type: str, scope_id: int, user_id: int, db: AsyncSession):
        await asyncio.sleep(0.1)  # Simulate LLM call
        return {"tokens_used": 1000}
    
    # Create concurrent requests
    tasks = []
    for i in range(10):
        task = llm_function(
            prompt=f"test {i}",
            scope_type="test",
            scope_id=1,
            user_id=1,
            db=await get_db().__aenter__()
        )
        tasks.append(task)
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify all succeeded
    assert len(results) == 10
    assert all(isinstance(r, dict) for r in results)
```

## Extension Points

### Custom Alert Handlers

Create custom alert handlers:

```python
from app.services.token_alert_service import TokenAlertService

class CustomAlertHandler:
    """Custom alert handler for specific notifications."""
    
    def __init__(self, config: dict):
        self.config = config
        self.alert_service = TokenAlertService()
    
    async def handle_alert(self, alert: TokenAlert):
        """Handle alert with custom logic."""
        
        # Send to custom webhook
        if alert.severity in ["critical", "emergency"]:
            await self.send_to_webhook(alert)
        
        # Send to Slack
        if self.config.get("slack_enabled"):
            await self.send_to_slack(alert)
        
        # Send to PagerDuty
        if alert.severity == "emergency":
            await self.send_to_pagerduty(alert)
    
    async def send_to_webhook(self, alert: TokenAlert):
        """Send alert to custom webhook."""
        
        import aiohttp
        
        payload = {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.created_at.isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.config["webhook_url"],
                json=payload
            )
    
    async def send_to_slack(self, alert: TokenAlert):
        """Send alert to Slack."""
        
        from slack_sdk.web.async_client import AsyncWebClient
        
        client = AsyncWebClient(token=self.config["slack_token"])
        
        await client.chat_postMessage(
            channel=self.config["slack_channel"],
            text=f"⚠️ Token Alert: {alert.message}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.severity.upper()}*: {alert.message}"
                    }
                }
            ]
        )
```

### Custom Enforcement Strategies

Implement custom enforcement logic:

```python
class CustomEnforcementStrategy:
    """Custom enforcement strategy for specific business rules."""
    
    async def check_availability(
        self,
        scope_type: str,
        scope_id: int,
        requested_tokens: int,
        db: AsyncSession
    ) -> dict:
        """Check availability with custom logic."""
        
        # Get standard budget check
        from app.services.token_budget_service import TokenBudgetService
        budget_service = TokenBudgetService()
        
        standard_check = await budget_service.check_token_availability(
            scope_type=scope_type,
            scope_id=scope_id,
            requested_tokens=requested_tokens,
            db=db
        )
        
        # Add custom rules
        if scope_type == "test":
            # Allow burst usage for critical tests
            test = await self.get_test(scope_id, db)
            if test.priority == "critical":
                return {
                    **standard_check,
                    "available": True,
                    "override_reason": "critical_test"
                }
        
        return standard_check
    
    async def record_usage(
        self,
        scope_type: str,
        scope_id: int,
        tokens_used: int,
        db: AsyncSession
    ):
        """Record usage with custom tracking."""
        
        # Standard recording
        from app.services.token_budget_service import TokenBudgetService
        budget_service = TokenBudgetService()
        
        await budget_service.record_token_usage(
            scope_type=scope_type,
            scope_id=scope_id,
            tokens_used=tokens_used,
            db=db
        )
        
        # Custom tracking
        await self.track_to_custom_system(
            scope_type=scope_type,
            scope_id=scope_id,
            tokens_used=tokens_used
        )
```

### Custom Analytics

Implement custom analytics:

```python
class CustomAnalytics:
    """Custom analytics for token usage patterns."""
    
    async def get_cost_efficiency(
        self,
        budget_id: int,
        db: AsyncSession
    ) -> dict:
        """Calculate cost efficiency metrics."""
        
        from app.services.token_budget_service import TokenBudgetService
        budget_service = TokenBudgetService()
        
        # Get budget status
        status = await budget_service.get_budget_status(budget_id, db)
        
        # Calculate efficiency
        total_tests = await self.get_total_tests_for_budget(budget_id, db)
        passed_tests = await self.get_passed_tests_for_budget(budget_id, db)
        
        efficiency = {
            "budget_id": budget_id,
            "tests_per_token": total_tests / status.get("used_tokens", 1),
            "passed_tests_per_token": passed_tests / status.get("used_tokens", 1),
            "cost_per_test": status.get("used_tokens", 0) / total_tests if total_tests > 0 else 0,
            "efficiency_score": self.calculate_efficiency_score(
                total_tests, passed_tests, status.get("used_tokens", 0)
            )
        }
        
        return efficiency
    
    def calculate_efficiency_score(
        self,
        total_tests: int,
        passed_tests: int,
        tokens_used: int
    ) -> float:
        """Calculate overall efficiency score."""
        
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        token_efficiency = min(1.0, 1000 / tokens_used)  # 1000 tokens per test is baseline
        
        return (pass_rate * 0.7 + token_efficiency * 0.3) * 100
```

## Code Examples

### Complete Workflow Example

```python
from app.core.decorators.token_decorators import enforce_token_limits
from app.core.database import get_db
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.core.agent_config import get_llm

async def complete_test_generation_workflow(
    test_definition_id: int,
    user_id: int
):
    """Complete workflow for generating tests with token management."""
    
    db = await get_db().__aenter__()
    
    try:
        # Step 1: Check availability
        budget_service = TokenBudgetService()
        quota_service = TokenQuotaService()
        
        budget_check = await budget_service.check_token_availability(
            scope_type="test",
            scope_id=test_definition_id,
            requested_tokens=50000,  # Estimated
            db=db
        )
        
        if not budget_check.get("available", True):
            return {
                "error": "budget_exceeded",
                "details": budget_check
            }
        
        # Step 2: Generate test plan
        @enforce_token_limits(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id",
            prompt_param="prompt"
        )
        async def generate_plan(
            prompt: str,
            scope_type: str,
            scope_id: int,
            user_id: int,
            db: AsyncSession
        ):
            llm = get_llm()
            response = await llm.ainvoke(prompt)
            
            return {
                "plan": response.content,
                "tokens_used": response.usage_metadata.get("total_tokens", 0)
            }
        
        plan_result = await generate_plan(
            prompt=f"Generate test plan for test {test_definition_id}",
            scope_type="test",
            scope_id=test_definition_id,
            user_id=user_id,
            db=db
        )
        
        # Step 3: Generate test script
        script_result = await generate_plan(
            prompt=f"Generate test script for plan: {plan_result['plan']}",
            scope_type="test",
            scope_id=test_definition_id,
            user_id=user_id,
            db=db
        )
        
        # Step 4: Check final status
        final_status = await budget_service.get_budget_status(
            budget_id=budget_check.get("budget_id"),
            db=db
        )
        
        return {
            "plan": plan_result["plan"],
            "script": script_result["script"],
            "total_tokens": plan_result["tokens_used"] + script_result["tokens_used"],
            "budget_status": final_status
        }
        
    finally:
        await db.close()
```

### Batch Processing Example

```python
async def batch_generate_tests(
    test_ids: list[int],
    user_id: int,
    batch_size: int = 5
):
    """Generate multiple tests in batches with token management."""
    
    from app.core.decorators.token_decorators import enforce_token_limits
    
    @enforce_token_limits(
        scope_type_param="scope_type",
        scope_id_param="scope_id",
        user_id_param="user_id",
        prompt_param="prompt"
    )
    async def generate_single_test(
        prompt: str,
        scope_type: str,
        scope_id: int,
        user_id: int,
        db: AsyncSession
    ):
        # Generate single test
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        
        return {
            "test_id": scope_id,
            "result": response.content,
            "tokens_used": response.usage_metadata.get("total_tokens", 0)
        }
    
    # Process in batches
    results = []
    total_tokens = 0
    
    for i in range(0, len(test_ids), batch_size):
        batch = test_ids[i:i + batch_size]
        
        # Get database session
        db = await get_db().__aenter__()
        
        try:
            # Generate batch
            batch_tasks = []
            for test_id in batch:
                task = generate_single_test(
                    prompt=f"Generate test for {test_id}",
                    scope_type="test",
                    scope_id=test_id,
                    user_id=user_id,
                    db=db
                )
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
                    total_tokens += result.get("tokens_used", 0)
                else:
                    results.append({
                        "error": "generation_failed",
                        "details": str(result)
                    })
        
        finally:
            await db.close()
    
    return {
        "results": results,
        "total_tests": len(results),
        "successful_tests": len([r for r in results if "error" not in r]),
        "total_tokens": total_tokens
    }
```

## Performance Optimization

### Caching Strategies

Implement caching for frequently accessed data:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedTokenService:
    """Token service with caching for improved performance."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_budget_status_cached(
        self,
        budget_id: int,
        db: AsyncSession
    ) -> dict:
        """Get budget status with caching."""
        
        # Check cache
        cache_key = f"budget_status_{budget_id}"
        cached = self.cache.get(cache_key)
        
        if cached:
            cache_time = cached.get("timestamp")
            if datetime.utcnow() - cache_time < timedelta(seconds=self.cache_ttl):
                return cached.get("data")
        
        # Get fresh data
        from app.services.token_budget_service import TokenBudgetService
        service = TokenBudgetService()
        
        data = await service.get_budget_status(budget_id, db)
        
        # Update cache
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.utcnow()
        }
        
        return data
    
    def clear_cache(self):
        """Clear cache."""
        self.cache.clear()
```

### Batch Operations

Use batch operations for efficiency:

```python
async def batch_record_usage(
    usage_records: list[dict],
    db: AsyncSession
):
    """Record multiple usage records in batch."""
    
    from app.models.token_budget import TokenBudget
    
    # Batch update budgets
    budget_updates = {}
    for record in usage_records:
        key = (record["scope_type"], record["scope_id"])
        if key not in budget_updates:
            budget_updates[key] = 0
        budget_updates[key] += record["tokens_used"]
    
    # Apply updates
    for (scope_type, scope_id), tokens in budget_updates.items():
        budget = await db.execute(
            select(TokenBudget)
            .where(TokenBudget.scope_type == scope_type)
            .where(TokenBudget.scope_id == scope_id)
        )
        budget = budget.scalar_one_or_none()
        
        if budget:
            budget.update_usage(tokens)
    
    await db.commit()
```

### Async Optimization

Use async operations for parallel processing:

```python
async def parallel_token_checks(
    requests: list[dict],
    db: AsyncSession
):
    """Check multiple token requests in parallel."""
    
    from app.services.token_budget_service import TokenBudgetService
    
    service = TokenBudgetService()
    
    # Create tasks
    tasks = []
    for request in requests:
        task = service.check_token_availability(
            scope_type=request["scope_type"],
            scope_id=request["scope_id"],
            requested_tokens=request["requested_tokens"],
            db=db
        )
        tasks.append(task)
    
    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [
        result if isinstance(result, dict) else {"error": str(result)}
        for result in results
    ]
```

---

**Next:** See [Deployment Guide](TOKEN_LIMITATION_DEPLOYMENT.md) for installation and setup instructions.