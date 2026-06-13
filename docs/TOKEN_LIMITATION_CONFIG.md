# Token Limitation Configuration Reference

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Service Configuration](#service-configuration)
3. [Database Settings](#database-settings)
4. [Alert Thresholds](#alert-thresholds)
5. [Enforcement Modes](#enforcement-modes)
6. [Priority Levels](#priority-levels)
7. [Performance Settings](#performance-settings)

## Environment Variables

### Core Configuration

```bash
# ============================================================================
# CORE APPLICATION SETTINGS
# ============================================================================

# Application Environment
ENVIRONMENT=production                    # development, staging, production
DEBUG=False                               # Enable debug mode
SECRET_KEY=your-secret-key-here           # JWT signing key
LOG_LEVEL=INFO                            # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Server Configuration
HOST=0.0.0.0                              # Server host
PORT=8011                                 # Server port
WORKERS=4                                 # Number of worker processes
```

### Database Configuration

```bash
# ============================================================================
# DATABASE SETTINGS
# ============================================================================

# PostgreSQL Configuration
POSTGRES_HOST=localhost                   # Database host
POSTGRES_PORT=5432                        # Database port
POSTGRES_USER=cc_test_user                # Database user
POSTGRES_PASSWORD=secure_password         # Database password
POSTGRES_DB=cc_test_db                   # Database name

# Database Pool Configuration
DB_POOL_SIZE=20                           # Connection pool size
DB_MAX_OVERFLOW=40                       # Max overflow connections
DB_POOL_TIMEOUT=30                        # Connection timeout (seconds)
DB_POOL_RECYCLE=3600                      # Connection recycle time (seconds)

# Database URL (constructed from above)
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Redis Configuration

```bash
# ============================================================================
# REDIS SETTINGS
# ============================================================================

# Redis Configuration
REDIS_HOST=localhost                      # Redis host
REDIS_PORT=6379                           # Redis port
REDIS_PASSWORD=                           # Redis password (empty if none)
REDIS_DB=0                                # Redis database number

# Redis URL (constructed from above)
REDIS_URL=redis://host:port/db

# Redis Cache Configuration
REDIS_CACHE_ENABLED=True                  # Enable Redis caching
REDIS_CACHE_TTL=300                       # Cache TTL (seconds)
REDIS_CACHE_MAX_SIZE=1000                # Max cached items
```

### LLM Configuration

```bash
# ============================================================================
# LLM API SETTINGS
# ============================================================================

# LLM API Configuration
LLM_API_KEY=your-api-key-here            # LLM API key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4  # LLM API base URL
LLM_MODEL=glm-4-plus                      # Default LLM model
LLM_TIMEOUT=120                           # LLM request timeout (seconds)

# LLM Token Pricing (for cost calculation)
LLM_TOKEN_PRICE_INPUT=0.00001            # Price per 1K input tokens
LLM_TOKEN_PRICE_OUTPUT=0.00002           # Price per 1K output tokens
```

### Token Limitation Core Settings

```bash
# ============================================================================
# TOKEN LIMITATION CORE SETTINGS
# ============================================================================

# System Enable/Disable
TOKEN_LIMITATION_ENABLED=True             # Master switch for token limitation
TOKEN_ENFORCEMENT_ENABLED=True            # Enable enforcement (vs. monitoring only)

# Default Budget Settings
TOKEN_BUDGET_DEFAULT_LIMIT=1000000        # Default budget limit (tokens)
TOKEN_BUDGET_DEFAULT_PERIOD=monthly       # Default budget period
TOKEN_BUDGET_DEFAULT_ENFORCEMENT=soft     # Default enforcement mode
TOKEN_BUDGET_DEFAULT_PRIORITY=5           # Default budget priority

# Default Quota Settings
TOKEN_QUOTA_DEFAULT_LIMIT=50000           # Default daily quota (tokens)
TOKEN_QUOTA_DEFAULT_PERIOD=daily          # Default quota period
TOKEN_QUOTA_DEFAULT_RESET=calendar        # Default reset strategy
TOKEN_QUOTA_DEFAULT_PRIORITY=5            # Default quota priority

# Alert Configuration
TOKEN_ALERT_ENABLED=True                   # Enable alert system
TOKEN_ALERT_EMAIL_ENABLED=True            # Enable email alerts
TOKEN_ALERT_WEBHOOK_ENABLED=False         # Enable webhook alerts
TOKEN_ALERT_WEBHOOK_URL=                  # Webhook URL for alerts

# Notification Configuration
SMTP_HOST=smtp.company.com                # SMTP server host
SMTP_PORT=587                             # SMTP server port
SMTP_USER=alerts@company.com              # SMTP username
SMTP_PASSWORD=smtp_password               # SMTP password
SMTP_FROM=noreply@company.com             # From email address
SMTP_USE_TLS=True                         # Use TLS for SMTP
```

### Monitoring and Analytics

```bash
# ============================================================================
# MONITORING AND ANALYTICS
# ============================================================================

# Metrics Configuration
TOKEN_METRICS_ENABLED=True                # Enable Prometheus metrics
TOKEN_METRICS_EXPORT_INTERVAL=60          # Metrics export interval (seconds)
TOKEN_METRICS_RETENTION_DAYS=30           # Metrics retention period

# Logging Configuration
TOKEN_LOG_ENABLED=True                     # Enable token logging
TOKEN_LOG_LEVEL=INFO                      # Token logging level
TOKEN_LOG_FORMAT=json                     # Log format (json, text)

# Analytics Configuration
TOKEN_ANALYTICS_ENABLED=True               # Enable analytics
TOKEN_ANALYTICS_RETENTION_DAYS=90          # Analytics data retention
TOKEN_FORECAST_ENABLED=True                # Enable usage forecasting
TOKEN_FORECAST_HORIZON_DAYS=30            # Forecast horizon (days)
```

### Performance Configuration

```bash
# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

# Caching Configuration
TOKEN_CACHE_ENABLED=True                   # Enable caching
TOKEN_CACHE_TTL=300                       # Cache TTL (seconds)
TOKEN_CACHE_BACKEND=redis                 # Cache backend (memory, redis)
TOKEN_CACHE_MAX_SIZE=1000                 # Maximum cache size

# Batch Processing
TOKEN_BATCH_SIZE=100                      # Default batch size
TOKEN_BATCH_TIMEOUT=30                    # Batch operation timeout (seconds)
TOKEN_ASYNC_ENABLED=True                  # Enable async operations

# Query Optimization
TOKEN_QUERY_TIMEOUT=10                    # Query timeout (seconds)
TOKEN_QUERY_PAGE_SIZE=20                  # Default page size for queries
TOKEN_QUERY_MAX_PAGE_SIZE=100             # Maximum page size
```

## Service Configuration

### Budget Service Configuration

```python
# platform/backend/app/services/token_budget_service.py

class TokenBudgetServiceConfig:
    """Token budget service configuration."""
    
    # Service Settings
    SERVICE_ENABLED = True                  # Enable budget service
    SERVICE_TIMEOUT = 30                    # Service timeout (seconds)
    
    # Budget Defaults
    DEFAULT_LIMIT = 1000000                # Default budget limit (tokens)
    DEFAULT_PERIOD = "monthly"             # Default period type
    DEFAULT_ENFORCEMENT = "soft"           # Default enforcement mode
    DEFAULT_PRIORITY = 5                   # Default priority level
    
    # Hierarchy Settings
    MAX_HIERARCHY_DEPTH = 4                # Maximum hierarchy depth
    ALLOW_INHERITANCE = True               # Allow budget inheritance
    DEFAULT_INHERITANCE_STRATEGY = "percentage"  # Default inheritance strategy
    
    # Calculation Settings
    FORECAST_ENABLED = True                # Enable usage forecasting
    FORECAST_MODEL = "linear"              # Forecasting model (linear, exponential)
    FORECAST_CONFIDENCE_THRESHOLD = 0.7   # Minimum confidence for forecasts
    
    # Validation Settings
    VALIDATE_HIERARCHY = True              # Validate budget hierarchy
    VALIDATE_PERIODS = True                # Validate budget periods
    VALIDATE_THRESHOLDS = True            # Validate alert thresholds
```

### Quota Service Configuration

```python
# platform/backend/app/services/token_quota_service.py

class TokenQuotaServiceConfig:
    """Token quota service configuration."""
    
    # Service Settings
    SERVICE_ENABLED = True                  # Enable quota service
    SERVICE_TIMEOUT = 30                    # Service timeout (seconds)
    
    # Quota Defaults
    DEFAULT_LIMIT = 50000                  # Default daily quota (tokens)
    DEFAULT_PERIOD = "daily"               # Default period type
    DEFAULT_RESET_STRATEGY = "calendar"     # Default reset strategy
    DEFAULT_PRIORITY = 5                   # Default priority level
    
    # Reset Settings
    RESET_TIMEZONE = "UTC"                 # Reset timezone
    RESET_CALENDAR_TIME = "00:00"         # Calendar reset time
    RESET_ROLLING_PERIOD_DAYS = 1          # Rolling reset period (days)
    
    # User Quota Settings
    ALLOW_MULTIPLE_QUOTAS = False          # Allow multiple quotas per user
    QUOTA_PER_USER_LIMIT = 1               # Maximum quotas per user
    ADMIN_BYPASS_QUOTA = True              # Allow admins to bypass quota
    
    # Validation Settings
    VALIDATE_PERIODS = True                # Validate quota periods
    VALIDATE_RESET_STRATEGIES = True       # Validate reset strategies
```

### Alert Service Configuration

```python
# platform/backend/app/services/token_alert_service.py

class TokenAlertServiceConfig:
    """Token alert service configuration."""
    
    # Service Settings
    SERVICE_ENABLED = True                  # Enable alert service
    SERVICE_TIMEOUT = 30                    # Service timeout (seconds)
    
    # Alert Defaults
    DEFAULT_THRESHOLDS = {                  # Default alert thresholds
        "warning": 80,
        "critical": 90,
        "emergency": 95
    }
    
    # Alert Generation
    ALERT_ON_THRESHOLD_CROSS = True        # Alert when crossing thresholds
    ALERT_ON_PERIOD_START = False          # Alert on period start
    ALERT_ON_PERIOD_END = True             # Alert on period end
    ALERT_ON_BUDGET_EXHAUSTED = True       # Alert when budget exhausted
    
    # Alert Deduplication
    DEDUPLICATE_ALERTS = True              # Deduplicate similar alerts
    DEDUPLICATION_WINDOW_MINUTES = 30      # Deduplication time window (minutes)
    MAX_ALERTS_PER_HOUR = 100              # Maximum alerts per hour
    
    # Notification Settings
    NOTIFICATION_RETRY_ATTEMPTS = 3        # Notification retry attempts
    NOTIFICATION_RETRY_DELAY_SECONDS = 60  # Retry delay (seconds)
    NOTIFICATION_TIMEOUT_SECONDS = 30      # Notification timeout (seconds)
    
    # Alert Retention
    ALERT_RETENTION_DAYS = 90              # Alert retention period (days)
    ARCHIVE_RESOLVED_ALERTS = True         # Archive resolved alerts
```

### Analytics Service Configuration

```python
# platform/backend/app/services/token_reporting_service.py

class TokenReportingServiceConfig:
    """Token reporting service configuration."""
    
    # Service Settings
    SERVICE_ENABLED = True                  # Enable reporting service
    SERVICE_TIMEOUT = 60                    # Service timeout (seconds)
    
    # Analytics Settings
    ANALYTICS_RETENTION_DAYS = 90          # Analytics data retention (days)
    AGGREGATION_INTERVAL_HOURS = 1        # Data aggregation interval (hours)
    
    # Reporting Settings
    COST_CALCULATION_ENABLED = True        # Enable cost calculation
    COST_PER_TOKEN_DEFAULT = 0.00001      # Default cost per token
    COST_MODEL_SPECIFIC = True             # Use model-specific pricing
    
    # Forecasting Settings
    FORECAST_ENABLED = True                # Enable usage forecasting
    FORECAST_MODELS = ["linear", "exponential", "moving_average"]
    FORECAST_DEFAULT_MODEL = "linear"      # Default forecasting model
    FORECAST_CONFIDENCE_THRESHOLD = 0.7    # Minimum confidence for forecasts
    FORECAST_MIN_DATA_POINTS = 7           # Minimum data points for forecasting
    
    # Trend Analysis
    TREND_ANALYSIS_ENABLED = True          # Enable trend analysis
    TREND_PERIOD_DAYS = 30                 # Trend analysis period (days)
    TREND_SMOOTHING_FACTOR = 0.3           # Exponential smoothing factor
    
    # Comparison Settings
    COMPARISON_MAX_ITEMS = 10              # Maximum items in comparisons
    COMPARISON_CACHE_TTL = 300             # Comparison cache TTL (seconds)
```

## Database Settings

### Connection Pool Configuration

```python
# platform/backend/app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

# Database engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,                              # Echo SQL queries
    pool_size=20,                            # Number of connections to maintain
    max_overflow=40,                         # Additional connections allowed
    pool_timeout=30,                         # Connection timeout (seconds)
    pool_recycle=3600,                       # Recycle connections after 1 hour
    pool_pre_ping=True,                      # Verify connections before using
    poolclass=QueuePool,                     # Connection pool class
    
    # Performance settings
    connect_args={
        "connect_timeout": 10,
        "command_timeout": 30,
        "server_settings": {
            "application_name": "deepagent_test_runner",
            "jit": "off"                     # Disable JIT for consistent performance
        }
    }
)
```

### Table Configuration

```sql
-- Token Budgets Table Configuration
CREATE TABLE token_budgets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    scope_type VARCHAR(50) NOT NULL,
    scope_id INTEGER,
    parent_budget_id INTEGER REFERENCES token_budgets(id),
    period_type VARCHAR(20) NOT NULL DEFAULT 'monthly',
    period_start TIMESTAMP NOT NULL DEFAULT NOW(),
    period_end TIMESTAMP,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    used_tokens BIGINT NOT NULL DEFAULT 0,
    remaining_tokens BIGINT NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 5,
    enforcement_mode VARCHAR(20) NOT NULL DEFAULT 'soft',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    inherit_from_parent BOOLEAN DEFAULT FALSE,
    inherit_strategy VARCHAR(50),
    alert_thresholds JSONB DEFAULT '{"warning": 80, "critical": 90, "emergency": 95}',
    config_data JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_reset_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX ix_token_budgets_scope_type_scope_id ON token_budgets(scope_type, scope_id);
CREATE INDEX ix_token_budgets_parent_id ON token_budgets(parent_budget_id);
CREATE INDEX ix_token_budgets_status ON token_budgets(status);
CREATE INDEX ix_token_budgets_period_start_end ON token_budgets(period_start, period_end);
CREATE INDEX ix_token_budgets_priority_status ON token_budgets(priority, status);
```

### Query Optimization Settings

```python
# Query optimization configuration
QUERY_SETTINGS = {
    # Timeout settings
    'default_timeout': 10,                  # Default query timeout (seconds)
    'long_running_timeout': 60,            # Long-running query timeout (seconds)
    
    # Pagination settings
    'default_page_size': 20,               # Default page size
    'max_page_size': 100,                  # Maximum page size
    
    # Batch settings
    'batch_size': 100,                      # Default batch size
    'max_batch_size': 1000,                 # Maximum batch size
    
    # Optimization settings
    'use_selectinload': True,               # Use selectin loading for relationships
    'use_joinedload': False,                # Use joined loading (careful with N+1)
    'use_nocached': False,                  # Disable caching for specific queries
}
```

## Alert Thresholds

### Threshold Configuration

```json
{
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  }
}
```

### Threshold Levels

| Level | Default | Description | Recommended Action |
|-------|---------|-------------|-------------------|
| **warning** | 80% | Initial warning threshold | Review usage patterns |
| **critical** | 90% | Critical usage threshold | Plan corrective action |
| **emergency** | 95% | Emergency usage threshold | Immediate action required |

### Custom Thresholds

```python
# Conservative thresholds (early warning)
CONSERVATIVE_THRESHOLDS = {
    "warning": 70,
    "critical": 85,
    "emergency": 95
}

# Aggressive thresholds (late warning)
AGGRESSIVE_THRESHOLDS = {
    "warning": 90,
    "critical": 95,
    "emergency": 99
}

# Custom thresholds by priority
HIGH_PRIORITY_THRESHOLDS = {
    "warning": 60,
    "critical": 80,
    "emergency": 90
}

LOW_PRIORITY_THRESHOLDS = {
    "warning": 90,
    "critical": 95,
    "emergency": 99
}
```

### Threshold Triggers

```python
# Threshold trigger configuration
THRESHOLD_TRIGGERS = {
    # Trigger on threshold crossing
    "on_cross": True,                      # Alert when crossing threshold
    "on_period_end": True,                 # Alert at period end if exceeded
    "on_budget_exhausted": True,           # Alert when budget exhausted
    
    # Trigger frequency
    "trigger_once_per_period": True,       # Only trigger once per threshold per period
    "recross_trigger": False,              # Don't re-trigger if crossed again
    
    # Alert timing
    "immediate": True,                     # Send alerts immediately
    "batch_delay_minutes": 0,              # Delay for batching alerts
}
```

## Enforcement Modes

### Mode Definitions

#### Soft Mode (Warning Only)

```python
SOFT_MODE_CONFIG = {
    "name": "soft",
    "description": "Warn when exceeded, but allow usage",
    "behavior": {
        "check_availability": True,        # Still check availability
        "block_on_exceeded": False,        # Don't block when exceeded
        "log_warning": True,               # Log warnings
        "generate_alert": True,            # Generate alerts
        "allow_execution": True            # Allow execution to proceed
    },
    "use_cases": [
        "Development environments",
        "Testing new features",
        "Low-priority operations"
    ]
}
```

#### Hard Mode (Block on Exceed)

```python
HARD_MODE_CONFIG = {
    "name": "hard",
    "description": "Block usage when exceeded",
    "behavior": {
        "check_availability": True,        # Check availability
        "block_on_exceeded": True,         # Block when exceeded
        "log_warning": True,               # Log warnings
        "generate_alert": True,            # Generate alerts
        "allow_execution": False           # Don't allow execution
    },
    "use_cases": [
        "Production environments",
        "High-cost operations",
        "Critical resource management"
    ]
}
```

#### Monitoring Mode (Track Only)

```python
MONITORING_MODE_CONFIG = {
    "name": "monitoring",
    "description": "Track only, no enforcement",
    "behavior": {
        "check_availability": False,       # Don't check availability
        "block_on_exceeded": False,        # Don't block when exceeded
        "log_warning": True,               # Log warnings
        "generate_alert": True,            # Generate alerts
        "allow_execution": True            # Always allow execution
    },
    "use_cases": [
        "Observation and analysis",
        "Gradual rollout",
        "A/B testing enforcement"
    ]
}
```

### Mode Selection Guidelines

| Scenario | Recommended Mode | Rationale |
|----------|-----------------|-----------|
| **Development** | soft | Allow flexibility while tracking usage |
| **Staging** | soft | Test limits without blocking |
| **Production** | hard | Strict cost control |
| **Critical Tests** | hard | Prevent runaway costs |
| **Analytics** | monitoring | Track usage without restrictions |
| **Onboarding** | monitoring | Learn usage patterns |

## Priority Levels

### Priority Configuration

```python
PRIORITY_LEVELS = {
    1: {
        "name": "lowest",
        "description": "Lowest priority operations",
        "enforcement": "monitoring",
        "alert_thresholds": {"warning": 90, "critical": 95, "emergency": 99}
    },
    2: {
        "name": "low",
        "description": "Low priority operations",
        "enforcement": "soft",
        "alert_thresholds": {"warning": 85, "critical": 92, "emergency": 97}
    },
    3: {
        "name": "medium-low",
        "description": "Medium-low priority operations",
        "enforcement": "soft",
        "alert_thresholds": {"warning": 80, "critical": 90, "emergency": 95}
    },
    4: {
        "name": "medium",
        "description": "Medium priority operations",
        "enforcement": "soft",
        "alert_thresholds": {"warning": 75, "critical": 88, "emergency": 95}
    },
    5: {
        "name": "medium-high",
        "description": "Medium-high priority operations",
        "enforcement": "soft",
        "alert_thresholds": {"warning": 70, "critical": 85, "emergency": 95}
    },
    6: {
        "name": "high",
        "description": "High priority operations",
        "enforcement": "hard",
        "alert_thresholds": {"warning": 60, "critical": 80, "emergency": 90}
    },
    7: {
        "name": "very-high",
        "description": "Very high priority operations",
        "enforcement": "hard",
        "alert_thresholds": {"warning": 50, "critical": 75, "emergency": 90}
    },
    8: {
        "name": "critical",
        "description": "Critical priority operations",
        "enforcement": "hard",
        "alert_thresholds": {"warning": 40, "critical": 70, "emergency": 85}
    },
    9: {
        "name": "emergency",
        "description": "Emergency priority operations",
        "enforcement": "hard",
        "alert_thresholds": {"warning": 30, "critical": 60, "emergency": 80}
    },
    10: {
        "name": "highest",
        "description": "Highest priority operations",
        "enforcement": "hard",
        "alert_thresholds": {"warning": 20, "critical": 50, "emergency": 75}
    }
}
```

### Priority-Based Resource Allocation

```python
# Resource allocation by priority
PRIORITY_RESOURCE_ALLOCATION = {
    # Budget allocation percentage
    "budget_allocation": {
        1: 0.05,    # 5% for lowest priority
        2: 0.05,    # 5% for low priority
        3: 0.10,    # 10% for medium-low priority
        4: 0.10,    # 10% for medium priority
        5: 0.15,    # 15% for medium-high priority
        6: 0.15,    # 15% for high priority
        7: 0.15,    # 15% for very-high priority
        8: 0.10,    # 10% for critical priority
        9: 0.10,    # 10% for emergency priority
        10: 0.05    # 5% for highest priority
    },
    
    # Quota allocation by user role priority
    "quota_allocation": {
        "viewer": 1,        # 10K tokens/day
        "tester": 3,         # 25K tokens/day
        "developer": 5,      # 50K tokens/day
        "senior_developer": 7, # 75K tokens/day
        "lead": 9,           # 100K tokens/day
        "admin": 10          # 150K tokens/day
    }
}
```

## Performance Settings

### Caching Configuration

```python
# Cache configuration
CACHE_SETTINGS = {
    # General cache settings
    "enabled": True,
    "backend": "redis",                    # redis, memory
    "default_ttl": 300,                    # 5 minutes
    "max_size": 1000,                      # Maximum cached items
    
    # Budget cache
    "budget": {
        "enabled": True,
        "ttl": 300,                         # 5 minutes
        "max_size": 500,
        "key_prefix": "budget:"
    },
    
    # Quota cache
    "quota": {
        "enabled": True,
        "ttl": 300,                         # 5 minutes
        "max_size": 500,
        "key_prefix": "quota:"
    },
    
    # Alert cache
    "alert": {
        "enabled": True,
        "ttl": 60,                          # 1 minute
        "max_size": 1000,
        "key_prefix": "alert:"
    },
    
    # Analytics cache
    "analytics": {
        "enabled": True,
        "ttl": 600,                         # 10 minutes
        "max_size": 200,
        "key_prefix": "analytics:"
    }
}
```

### Batch Processing Configuration

```python
# Batch processing settings
BATCH_SETTINGS = {
    # General batch settings
    "enabled": True,
    "default_size": 100,
    "max_size": 1000,
    "timeout": 30,                          # 30 seconds
    
    # Usage recording batch
    "usage_recording": {
        "enabled": True,
        "batch_size": 100,
        "flush_interval": 10,               # 10 seconds
        "max_queue_size": 1000
    },
    
    # Alert generation batch
    "alert_generation": {
        "enabled": True,
        "batch_size": 50,
        "flush_interval": 5,                 # 5 seconds
        "max_queue_size": 500
    },
    
    # Analytics aggregation batch
    "analytics_aggregation": {
        "enabled": True,
        "batch_size": 200,
        "flush_interval": 60,                # 1 minute
        "max_queue_size": 2000
    }
}
```

### Async Operation Configuration

```python
# Async operation settings
ASYNC_SETTINGS = {
    # General async settings
    "enabled": True,
    "max_concurrent_tasks": 100,
    "task_timeout": 120,                    # 2 minutes
    
    # Budget check async
    "budget_check": {
        "enabled": True,
        "max_concurrent": 50,
        "timeout": 10                        # 10 seconds
    },
    
    # Usage recording async
    "usage_recording": {
        "enabled": True,
        "max_concurrent": 20,
        "timeout": 30                        # 30 seconds
    },
    
    # Alert notification async
    "alert_notification": {
        "enabled": True,
        "max_concurrent": 10,
        "timeout": 60                        # 1 minute
    }
}
```

### Query Optimization Configuration

```python
# Query optimization settings
QUERY_SETTINGS = {
    # General query settings
    "default_timeout": 10,                   # 10 seconds
    "long_running_timeout": 60,             # 1 minute
    "max_execution_time": 120,              # 2 minutes
    
    # Pagination settings
    "default_page_size": 20,
    "max_page_size": 100,
    "optimize_pagination": True,
    
    # Relationship loading
    "use_selectinload": True,
    "use_joinedload": False,
    "use_subqueryload": False,
    
    # Query hints
    "enable_query_hints": True,
    "use_index_hints": True,
    
    # Result limiting
    "max_results": 10000,
    "limit_large_queries": True
}
```

### Memory Optimization Configuration

```python
# Memory optimization settings
MEMORY_SETTINGS = {
    # General memory settings
    "max_memory_usage": 2147483648,         # 2GB
    "gc_threshold": 0.8,                    # 80% memory usage triggers GC
    
    # Query result memory
    "max_query_result_size": 10485760,     # 10MB
    "cache_result_size": 1048576,           # 1MB
    
    # Batch operation memory
    "max_batch_memory": 52428800,           # 50MB
    "batch_size_memory_limit": 1048576,      # 1MB per batch item
    
    # Connection memory
    "connection_memory_limit": 1048576,      # 1MB per connection
    "result_cache_size": 5242880            # 5MB result cache
}
```

---

**Documentation Complete**

The Token Limitation System documentation is now complete with 6 comprehensive guides:

1. **Architecture Documentation** (`TOKEN_LIMITATION_ARCHITECTURE.md`) - System overview, design principles, and component interactions
2. **API Documentation** (`TOKEN_LIMITATION_API.md`) - Complete API reference with 37 endpoints
3. **User Guide** (`TOKEN_LIMITATION_USER_GUIDE.md`) - Budget configuration, quota management, and troubleshooting
4. **Developer Guide** (`TOKEN_LIMITATION_DEVELOPER.md`) - Code integration, decorator usage, and testing strategies
5. **Deployment Guide** (`TOKEN_LIMITATION_DEPLOYMENT.md`) - Installation, migration, and monitoring setup
6. **Configuration Reference** (`TOKEN_LIMITATION_CONFIG.md`) - Environment variables, service settings, and performance tuning

All documentation files are located in `/home/fqs/workspace/self/deepagent-test-runner/docs/`.