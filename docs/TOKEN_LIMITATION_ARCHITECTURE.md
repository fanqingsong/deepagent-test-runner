# Token Limitation System Architecture

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Principles](#design-principles)
3. [Architecture Diagrams](#architecture-diagrams)
4. [Component Interactions](#component-interactions)
5. [Data Flows](#data-flows)
6. [Integration Points](#integration-points)
7. [Security Considerations](#security-considerations)
8. [Performance Considerations](#performance-considerations)

## System Overview

The Token Limitation System is a comprehensive framework for managing and controlling LLM token usage across the DeepAgent Test Runner platform. It provides hierarchical budget management, user-specific quotas, automated alerting, and enforcement mechanisms to optimize costs and ensure fair resource allocation.

### Core Objectives

- **Cost Control**: Monitor and limit LLM API costs through budget enforcement
- **Resource Allocation**: Ensure fair distribution of tokens across users and projects
- **Operational Visibility**: Provide real-time insights into token consumption patterns
- **Automated Management**: Reduce manual oversight through intelligent alerts and enforcement
- **Scalable Architecture**: Support growth from small teams to enterprise deployments

### Key Capabilities

1. **Hierarchical Budget Structure**: Organization → Suite → Test → User levels
2. **User-Specific Quotas**: Time-based limits with flexible reset strategies
3. **Intelligent Alerting**: Threshold-based notifications with multiple severity levels
4. **Multi-Mode Enforcement**: Soft warnings, hard blocks, and monitoring-only modes
5. **Comprehensive Analytics**: Usage trends, forecasting, and performance metrics
6. **Decorator-Based Integration**: Minimal code changes for automatic token tracking

### Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL with JSONB for flexible configuration storage
- **ORM**: SQLAlchemy 2.0 with async support
- **Frontend**: React with TypeScript
- **Monitoring**: Langfuse integration for detailed LLM tracking

## Design Principles

### SOLID Principles Implementation

#### Single Responsibility Principle (SRP)

Each component has a clearly defined, focused responsibility:

- **TokenBudgetService**: Budget operations only (checking, recording, status)
- **TokenQuotaService**: User quota management only
- **TokenAlertService**: Alert generation and notification only
- **TokenReportingService**: Analytics and reporting only
- **Repositories**: Data access and persistence only

```python
# Good: Service handles only budget operations
class TokenBudgetService:
    async def check_token_availability(...)  # Budget checking
    async def record_token_usage(...)          # Usage recording
    async def get_budget_status(...)           # Status reporting
```

#### Open/Closed Principle (OCP)

The system is extensible through configuration and interfaces, not code modification:

- **Strategies**: Reset strategies, enforcement modes, alert thresholds
- **Interfaces**: Repository interfaces for multiple implementations
- **JSONB Configuration**: Extensible configuration without schema changes
- **Decorator Patterns**: Composable token management behaviors

```python
# Extensible through strategy pattern
class TokenBudget:
    period_type: str  # "daily", "weekly", "monthly", "custom"
    enforcement_mode: str  # "soft", "hard", "monitoring"
    alert_thresholds: dict  # Customizable thresholds
```

#### Liskov Substitution Principle (LSP)

All service implementations can be substituted without breaking the application:

- **Repository Interfaces**: `ITokenBudgetRepository`, `ITokenQuotaRepository`
- **Service Contracts**: Consistent return types via `Result` objects
- **Error Handling**: Standardized error responses across all services

```python
# All repositories implement the same interface
class ITokenBudgetRepository(ABC):
    @abstractmethod
    async def get_by_id(self, budget_id: int, db: AsyncSession): pass
    @abstractmethod
    async def get_by_scope(self, scope_type: str, scope_id: int, db: AsyncSession): pass
```

#### Interface Segregation Principle (ISP)

Clients depend only on interfaces they use:

- **Focused Interfaces**: Separate interfaces for budgets, quotas, alerts
- **Minimal Dependencies**: Services only depend on what they need
- **Optional Dependencies**: Metrics collector, notification services

```python
# Focused, minimal interfaces
class ITokenBudgetRepository(ABC):
    # Only budget-related methods
    async def get_by_id(...)
    async def get_by_scope(...)

class ITokenAlertRepository(ABC):
    # Only alert-related methods
    async def create(...)
    async def acknowledge(...)
```

#### Dependency Inversion Principle (DIP)

High-level modules depend on abstractions, not concrete implementations:

- **Repository Factory**: Abstract factory pattern for repository creation
- **Service Dependencies**: Inject repository interfaces, not concrete classes
- **Configuration Injection**: All configuration externalized

```python
# Dependencies on abstractions
class TokenBudgetService:
    def __init__(
        self,
        budget_repository: ITokenBudgetRepository  # Interface, not concrete
    ):
        self.budget_repository = budget_repository
```

### Additional Design Principles

#### Separation of Concerns

- **API Layer**: HTTP handling and validation only
- **Service Layer**: Business logic only
- **Repository Layer**: Data access only
- **Model Layer**: Data representation only

#### DRY (Don't Repeat Yourself)

- **Shared Utilities**: Token estimation, result helpers
- **Base Functionality**: Common model properties and methods
- **Reusable Decorators**: `@check_token_budget`, `@track_token_usage`

#### KISS (Keep It Simple, Stupid)

- **Straightforward APIs**: Intuitive endpoint design
- **Clear Naming**: Descriptive variable and function names
- **Minimal Complexity**: Avoid over-engineering

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│  React Components (Budget Management, Analytics, Alerts)        │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP/REST API
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Budget APIs  │  │ Quota APIs   │  │ Alert APIs   │           │
│  │ (37 endpoints)│  │              │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Business Logic
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Budget Service   │  │ Quota Service    │  │ Alert Service │ │
│  │ - Check           │  │ - Record         │  │ - Generate    │ │
│  │ - Record          │  │ - Reset          │  │ - Notify      │ │
│  │ - Forecast        │  │ - Status         │  │ - Acknowledge │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Reporting Service                              │  │
│  │ - Analytics - Trends - Forecasts - Comparisons             │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Data Access
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Repository Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Budget Repo      │  │ Quota Repo       │  │ Alert Repo    │ │
│  │ - CRUD            │  │ - CRUD           │  │ - Create      │ │
│  │ - Scope queries   │  │ - User queries   │  │ - Acknowledge │ │
│  │ - Hierarchy       │  │ - Reset          │  │ - History     │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└───────────────────────┬─────────────────────────────────────────┘
                        │ SQL Queries
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ token_budgets│  │ token_quotas │  │ token_alerts │           │
│  │              │  │              │  │              │           │
│  │ - Hierarchical│  │ - User-based│  │ - Threshold  │           │
│  │ - Multi-level│  │ - Time-based│  │ - Notification│          │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Budget Hierarchy Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Organization Budget                          │
│  - Total: 10,000,000 tokens/month                             │
│  - Priority: 10 (Highest)                                     │
│  - Scope: organization:1                                      │
│  └─────────────────────────────────────────────────────────┐
│      │                                                        │
│      ├──────────────────────┬──────────────────────┐        │
│      ▼                      ▼                      ▼        │
│ ┌─────────────┐      ┌─────────────┐      ┌─────────────┐   │
│ │ Suite Budget│      │ Suite Budget│      │ Suite Budget│   │
│ │ Test Suite 1│      │ Test Suite 2│      │ Test Suite 3│   │
│ │ Total: 1M   │      │ Total: 2M   │      │ Total: 5M   │   │
│ └──────┬──────┘      └──────┬──────┘      └──────┬──────┘   │
│        │                    │                    │          │
│        ▼                    ▼                    ▼          │
│ ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐  │
│ │  Test Budgets    │  │  Test Budgets    │  │  Test     │  │
│ │  - Test 1: 100K  │  │  - Test 1: 200K │  │  Budgets  │  │
│ │  - Test 2: 200K  │  │  - Test 2: 300K │  │           │  │
│ └──────────────────┘  └──────────────────┘  └───────────┘  │
│        │                    │                              │
│        ▼                    ▼                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │           User Quotas (Per-User Limits)                │ │
│ │  - User A: 50K/day, 350K/week                           │ │
│ │  - User B: 30K/day, 210K/week                           │ │
│ └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
┌─────────────┐
│   LLM Call  │
└──────┬──────┘
       │ Request
       ▼
┌──────────────────────────────────────────────────────────┐
│          @enforce_token_limits Decorator                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. @check_token_budget (Pre-call)               │    │
│  │     - Estimate tokens needed                      │    │
│  │     - Check budget availability                   │    │
│  │     - Check quota availability                    │    │
│  │     - Enforce limits if exceeded                  │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  2. Execute Function                             │    │
│  │     - Make LLM API call                          │    │
│  │     - Get actual token usage                     │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  3. @track_token_usage (Post-call)               │    │
│  │     - Record budget usage                        │    │
│  │     - Record quota usage                         │    │
│  │     - Check thresholds                           │    │
│  │     - Generate alerts if needed                  │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   Service Layer                           │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ Budget Service   │  │ Quota Service    │             │
│  │ - Check           │  │ - Check           │             │
│  │ - Record          │  │ - Record          │             │
│  │ - Update Status    │  │ - Update Status    │             │
│  └──────────────────┘  └──────────────────┘             │
│  ┌─────────────────────────────────────────────────┐    │
│  │        Alert Service                              │    │
│  │ - Check thresholds                               │    │
│  │ - Create alert records                           │    │
│  │ - Trigger notifications                          │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│                  Repository Layer                          │
│  - Update budget usage                                     │
│  - Update quota usage                                      │
│  - Create alert records                                    │
│  - Update alert status                                     │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│                    Database                                │
│  - UPDATE token_budgets SET used_tokens = used_tokens + X │
│  - UPDATE token_quotas SET used_tokens = used_tokens + X  │
│  - INSERT INTO token_alerts (...)                          │
└──────────────────────────────────────────────────────────┘
```

### Alert Generation Flow

```
┌──────────────────────────────────────────────────────────┐
│              Token Usage Recorded                          │
│  - Budget usage: 850,000 / 1,000,000 (85%)                │
│  - Quota usage: 42,000 / 50,000 (84%)                     │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│           Threshold Check (Automatic)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Budget Thresholds:                               │   │
│  │  - Warning: 80%  ✓ (85% ≥ 80%)                   │   │
│  │  - Critical: 90%  ✗ (85% < 90%)                  │   │
│  │  - Emergency: 95% ✗ (85% < 95%)                  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Quota Thresholds:                                │   │
│  │  - Warning: 80%  ✓ (84% ≥ 80%)                   │   │
│  │  - Critical: 90%  ✗ (84% < 90%)                  │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────────┘
                        │ Thresholds Exceeded
                        ▼
┌──────────────────────────────────────────────────────────┐
│              Alert Service                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Create Alert Records                             │   │
│  │  - alert_type: "budget_warning"                  │   │
│  │  - alert_type: "quota_warning"                   │   │
│  │  - severity: "warning"                           │   │
│  │  - threshold_value: 80.0                          │   │
│  │  - current_value: 85.0                           │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│            Notification Service                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Send Notifications                                │   │
│  │  - Email: admin@company.com                        │   │
│  │  - Webhook: https://hooks.company.com/alerts       │   │
│  │  - In-App: User notification center               │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Track Delivery Status                            │   │
│  │  - notifications_sent: {"email": true}           │   │
│  │  - notification_errors: {}                        │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Component Interactions

### API → Service → Repository Flow

```python
# API Layer (HTTP Handler)
@router.post("/{budget_id}/check-availability")
async def check_token_availability(
    budget_id: int,
    requested_tokens: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # API Layer: Request validation and authentication
    service = TokenBudgetService()
    budget = await budget_repo.get_by_id(budget_id, db)
    
    result = await service.check_token_availability(
        budget.scope_type,
        budget.scope_id,
        requested_tokens,
        db
    )
    
    # API Layer: Response formatting
    return get_data(result)

# Service Layer (Business Logic)
class TokenBudgetService:
    async def check_token_availability(
        self,
        scope_type: str,
        scope_id: int,
        requested_tokens: int,
        db: AsyncSession
    ):
        # Service Layer: Business logic
        budget = await self.budget_repository.get_by_scope(
            scope_type, scope_id, db
        )
        
        # Business rules
        available = budget.remaining_tokens >= requested_tokens
        enforcement = self._determine_enforcement(budget, available)
        
        return service_success({
            "available": available,
            "enforcement_action": enforcement
        })

# Repository Layer (Data Access)
class TokenBudgetRepository:
    async def get_by_scope(
        self,
        scope_type: str,
        scope_id: int,
        db: AsyncSession
    ):
        # Repository Layer: Database queries
        result = await db.execute(
            select(TokenBudget)
            .where(TokenBudget.scope_type == scope_type)
            .where(TokenBudget.scope_id == scope_id)
        )
        return result.scalar_one_or_none()
```

### Decorator Integration Flow

```python
# 1. Apply Decorator to LLM Function
@enforce_token_limits(
    scope_type_param="scope_type",
    scope_id_param="scope_id",
    user_id_param="user_id",
    enforcement_mode="soft"
)
async def generate_test_plan(
    prompt: str,
    scope_type: str,
    scope_id: int,
    user_id: int,
    **kwargs
):
    # Make LLM call
    response = await llm_client.generate(prompt)
    return response

# 2. Decorator Chain Execution
# @check_token_budget (Pre-call)
async def check_wrapper(*args, **kwargs):
    # Extract parameters
    scope_type = kwargs.get("scope_type")
    scope_id = kwargs.get("scope_id")
    prompt = kwargs.get("prompt")
    
    # Estimate tokens
    estimator = TokenEstimator()
    estimated = estimator.estimate_prompt_tokens(prompt, model)
    
    # Check availability
    result = await budget_service.check_token_availability(
        scope_type, scope_id, estimated["total"], db
    )
    
    # Enforce if exceeded
    if not result["available"]:
        if enforcement_mode == "hard":
            raise TokenBudgetExceeded(...)
    
    # Execute original function
    return await func(*args, **kwargs)

# @track_token_usage (Post-call)
async def track_wrapper(*args, **kwargs):
    # Execute function (including pre-call check)
    result = await check_wrapper(*args, **kwargs)
    
    # Extract token usage from result
    tokens_used = result.get("tokens_used")
    
    # Record usage
    await budget_service.record_token_usage(
        scope_type, scope_id, tokens_used, db
    )
    
    await quota_service.record_quota_usage(
        user_id, tokens_used, db
    )
    
    return result
```

### Alert Generation Interaction

```python
# Service Layer: Recording Usage
class TokenBudgetService:
    async def record_token_usage(
        self,
        scope_type: str,
        scope_id: int,
        tokens_used: int,
        db: AsyncSession,
        metadata: dict
    ):
        # Update budget usage
        budget = await self.budget_repository.get_by_scope(
            scope_type, scope_id, db
        )
        budget.update_usage(tokens_used)
        
        # Check thresholds
        triggered = budget.check_threshold_alerts()
        
        # Generate alerts for triggered thresholds
        for threshold in triggered:
            await self.alert_service.create_threshold_alert(
                budget=budget,
                threshold_type=threshold,
                current_usage=budget.usage_percentage,
                db=db
            )
        
        await self.budget_repository.update(budget.id, budget, db)

# Alert Service
class TokenAlertService:
    async def create_threshold_alert(
        self,
        budget: TokenBudget,
        threshold_type: str,
        current_usage: float,
        db: AsyncSession
    ):
        # Create alert record
        alert = TokenAlert(
            alert_type=f"budget_{threshold_type}",
            severity=threshold_type,
            budget_id=budget.id,
            user_id=self._get_user_id(budget),
            threshold_value=budget.alert_thresholds[threshold_type],
            current_value=current_usage,
            message=f"Budget {budget.name} exceeded {threshold_type} threshold",
            metrics_snapshot={
                "budget_id": budget.id,
                "budget_name": budget.name,
                "usage_percentage": current_usage,
                "total_tokens": budget.total_tokens,
                "used_tokens": budget.used_tokens
            }
        )
        
        await self.alert_repository.create(alert, db)
        
        # Send notifications
        await self._send_notifications(alert, db)
```

## Data Flows

### LLM Request Flow (Complete)

```
1. USER REQUEST
   └─> POST /api/v1/scripts/generate
       Body: {test_definition_id: 123, prompt: "Generate login test"}

2. API HANDLER
   └─> Validates request
       Gets current user
       Starts DB transaction

3. SERVICE LAYER
   └─> ScriptGenerationService.generate_script()
       └─> Calls Agent (LLM call)

4. DECORATOR: @check_token_budget (PRE-CALL)
   └─> Extracts scope_type="test", scope_id=123
       Estimates tokens: 15,000
       Checks budget availability
       └─> TokenBudgetService.check_token_availability()
           └─> TokenBudgetRepository.get_by_scope()
               └─> SQL: SELECT * FROM token_budgets 
                     WHERE scope_type='test' AND scope_id=123
       └─> Budget: 100,000 total, 20,000 used, 80,000 remaining
       └─> Available: True (15,000 < 80,000)
       └─> Enforcement: None (within limits)

5. LLM CALL EXECUTION
   └─> Agent.generate_response()
       └─> LLM API call (GLM-4 Plus)
       └─> Actual tokens used: 12,500

6. DECORATOR: @track_token_usage (POST-CALL)
   └─> Extracts tokens_used: 12,500
       Records budget usage
       └─> TokenBudgetService.record_token_usage()
           └─> Updates budget: 20,000 + 12,500 = 32,500
           └─> Checks thresholds
           └─> No alerts (32.5% < 80%)
       └─> Records quota usage
           └─> TokenQuotaService.record_quota_usage()
               └─> Updates quota: 10,000 + 12,500 = 22,500

7. DATABASE UPDATES
   └─> UPDATE token_budgets 
       SET used_tokens = 32500, remaining_tokens = 67500
       WHERE id = 456
   └─> UPDATE token_quotas
       SET used_tokens = 22500, remaining_tokens = 27500
       WHERE user_id = 789

8. RESPONSE
   └─> Returns generated script to user
```

### Alert Generation Flow (Complete)

```
1. USAGE UPDATE
   └─> Budget usage updated: 85,000 / 100,000 (85%)

2. THRESHOLD CHECK
   └─> budget.check_threshold_alerts()
       └─> triggered_alerts = ["warning"] (85% ≥ 80%)

3. ALERT CREATION
   └─> TokenAlertService.create_threshold_alert()
       └─> TokenAlert(
           alert_type: "budget_warning",
           severity: "warning",
           budget_id: 456,
           threshold_value: 80.0,
           current_value: 85.0,
           message: "Budget 'Test Suite 1' exceeded warning threshold",
           metrics_snapshot: {
               budget_name: "Test Suite 1",
               usage_percentage: 85.0,
               total_tokens: 100000,
               used_tokens: 85000
           }
       )

4. DATABASE INSERT
   └─> INSERT INTO token_alerts (...)
       VALUES (budget_warning, warning, 456, 80.0, 85.0, ...)

5. NOTIFICATION
   └─> NotificationService.send(alert)
       └─> Email: admin@company.com
           Subject: ⚠️ Budget Warning: Test Suite 1
           Body: Budget usage at 85% (warning threshold: 80%)
       └─> Webhook: POST https://hooks.company.com/alerts
           Body: {alert_type: "budget_warning", severity: "warning", ...}
       └─> In-App: User notification center
           Icon: ⚠️ Message: "Budget 'Test Suite 1' at 85% capacity"

6. DELIVERY TRACKING
   └─> UPDATE token_alerts
       SET notifications_sent = '{"email": true, "webhook": true}'
       WHERE id = 123

7. ACKNOWLEDGMENT
   └─> POST /api/v1/token/alerts/123/acknowledge
       └─> TokenAlert.acknowledge(user_id=789)
       └─> UPDATE token_alerts
           SET is_acknowledged = true,
               acknowledged_by = 789,
               acknowledged_at = NOW()
           WHERE id = 123
```

## Integration Points

### 1. LLM Integration

```python
# Core LLM Client Integration
from app.core.agent_config import get_llm
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
    # Get LLM client
    llm = get_llm()
    
    # Make LLM call
    response = await llm.ainvoke(prompt)
    
    # Return result with token usage
    return {
        "script": response.content,
        "tokens_used": response.usage_metadata.get("total_tokens", 0)
    }
```

### 2. Database Integration

```python
# Database Connection Factory
from app.core.database import get_db

# API Endpoint Integration
@router.post("/budgets")
async def create_budget(
    budget_data: TokenBudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  # DB session injection
):
    service = TokenBudgetService()
    result = await service.create_budget(budget_data, db)
    return result

# Repository Integration
class TokenBudgetRepository:
    async def create(self, data: dict, db: AsyncSession):
        budget = TokenBudget(**data)
        db.add(budget)
        await db.commit()
        await db.refresh(budget)
        return budget
```

### 3. Frontend Integration

```typescript
// React Component Integration
import { useTokenBudget } from '@/hooks/useTokenBudget';

function BudgetManager() {
    const { data: budget, refetch } = useTokenBudget(budgetId);
    
    const handleCheckAvailability = async (tokens: number) => {
        const result = await fetch(
            `/api/v1/token/budgets/${budgetId}/check-availability?requested_tokens=${tokens}`
        );
        return result.json();
    };
    
    return (
        <div>
            <h2>Budget Status</h2>
            <p>Usage: {budget.usage_percentage}%</p>
            <p>Remaining: {budget.remaining_tokens}</p>
            <button onClick={() => handleCheckAvailability(10000)}>
                Check Availability
            </button>
        </div>
    );
}
```

### 4. Monitoring Integration

```python
# Langfuse Integration for Detailed Tracking
from app.core.llm_usage_callback import LLMUsageCallback

# Automatic token tracking
llm = get_llm()
callback = LLMUsageCallback(
    agent_type="test_composer",
    user_id=current_user.id,
    test_run_id=test_run.id
)

response = await llm.ainvoke(prompt, config={"callbacks": [callback]})

# Callback automatically records to llm_usage table
# which is then aggregated for budget/quota reporting
```

### 5. Temporal Workflow Integration

```python
# Temporal Activity Integration
@activity.defn
async def run_browser_test(test_run_id: int, script: str):
    # Get budget for test
    budget = await budget_service.get_by_scope("test", test_run_id, db)
    
    # Check availability before execution
    available = await budget_service.check_token_availability(
        "test", test_run_id, estimated_tokens, db
    )
    
    if not available["available"]:
        raise ApplicationError("Token budget exceeded")
    
    # Execute test
    result = await execute_playwright_script(script)
    
    # Track usage
    await budget_service.record_token_usage(
        "test", test_run_id, result.tokens_used, db
    )
    
    return result
```

## Security Considerations

### 1. Authentication & Authorization

```python
# Admin-only endpoints
@router.post("/budgets")
async def create_budget(
    current_user: User = Depends(get_current_admin_user)  # Admin check
):
    pass

# User-only access
@router.get("/quotas/my-quota")
async def get_my_quota(
    current_user: User = Depends(get_current_user)  # Auth check
):
    # Only returns current user's quota
    pass
```

### 2. Data Isolation

```python
# Automatic filtering by user_id
async def list_alerts(current_user: User, db: AsyncSession):
    # Non-admin users only see their own alerts
    user_id_filter = None if current_user.is_admin else current_user.id
    
    alerts = await alert_repository.list_all(
        db, user_id=user_id_filter
    )
    return alerts
```

### 3. Input Validation

```python
# Parameter validation
@router.get("/{budget_id}")
async def get_budget(
    budget_id: int = Path(..., ge=1),  # Must be >= 1
    requested_tokens: int = Query(..., gt=0)  # Must be > 0
):
    pass
```

### 4. SQL Injection Prevention

```python
# SQLAlchemy ORM prevents SQL injection
async def get_by_scope(scope_type: str, scope_id: int, db: AsyncSession):
    # Safe parameterized query
    result = await db.execute(
        select(TokenBudget)
        .where(TokenBudget.scope_type == scope_type)  # Parameterized
        .where(TokenBudget.scope_id == scope_id)      # Parameterized
    )
    return result.scalar_one_or_none()
```

## Performance Considerations

### 1. Database Indexing

```sql
-- Optimize common queries
CREATE INDEX ix_token_budgets_scope_type_scope_id 
ON token_budgets(scope_type, scope_id);

CREATE INDEX ix_token_budgets_status 
ON token_budgets(status);

CREATE INDEX ix_token_alerts_severity 
ON token_alerts(severity);
```

### 2. Query Optimization

```python
# Efficient pagination
async def list_budgets(page: int, page_size: int, db: AsyncSession):
    offset = (page - 1) * page_size
    
    # Single query with limit/offset
    budgets, total = await budget_repo.list_all(
        db,
        limit=page_size,
        offset=offset
    )
    
    return budgets, total
```

### 3. Caching Strategy

```python
# Cache frequently accessed data
@lru_cache(maxsize=100)
async def get_budget_config(budget_id: int):
    # Cache budget configuration
    return await budget_repo.get_by_id(budget_id, db)
```

### 4. Async Operations

```python
# Parallel independent operations
async def record_usage(budget_id, quota_id, tokens_used, db):
    # Record budget and quota usage in parallel
    await asyncio.gather(
        budget_service.record_usage(budget_id, tokens_used, db),
        quota_service.record_usage(quota_id, tokens_used, db)
    )
```

### 5. Bulk Operations

```python
# Bulk insert for efficiency
async def bulk_create_alerts(alerts: List[TokenAlert], db: AsyncSession):
    db.bulk_save_objects(alerts)
    await db.commit()
```

---

**Next:** See [API Documentation](TOKEN_LIMITATION_API.md) for complete endpoint reference and examples.