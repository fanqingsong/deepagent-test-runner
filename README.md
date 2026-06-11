# DeepAgent Test Runner

<div align="center">

![DeepAgent Test Runner](https://img.shields.io/badge/AI-Powered%20E2E%20Testing-blue)
![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Desktop-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

</div>

---

## Overview

**DeepAgent Test Runner** is an AI-powered End-to-End (E2E) automated testing platform that revolutionizes how tests are written and executed. By leveraging natural language to drive tests, combined with advanced LLM technology and browser automation capabilities, test creation has never been easier.

## Key Features

### AI-Driven Test Authoring
- **Natural language test definitions**: Write tests in descriptive language without coding knowledge
- **Intelligent test generation**: GLM-4 Plus powered test planning and script generation
- **Adaptive element selection**: AI locates elements based on context, not fixed selectors
- **Visual validation**: UI state validation based on visual appearance

### DeepAgents Orchestration
- **DeepAgents framework integration**: Industry-leading orchestration for test execution
- **Sandboxed execution**: Secure Playwright script execution environment
- **Deterministic execution mode**: Support for pre-generated scripts
- **Real-time feedback**: Live progress updates during test execution

### Complete Observability
- **Langfuse LLM monitoring**: Token usage, cost, and performance tracking
- **Test execution analytics**: Detailed step results, screenshots, and Playwright traces
- **Multi-dimensional dashboards**: Pass rates, execution time, cost trends
- **Historical comparison**: Time-series analysis and trend prediction

### Enterprise Features
- **RBAC system**: Granular test suite and workspace permissions
- **Review workflow**: Built-in peer review mechanism
- **Version control**: Complete history of test cases and suites
- **Tag system**: Flexible test categorization
- **Workspace isolation**: Multi-tenant support with data separation

### Open Ecosystem
- **Test marketplace**: Share and discover test cases and suites
- **RESTful API**: Complete API interface for CI/CD integration
- **Cron scheduling**: Reliable Temporal-based scheduling
- **Webhook notifications**: Real-time test result push

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (:8080)                             │
│                   (Gateway & Reverse Proxy)                      │
└─────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│  React Frontend      │    │    FastAPI Backend (:8011)       │
│  (Vite Dev :5173)    │    │  ┌────────────────────────────┐  │
│                      │    │  │ - Test Composer Agent      │  │
│  - Test Editor       │    │  │ - Script Generator         │  │
│  - Analytics Dashboard│    │  │ - Execution Service        │  │
│  - Test Marketplace   │    │  │ - Analytics Service        │  │
└──────────────────────┘    │  └────────────────────────────┘  │
                             └──────────────────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────┐
        │                                │                            │
        ▼                                ▼                            ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
│  PostgreSQL      │   │  Temporal Server  │   │  Redis              │
│  (:5433)         │   │  (:7233)          │   │  (:6380)             │
│                  │   │                   │   │                      │
│  - Test Data     │   │  - Scheduler      │   │  - Job Queue         │
│  - Execution Results│  │  - Workflow      │   │  - Session Cache     │
└──────────────────┘   └───────────────────┘   └─────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────┐
        │                                │                            │
        ▼                                ▼                            ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
│  Playwright      │   │  GLM LLM API      │   │  Langfuse Stack     │
│  Browser         │   │  (Zhipu AI)       │   │                     │
│                  │   │                   │   │  - LLM Monitoring   │
│  - Browser Auto  │   │  - Test Plan Gen  │   │  - Cost Tracking    │
│  - DOM Extraction│   │  - Script Gen     │   │  - Performance      │
└──────────────────┘   └───────────────────┘   └─────────────────────┘
```

## Core Components

| Component | Tech Stack | Port | Function |
|-----------|-----------|------|----------|
| **Test Orchestrator** | DeepAgents + LangChain | - | AI test planning & script generation |
| **Script Generator** | GLM-4 Plus | - | Natural language to Playwright scripts |
| **Execution Engine** | Playwright + Temporal | - | Test execution & result collection |
| **API Service** | FastAPI | 8011 | Unified backend API |
| **Frontend** | React + Vite | 5173 (dev) | Web UI |
| **Database** | PostgreSQL | 5433 | Data persistence |
| **Cache** | Redis | 6380 | Session & job queue |
| **Scheduler** | Temporal | 7233 | Workflow orchestration |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM
- Linux/macOS/WSL2

### One-Command Start

```bash
# Clone the repository
git clone https://github.com/your-org/deepagent-test-runner.git
cd deepagent-test-runner

# Start development environment (with hot-reload)
./start-dev.sh

# Start production environment
./start-prod.sh
```

### Access Services

- **Web Console**: http://localhost:8080
- **API Documentation**: http://localhost:8011/docs
- **Langfuse Monitoring**: http://localhost:3000

### Stop Services

```bash
# Stop development environment
./stop-dev.sh

# Stop production environment
./stop-prod.sh
```

## Usage Guide

### 1. Create Test Cases

Describe test steps in natural language within the test editor:

```
1. Open https://example.com
2. Click login button
3. Enter username and password
4. Submit form
5. Verify login success message
```

AI automatically generates executable Playwright scripts.

### 2. Configure Scheduling

Set up Cron expressions for scheduled automated testing:

```yaml
cron: "0 2 * * *"  # Daily at 2 AM
environment: production
```

### 3. View Analytics

Real-time test execution results, pass rate trends, and cost analysis.

## Design System

Built with IBM Carbon Design System for enterprise UX:

- **Zero border-radius**: Professional, clean visual style
- **IBM Plex Sans** typography
- **8px grid system**: Precise layout standards
- **Single accent color**: IBM Blue 60 (#0f62fe)
- **Responsive design**: Full support from 320px to 1584px

See [DESIGN.md](DESIGN.md) for details.

## API Integration

### Test Execution API

```bash
# Create test run
curl -X POST http://localhost:8011/api/v1/test-runs/ \
  -H "Content-Type: application/json" \
  -d '{
    "test_definition_id": 123,
    "environment": "production"
  }'

# Get execution results
curl http://localhost:8011/api/v1/test-runs/{run_id}/results
```

### LLM Usage API

```bash
# Query token usage statistics
curl http://localhost:8011/api/v1/llm-usage/summary

# Query daily usage
curl http://localhost:8011/api/v1/llm-usage/by-day?days=30
```

## Data Model

Core database tables:

- `test_definitions`: Test case definitions
- `test_steps`: Test step details
- `test_runs`: Test execution records
- `test_cases`: Individual step results
- `schedules`: Scheduling configurations
- `llm_usage`: LLM call records

See [Database Documentation](.claude/rules/database.md)

## Security Features

- **JWT authentication**
- **RBAC access control**
- **SQL injection protection** (ORM parameterized queries)
- **XSS protection** (frontend input escaping)
- **Rate limiting** (Redis sliding window)
- **Audit logs**: 90-day security event retention

## Internationalization

Multi-language support (i18n):

- ✅ English (default)
- 🔄 Chinese (Simplified) - In development

## Documentation

- [Development Guide](.claude/rules/development.md)
- [Database Schema](.claude/rules/database.md)
- [Frontend Development](.claude/rules/frontend.md)
- [Backend Development](.claude/rules/backend.md)
- [Test Execution Flow](.claude/rules/test-execution.md)
- [Performance Optimization](.claude/rules/performance.md)
- [Troubleshooting](.claude/rules/troubleshooting.md)
- [Configuration Reference](.claude/rules/config.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Community

- **Issue Tracker**: [GitHub Issues](https://github.com/your-org/deepagent-test-runner/issues)
- **Feature Discussions**: [GitHub Discussions](https://github.com/your-org/deepagent-test-runner/discussions)
- **Documentation**: [Project Wiki](https://github.com/your-org/deepagent-test-runner/wiki)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Playwright](https://playwright.dev/) - Modern browser automation framework
- [Temporal](https://temporal.io/) - Durable workflow engine
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - User interface library
- [LangChain](https://langchain.com/) - LLM application framework
- [DeepAgents](https://deepagents.ai/) - AI agent framework
- [IBM Carbon Design System](https://carbondesignsystem.com/) - Enterprise design system

---

<div align="center">
Made with ❤️ by the DeepAgent Team
</div>
