# Infrastructure Directory

This directory contains all infrastructure-related configurations, scripts, and tools separated from business application code.

## Directory Structure

```
infrastructure/
├── ci/                      # CI/CD tools and configurations
│   ├── zap/                 # OWASP ZAP security scanning
│   │   ├── zap.yaml        # ZAP configuration
│   │   ├── spider-scan.js  # Spider scan script
│   │   └── scripts/        # ZAP helper scripts
│   └── sonarqube/           # SonarQube code quality analysis
│       ├── install-sonar-scanner.sh
│       ├── install-sonar-scanner-user.sh
│       └── setup-and-scan.sh
│
└── observability/           # Monitoring and observability stack
    ├── prometheus/          # Metrics collection
    ├── loki/                # Log aggregation
    ├── promtail/            # Log collection agent
    ├── grafana/             # Visualization dashboards
    ├── docker-compose.observability.yml
    ├── start-observability.sh
    └── README.md
```

## Modules

### Observability Stack

**Purpose:** Production monitoring, logging, and distributed tracing

**Components:**
- Prometheus - Metrics scraping and storage
- Loki - Log aggregation
- Promtail - Docker log collection
- Jaeger - Distributed tracing
- Grafana - Unified dashboards

**Usage:**
```bash
cd infrastructure/observability
./start-observability.sh
```

**Documentation:** See [observability/README.md](observability/README.md)

### CI/CD Tools

#### OWASP ZAP
**Purpose:** Dynamic application security testing (DAST)

**Usage:**
```bash
# ZAP runs as Docker service in docker-compose.yml
# Access ZAP UI at http://localhost:8090
```

#### SonarQube
**Purpose:** Static code analysis and quality gates

**Usage:**
```bash
cd infrastructure/ci/sonarqube
./setup-and-scan.sh
```

## Design Principles

1. **Separation of Concerns:** Infrastructure configs separated from application code
2. **Modular Structure:** Each infrastructure component is self-contained
3. **Independent Management:** Each module can be started/stopped independently
4. **Documentation:** Each module has its own README with detailed usage

## Related Documentation

- [Observability Setup Guide](observability/README.md)
- [Docker Compose Deployment](../docs/observability/docker-compose-setup.md)
- [Kubernetes Deployment](../docs/observability/setup.md)
- [Troubleshooting](../docs/observability/troubleshooting.md)

## Maintenance

When adding new infrastructure:
1. Create a new subdirectory under appropriate module (ci/ or observability/)
2. Add configuration files
3. Create startup/management scripts if needed
4. Update this README with documentation
5. Keep infrastructure separate from business logic in service/
