# Token Limitation System Documentation

## Overview

The Token Limitation System is a comprehensive framework for managing and controlling LLM token usage across the DeepAgent Test Runner platform. It provides hierarchical budget management, user-specific quotas, automated alerting, and enforcement mechanisms to optimize costs and ensure fair resource allocation.

## Documentation Structure

### 1. Architecture Documentation
**File:** `TOKEN_LIMITATION_ARCHITECTURE.md`

**Contents:**
- System overview and objectives
- SOLID design principles implementation
- Architecture diagrams (high-level, hierarchy, component interactions)
- Data flows (LLM request, alert generation)
- Integration points (LLM, database, frontend, monitoring)
- Security and performance considerations

**Best For:** Understanding system design and architecture

### 2. API Documentation
**File:** `TOKEN_LIMITATION_API.md`

**Contents:**
- Complete API reference for all 37 endpoints
- Budget endpoints (10 endpoints)
- Quota endpoints (8 endpoints)
- Alert endpoints (10 endpoints)
- Analytics endpoints (9 endpoints)
- Request/response examples
- Error responses and handling
- Rate limiting information
- OpenAPI specification

**Best For:** API integration and reference

### 3. User Guide
**File:** `TOKEN_LIMITATION_USER_GUIDE.md`

**Contents:**
- Getting started guide
- Budget configuration steps
- Quota management procedures
- Alert setup and interpretation
- Analytics interpretation
- Common workflows (setup, alerts, reviews, optimization)
- Troubleshooting common issues
- Best practices for planning, monitoring, and optimization

**Best For:** End-users and administrators

### 4. Developer Guide
**File:** `TOKEN_LIMITATION_DEVELOPER.md`

**Contents:**
- Integration overview and methods
- Service usage examples
- Decorator integration (@enforce_token_limits, @check_token_budget, @track_token_usage)
- LLM client integration (LangChain, OpenAI, custom)
- Testing strategies (unit, integration, mock, load)
- Extension points (custom handlers, enforcement, analytics)
- Complete code examples
- Performance optimization techniques

**Best For:** Developers integrating the system

### 5. Deployment Guide
**File:** `TOKEN_LIMITATION_DEPLOYMENT.md`

**Contents:**
- Installation steps (prerequisites, setup, verification)
- Database migration (Alembic, verification, data migration)
- Configuration options (services, repositories)
- Environment variables setup
- Health checks (API, database, services)
- Monitoring setup (Prometheus, Grafana, Loki, Alertmanager)
- Rollback procedures (database, application, emergency)
- Performance tuning (database, caching, batching)

**Best For:** DevOps and system administrators

### 6. Configuration Reference
**File:** `TOKEN_LIMITATION_CONFIG.md`

**Contents:**
- Environment variables (core, database, Redis, LLM, monitoring)
- Service configuration (budget, quota, alert, analytics)
- Database settings (connection pool, tables, queries)
- Alert thresholds (levels, customization, triggers)
- Enforcement modes (soft, hard, monitoring)
- Priority levels (1-10, resource allocation)
- Performance settings (caching, batching, async, memory)

**Best For:** Configuration and tuning reference

## Quick Start Guides

### For Users

1. **Check your quota:**
   ```bash
   curl -X GET "http://localhost:8080/api/v1/token/quotas/my-quota" \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **View your alerts:**
   ```bash
   curl -X GET "http://localhost:8080/api/v1/token/alerts/my-alerts" \
     -H "Authorization: Bearer $TOKEN"
   ```

3. **Check usage summary:**
   ```bash
   curl -X GET "http://localhost:8080/api/v1/token/analytics/summary" \
     -H "Authorization: Bearer $TOKEN"
   ```

### For Developers

1. **Apply decorator to LLM function:**
   ```python
   from app.core.decorators.token_decorators import enforce_token_limits

   @enforce_token_limits(
       scope_type_param="scope_type",
       scope_id_param="scope_id",
       user_id_param="user_id",
       enforcement_mode="soft"
   )
   async def generate_test(prompt: str, scope_type: str, scope_id: int, user_id: int):
       llm = get_llm()
       response = await llm.ainvoke(prompt)
       return {"result": response.content, "tokens_used": response.usage_metadata.get("total_tokens", 0)}
   ```

2. **Run database migration:**
   ```bash
   alembic upgrade head
   ```

3. **Verify installation:**
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

### For Administrators

1. **Create a budget:**
   ```bash
   curl -X POST "http://localhost:8080/api/v1/token/budgets" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Team Budget",
       "scope_type": "suite",
       "scope_id": 1,
       "total_tokens": 1000000,
       "enforcement_mode": "soft"
     }'
   ```

2. **Configure alerts:**
   ```bash
   curl -X PUT "http://localhost:8080/api/v1/token/alerts/config?enable_email=true" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

3. **Monitor system health:**
   ```bash
   curl http://localhost:8080/api/v1/health/detailed
   ```

## System Features

### Core Capabilities

- **Hierarchical Budget Structure**: Organization → Suite → Test → User levels
- **User-Specific Quotas**: Time-based limits with flexible reset strategies
- **Intelligent Alerting**: Threshold-based notifications with multiple severity levels
- **Multi-Mode Enforcement**: Soft warnings, hard blocks, and monitoring-only modes
- **Comprehensive Analytics**: Usage trends, forecasting, and performance metrics
- **Decorator-Based Integration**: Minimal code changes for automatic token tracking

### Key Metrics

- **37 API Endpoints**: Complete CRUD and analytics operations
- **4 Scope Types**: Organization, suite, test, user
- **3 Enforcement Modes**: Soft, hard, monitoring
- **3 Severity Levels**: Warning, critical, emergency
- **10 Priority Levels**: 1 (lowest) to 10 (highest)
- **Multiple Period Types**: Hourly, daily, weekly, monthly, custom

### Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL 14+ with JSONB
- **ORM**: SQLAlchemy 2.0 with async support
- **Frontend**: React with TypeScript
- **Monitoring**: Prometheus, Grafana, Loki
- **Containerization**: Docker and Docker Compose

## Documentation Navigation

### By Role

| Role | Recommended Documentation |
|------|-------------------------|
| **End User** | User Guide, API Documentation |
| **Developer** | Developer Guide, API Documentation, Architecture Documentation |
| **Administrator** | User Guide, Deployment Guide, Configuration Reference |
| **DevOps** | Deployment Guide, Configuration Reference |
| **Architect** | Architecture Documentation, Configuration Reference |

### By Task

| Task | Recommended Documentation |
|------|-------------------------|
| **Understanding System** | Architecture Documentation, User Guide |
| **API Integration** | API Documentation, Developer Guide |
| **Code Integration** | Developer Guide, Architecture Documentation |
| **Setup & Deployment** | Deployment Guide, Configuration Reference |
| **Configuration** | Configuration Reference, User Guide |
| **Troubleshooting** | User Guide, Deployment Guide |
| **Monitoring** | Deployment Guide, Configuration Reference |
| **Optimization** | User Guide, Developer Guide, Configuration Reference |

### By Topic

| Topic | Documentation |
|-------|---------------|
| **Architecture & Design** | Architecture Documentation |
| **API Reference** | API Documentation |
| **User Workflows** | User Guide |
| **Code Examples** | Developer Guide |
| **Installation** | Deployment Guide |
| **Configuration** | Configuration Reference |
| **Monitoring** | Deployment Guide |
| **Best Practices** | User Guide, Developer Guide |

## File Locations

All documentation is located in:
```
/home/fqs/workspace/self/deepagent-test-runner/docs/
```

### Documentation Files

```
docs/
├── TOKEN_LIMITATION_README.md           # This file - overview and navigation
├── TOKEN_LIMITATION_ARCHITECTURE.md     # System architecture and design
├── TOKEN_LIMITATION_API.md              # Complete API reference
├── TOKEN_LIMITATION_USER_GUIDE.md       # User workflows and best practices
├── TOKEN_LIMITATION_DEVELOPER.md        # Developer integration guide
├── TOKEN_LIMITATION_DEPLOYMENT.md       # Installation and deployment
└── TOKEN_LIMITATION_CONFIG.md           # Configuration reference
```

## Support and Resources

### Getting Help

1. **Check Documentation**: Start with the relevant guide for your role/task
2. **Review Examples**: See code examples in Developer Guide
3. **Troubleshoot**: Check User Guide and Deployment Guide for common issues
4. **Configure**: Reference Configuration Reference for detailed settings

### Additional Resources

- **API Testing**: Use the interactive API docs at `/api/docs`
- **Health Monitoring**: Check `/api/v1/health` endpoints
- **Metrics**: Access Prometheus metrics at `/metrics`
- **Logs**: View application logs for debugging

### Community

- **Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share experiences
- **Contributions**: Submit pull requests for improvements

## Version Information

- **Documentation Version**: 1.0.0
- **System Version**: Compatible with DeepAgent Test Runner 1.0+
- **Last Updated**: 2026-06-13
- **Python Version**: 3.11+
- **Database Version**: PostgreSQL 14+

## Changelog

### Version 1.0.0 (2026-06-13)

**Initial Release**

- Complete Token Limitation System documentation
- 6 comprehensive documentation files
- 37 API endpoints documented
- Complete integration guides
- Deployment and configuration references
- Best practices and troubleshooting guides

## Summary

The Token Limitation System documentation provides comprehensive coverage of all aspects of the system:

- **Complete**: All 6 documentation sections created as specified
- **Structured**: Clear organization with progressive complexity
- **Practical**: Real examples and workflows
- **Professional**: High-quality documentation with diagrams and code samples
- **Accessible**: Navigation guides for different roles and tasks

The documentation serves both users and developers, providing everything needed to understand, integrate, deploy, configure, and optimize the Token Limitation System.