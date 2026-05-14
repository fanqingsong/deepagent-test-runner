# Plan: Observability Stack Implementation

## Summary
Implement comprehensive observability for the Claude Code Test Runner backend service with Prometheus metrics, Grafana dashboards, Loki logging, and Jaeger distributed tracing to enable proactive monitoring, debugging, and performance optimization.

## User Story
As a **Site Reliability Engineer**, I want **centralized observability with metrics, logs, and traces**, so that **I can proactively detect issues, debug problems efficiently, and optimize system performance**.

## Problem → Solution
**Current State**: Basic Python logging with print statements, no centralized logging, no metrics collection, no distributed tracing, reactive debugging only.

**Desired State**: Structured JSON logging with Loki, Prometheus metrics exposed at `/metrics`, Grafana dashboards for visualization, Jaeger tracing for end-to-end request tracking, proactive issue detection with alerts.

## Metadata
- **Complexity**: Large (Cross-cutting concerns, multiple new systems, 15+ files)
- **Source PRD**: N/A (focused observability implementation)
- **PRD Phase**: N/A
- **Estimated Files**: 18 files (4 middleware, 4 configs, 4 K8s manifests, 3 dashboards, 2 docs, 1 requirements update)

---

## UX Design

### Before
```
┌─────────────────────────────────────────────────────────┐
│  Debug issue:                                           │
│  1. SSH into container                                  │
│  2. grep through logs                                   │
│  3. No metrics to see trends                            │
│  4. No way to trace request across services             │
│  5. Reactive: wait for user reports                    │
└─────────────────────────────────────────────────────────┘
```

### After
```
┌─────────────────────────────────────────────────────────────┐
│  Debug issue:                                               │
│  1. Alert triggered in Slack (high error rate)             │
│  2. Open Grafana dashboard → see spike in latency          │
│  3. Click trace ID → Jaeger shows full request path        │
│  4. Search logs in Loki by trace_id → find error details   │
│  5. Proactive: fix before users notice                    │
└─────────────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Troubleshooting | SSH + grep logs | Grafana dashboards + Loki search | 10x faster debugging |
| Performance issues | No visibility | Prometheus metrics graphs | Proactive optimization |
| Request tracking | No correlation | Trace ID in logs + Jaeger UI | End-to-end visibility |
| Alerting | User reports first | Prometheus alerts → Slack | Proactive detection |
| Capacity planning | Guesswork | Historical metrics + trends | Data-driven decisions |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 (critical) | `service/backend/app/main.py` | 19-100 | Application structure, middleware setup, lifespan |
| P0 (critical) | `service/backend/app/core/config.py` | 1-80 | Environment variable pattern for observability config |
| P0 (critical) | `service/backend/app/services/auth/auth_service.py` | 16-17 | Existing logging pattern (`logger = logging.getLogger(__name__)`) |
| P1 (important) | `service/backend/app/middleware/admin.py` | 1-65 | Middleware pattern implementation |
| P1 (important) | `service/backend/requirements.txt` | 1-30 | Current dependencies, add monitoring packages |
| P2 (reference) | `service/nginx/nginx.conf` | 19-22 | Current logging format (for Loki integration) |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Prometheus Python Client | https://prometheus.github.io/client_python/ | Use `prometheus_fastapi_instrumentator` for automatic HTTP metrics |
| Grafana Loki | https://grafana.com/docs/loki/latest/ | Log aggregation with label-based indexing, JSON format preferred |
| OpenTelemetry Tracing | https://opentelemetry.io/docs/instrumentation/python/ | Use `opentelemetry-instrumentation-fastapi` for auto-instrumentation |
| Jaeger Deployment | https://www.jaegertracing.io/docs/latest/deployment/ | All-in-one deployment for development, production with Elasticsearch |

---

## Patterns to Mirror

### LOGGING_PATTERN
// SOURCE: `service/backend/app/services/auth/auth_service.py:16-17`
```python
import logging

logger = logging.getLogger(__name__)
```
**Pattern**: Module-level logger using `__name__`, log with `logger.info()`, `logger.error()`, `logger.warning()`

### MIDDLEWARE_PATTERN
// SOURCE: `service/backend/app/main.py:49-56`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Pattern**: FastAPI middleware added with `app.add_middleware()` before routes

### LIFESPAN_CONTEXT
// SOURCE: `service/backend/app/main.py:19-29`
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    print(f"Shutting down {settings.APP_NAME}")
```
**Pattern**: Use lifespan for startup/shutdown of observability systems (Prometheus registry, tracer provider)

### CONFIGURATION_PATTERN
// SOURCE: `service/backend/app/core/config.py:14-25`
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    APP_NAME: str = Field(default="Test Case Service")
```
**Pattern**: Add observability config fields (JAEGER_AGENT_HOST, LOKI_ENDPOINT, PROMETHEUS_PORT)

### HEALTH_CHECK_PATTERN
// SOURCE: `service/backend/app/main.py:96-99`
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```
**Pattern**: Add `/metrics` endpoint for Prometheus scraping alongside `/health`

---

## Files to Change

### Observability Instrumentation (4 files)
| File | Action | Justification |
|---|---|---|---|
| `service/backend/app/middleware/prometheus.py` | CREATE | Prometheus metrics middleware |
| `service/backend/app/middleware/logging.py` | CREATE | Structured JSON logging middleware |
| `service/backend/app/middleware/tracing.py` | CREATE | OpenTelemetry tracing middleware |
| `service/backend/app/core/observability.py` | CREATE | Centralized observability setup |

### Configuration Updates (2 files)
| File | Action | Justification |
|---|---|---|---|
| `service/backend/app/core/config.py` | UPDATE | Add observability settings |
| `service/backend/requirements.txt` | UPDATE | Add monitoring dependencies |

### Application Integration (1 file)
| File | Action | Justification |
|---|---|---|---|
| `service/backend/app/main.py` | UPDATE | Integrate middleware and lifespan |

### Kubernetes Deployment (4 files)
| File | Action | Justification |
|---|---|---|---|
| `k8s/observability/prometheus-config.yaml` | CREATE | Prometheus scrape configuration |
| `k8s/observability/grafana-dashboards.yaml` | CREATE | Grafana dashboard provisioning |
| `k8s/observability/loki-stack.yaml` | CREATE | Loki + Promtail deployment |
| `k8s/observability/jaeger-deployment.yaml` | CREATE | Jaeger all-in-one deployment |

### Documentation (2 files)
| File | Action | Justification |
|---|---|---|---|
| `docs/observability/setup.md` | CREATE | Setup and configuration guide |
| `docs/observability/troubleshooting.md` | CREATE | Common issues and solutions |

### Dashboards (3 JSON files)
| File | Action | Justification |
|---|---|---|---|
| `grafana/dashboards/overview.json` | CREATE | Main system overview dashboard |
| `grafana/dashboards/api-performance.json` | CREATE | API performance metrics |
| `grafana/dashboards/database.json` | CREATE | Database connection pool metrics |

## NOT Building

- Multi-service tracing (only backend service in scope)
- Advanced log parsing (use Loki defaults)
- Custom Prometheus exporters (use FastAPI instrumentor)
- Business metrics dashboards (focus on technical observability)
- Log retention policies (use Loki defaults)
- Metrics alerting rules (alerting configuration out of scope)
- High-availability observability stack (single instance deployments)

---

## Step-by-Step Tasks

### Task 1: Add Observability Dependencies
- **ACTION**: Update requirements.txt with monitoring packages
- **IMPLEMENT**:
  ```txt
  # Observability
  prometheus-fastapi-instrumentator==6.1.0
  prometheus-client==0.19.0
  opentelemetry-api==1.21.0
  opentelemetry-sdk==1.21.0
  opentelemetry-instrumentation-fastapi==0.42b0
  opentelemetry-instrumentation-httpx==0.42b0
  opentelemetry-exporter-jaeger==1.21.0
  opentelemetry-instrumentation-sqlalchemy==0.42b0
  structlog==23.2.0
  python-json-logger==2.0.7
  ```
- **MIRROR**: Follow requirements.txt format from `service/backend/requirements.txt:1-30`
- **IMPORTS**: N/A (requirements file)
- **GOTCHA**: Pin versions to avoid breaking changes, use compatible opentelemetry packages (all same version)
- **VALIDATE**: `pip install -r requirements.txt` succeeds without conflicts

### Task 2: Add Observability Configuration
- **ACTION**: Extend Settings class with observability environment variables
- **IMPLEMENT**:
  ```python
  # service/backend/app/core/config.py
  class Settings(BaseSettings):
      # ... existing fields ...

      # Observability - Prometheus
      PROMETHEUS_PORT: int = Field(default=9090, description="Prometheus metrics port")
      PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")

      # Observability - Loki
      LOKI_ENABLED: bool = Field(default=False, description="Enable Loki logging")
      LOKI_ENDPOINT: str = Field(default="http://loki:3100/loki/api/v1/push", description="Loki push endpoint")

      # Observability - Jaeger
      JAEGER_ENABLED: bool = Field(default=False, description="Enable Jaeger tracing")
      JAEGER_AGENT_HOST: str = Field(default="jaeger", description="Jaeger agent hostname")
      JAEGER_AGENT_PORT: int = Field(default=6831, description="Jaeger agent port")
      TRACE_SAMPLE_RATE: float = Field(default=0.1, description="Trace sampling rate (0.0-1.0)")

      # Observability - Logging
      LOG_LEVEL: str = Field(default="INFO", description="Logging level")
      LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
  ```
- **MIRROR**: Follow Settings pattern from `service/backend/app/core/config.py:14-80`
- **IMPORTS**: `from pydantic import Field`
- **GOTCHA**: Use port 9090 for Prometheus (not 8001) to avoid conflict with FastAPI, set TRACE_SAMPLE_RATE=0.1 in production to reduce overhead
- **VALIDATE**: Export env vars `PROMETHEUS_ENABLED=true`, `LOG_LEVEL=DEBUG`, settings load correctly

### Task 3: Create Structured Logging Middleware
- **ACTION**: Implement JSON logging with correlation ID injection
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/logging.py
  import logging
  import structlog
  import uuid
  from typing import AsyncGenerator
  from fastapi import Request
  from app.core.config import settings

  # Configure structlog
  structlog.configure(
      processors=[
          structlog.stdlib.filter_by_level,
          structlog.stdlib.add_logger_name,
          structlog.stdlib.add_log_level,
          structlog.stdlib.PositionalArgumentsFormatter(),
          structlog.processors.TimeStamper(fmt="iso"),
          structlog.processors.StackInfoRenderer(),
          structlog.processors.format_exc_info,
          structlog.processors.UnicodeDecoder(),
          structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
      ],
      context_class=dict,
      logger_factory=structlog.stdlib.LoggerFactory(),
      wrapper_class=structlog.stdlib.BoundLogger,
      cache_logger_on_first_use=True,
  )

  # Create logger
  logger = structlog.get_logger(__name__)

  class LoggingMiddleware:
      """Middleware to add request ID and structured logging."""

      async def __call__(self, request: Request, call_next) -> AsyncGenerator:
          # Generate correlation ID
          correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
          request.state.correlation_id = correlation_id

          # Bind correlation ID to logger context
          log = logger.bind(correlation_id=correlation_id)

          # Log request
          log.info(
              "request_started",
              method=request.method,
              path=request.url.path,
              client=request.client.host if request.client else None,
          )

          # Process request
          try:
              response = await call_next(request)
              log.info(
                  "request_completed",
                  status_code=response.status_code,
                  method=request.method,
                  path=request.url.path,
              )
              # Add correlation ID to response headers
              response.headers["X-Correlation-ID"] = correlation_id
              return response
          except Exception as e:
              log.error(
                  "request_failed",
                  error=str(e),
                  error_type=type(e).__name__,
                  method=request.method,
                  path=request.url.path,
              )
              raise
  ```
- **MIRROR**: Follow middleware pattern from `service/backend/app/middleware/admin.py:12-64`
- **IMPORTS**: `import structlog`, `from fastapi import Request`, `from app.core.config import settings`
- **GOTCHA**: Correlation ID must be injected into ALL log calls, use `structlog.bind()` for context propagation
- **VALIDATE**: Make request, see JSON logs with `correlation_id`, response header contains same ID

### Task 4: Create Prometheus Metrics Middleware
- **ACTION**: Expose HTTP and application metrics at `/metrics` endpoint
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/prometheus.py
  from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
  from prometheus_fastapi_instrumentator import Instrumentator
  from fastapi import FastAPI, Response
  from app.core.config import settings

  # Custom metrics
  http_requests_total = Counter(
      "http_requests_total",
      "Total HTTP requests",
      ["method", "endpoint", "status"]
  )

  http_request_duration_seconds = Histogram(
      "http_request_duration_seconds",
      "HTTP request latency",
      ["method", "endpoint"]
  )

  active_connections = Gauge(
      "active_connections",
      "Active database connections"
  )

  def setup_prometheus(app: FastAPI) -> None:
      """Configure Prometheus metrics collection."""
      if not settings.PROMETHEUS_ENABLED:
          return

      # Auto-instrument FastAPI
      instrumentator = Instrumentator(
          should_group_status_codes=False,
          should_ignore_untemplated=True,
          should_group_untemplated=True,
          should_instrument_requests_inprogress=True,
          should_instrument_requests_cancellation=True,
          excluded_handlers=["/metrics"],
          env_var_name="PROMETHEUS_MULTIPROC_DIR",
          inprogress_name="fastapi_inprogress",
          inprogress_labels=True,
      )
      instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

      # Add custom metrics endpoint (alternative to instrumentator.expose)
      @app.get("/metrics", include_in_schema=False)
      async def metrics():
          """Prometheus metrics endpoint."""
          return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
  ```
- **MIRROR**: Follow lifespan setup pattern from `service/backend/app/main.py:19-29`
- **IMPORTS**: `from prometheus_fastapi_instrumentator import Instrumentator`, `from prometheus_client import Counter, Histogram`
- **GOTCHA**: Exclude `/metrics` endpoint from instrumentation to avoid infinite recursion, use `should_group_untemplated=True` to reduce cardinality
- **VALIDATE**: Access `http://localhost:9090/metrics`, see `http_requests_total`, `http_request_duration_seconds` metrics

### Task 5: Create OpenTelemetry Tracing Middleware
- **ACTION**: Implement distributed tracing with Jaeger exporter
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/tracing.py
  from opentelemetry import trace
  from opentelemetry.sdk.trace import TracerProvider
  from opentelemetry.sdk.trace.export import BatchSpanProcessor
  from opentelemetry.exporter.jaeger.thrift import JaegerExporter
  from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
  from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
  from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
  from opentelemetry.sdk.resources import SERVICE_NAME, Resource
  from fastapi import FastAPI
  from app.core.config import settings

  def setup_tracing(app: FastAPI) -> None:
      """Configure OpenTelemetry tracing with Jaeger exporter."""
      if not settings.JAEGER_ENABLED:
          return

      # Create resource with service name
      resource = Resource(attributes={
          SERVICE_NAME: settings.APP_NAME,
          "service.version": settings.APP_VERSION,
      })

      # Configure tracer provider
      tracer_provider = TracerProvider(resource=resource)
      jaeger_exporter = JaegerExporter(
          agent_host_name=settings.JAEGER_AGENT_HOST,
          agent_port=settings.JAEGER_AGENT_PORT,
      )
      tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
      trace.set_tracer_provider(tracer_provider)

      # Auto-instrument FastAPI
      FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

      # Instrument HTTPX (for external API calls)
      HTTPXClientInstrumentor().instrument()

      # Instrument SQLAlchemy (for database queries)
      from app.core.database import engine
      SQLAlchemyInstrumentor().instrument(engine=engine)

      # Log trace setup
      import logging
      logger = logging.getLogger(__name__)
      logger.info(f"Tracing enabled: Jaeger agent at {settings.JAEGER_AGENT_HOST}:{settings.JAEGER_AGENT_PORT}")
      logger.info(f"Trace sampling rate: {settings.TRACE_SAMPLE_RATE}")
  ```
- **MIRROR**: Follow import pattern from `service/backend/app/main.py:12-16`
- **IMPORTS**: `from opentelemetry import trace`, `from opentelemetry.sdk.trace import TracerProvider`, `from app.core.config import settings`
- **GOTCHA**: Tracer provider must be set BEFORE instrumenting FastAPI, use sampling rate < 1.0 in production to reduce overhead
- **VALIDATE**: Access Jaeger UI (http://localhost:16686), make API request, see trace with FastAPI spans

### Task 6: Create Centralized Observability Setup
- **ACTION**: Create single initialization function for all observability systems
- **IMPLEMENT**:
  ```python
  # service/backend/app/core/observability.py
  from fastapi import FastAPI
  from app.middleware.prometheus import setup_prometheus
  from app.middleware.logging import LoggingMiddleware
  from app.middleware.tracing import setup_tracing
  from app.core.config import settings
  import logging

  logger = logging.getLogger(__name__)

  def setup_observability(app: FastAPI) -> None:
      """
      Initialize all observability systems.

      Order matters:
      1. Tracing (must be first to instrument all requests)
      2. Prometheus (metrics collection)
      3. Logging (structured logging with correlation)
      """
      # 1. Setup distributed tracing
      if settings.JAEGER_ENABLED:
          setup_tracing(app)
          logger.info("Jaeger tracing enabled")
      else:
          logger.info("Jaeger tracing disabled")

      # 2. Setup Prometheus metrics
      if settings.PROMETHEUS_ENABLED:
          setup_prometheus(app)
          logger.info("Prometheus metrics enabled")
      else:
          logger.info("Prometheus metrics disabled")

      # 3. Setup structured logging middleware
      if settings.LOKI_ENABLED or settings.LOG_FORMAT == "json":
          from app.middleware.logging import LoggingMiddleware
          app.middleware("http")(LoggingMiddleware())
          logger.info(f"Structured logging enabled (format={settings.LOG_FORMAT})")
      else:
          logger.info("Structured logging disabled, using default logging")

      logger.info(f"Observability initialized: tracing={settings.JAEGER_ENABLED}, metrics={settings.PROMETHEUS_ENABLED}, loki={settings.LOKI_ENABLED}")
  ```
- **MIRROR**: Follow function pattern from `service/backend/app/main.py:32-58`
- **IMPORTS**: `from app.middleware.prometheus import setup_prometheus`, `from app.core.config import settings`
- **GOTCHA**: Order is critical: tracing first, then metrics, then logging (logging middleware must wrap everything)
- **VALIDATE**: Startup logs show all observability systems initialized, `/metrics` endpoint returns data

### Task 7: Integrate Observability into FastAPI App
- **ACTION**: Update main.py to initialize observability in lifespan
- **IMPLEMENT**:
  ```python
  # service/backend/app/main.py (UPDATE)
  from contextlib import asynccontextmanager
  from typing import AsyncGenerator
  import logging

  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware

  from app.api.v1.api import api_router
  from app.core.config import settings
  from app.core.observability import setup_observability  # NEW

  logger = logging.getLogger(__name__)  # NEW

  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator:
      """
      Lifespan event handler for FastAPI application.
      Manages application startup and shutdown events.
      """
      # Startup
      logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")  # CHANGED from print
      yield
      # Shutdown
      logger.info(f"Shutting down {settings.APP_NAME}")  # CHANGED from print

  def create_application() -> FastAPI:
      """
      Create and configure the FastAPI application.

      Returns:
          FastAPI: Configured application instance
      """
      app = FastAPI(
          title=settings.APP_NAME,
          version=settings.APP_VERSION,
          description="Unified Backend Service for Test Management and Scheduling",
          lifespan=lifespan,
          docs_url="/api/docs",
          redoc_url="/api/redoc",
          openapi_url="/api/openapi.json",
      )

      # Setup observability FIRST (before CORS)  # NEW
      setup_observability(app)

      # Configure CORS
      app.add_middleware(
          CORSMiddleware,
          allow_origins=settings.CORS_ORIGINS,
          allow_credentials=True,
          allow_methods=["*"],
          allow_headers=["*"],
      )

      # ... rest of the code unchanged ...
  ```
- **MIRROR**: Follow main.py structure from `service/backend/app/main.py:19-58`
- **IMPORTS**: `from app.core.observability import setup_observability`, `import logging`
- **GOTCHA**: Call `setup_observability(app)` BEFORE adding CORS middleware (observability must wrap all requests), replace `print()` with `logger.info()`
- **VALIDATE**: Application starts without errors, logs show JSON format, `/metrics` accessible

### Task 8: Deploy Prometheus with Helm
- **ACTION**: Install Prometheus server and node_exporter
- **IMPLEMENT**:
  ```bash
  # Add Prometheus community Helm repo
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm repo update

  # Install Prometheus (includes node_exporter and kube-state-metrics)
  helm install prometheus prometheus-community/prometheus \
    --namespace observability \
    --create-namespace \
    --set server.service.type=ClusterIP \
    --set server.service.port=9090 \
    --set server.persistentVolume.enabled=true \
    --set server.persistentVolume.size=50Gi \
    --set rbac.create=true

  # Port-forward to access Prometheus UI
  kubectl port-forward -n observability svc/prometheus-server 9090:9090
  ```
- **MIRROR**: Follow deployment pattern from existing services in `service/docker-compose.yml`
- **IMPORTS**: N/A (shell commands)
- **GOTCHA**: Prometheus needs persistent storage for historical data, use ClusterIP (not LoadBalancer) for security
- **VALIDATE**: Access http://localhost:9090, see "Prometheus" UI, targets show UP status

### Task 9: Deploy Loki and Promtail
- **ACTION**: Install Loki log aggregation and Promtail log shipper
- **IMPLEMENT**:
  ```yaml
  # k8s/observability/loki-stack.yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: loki-config
    namespace: observability
  data:
    loki-config.yaml: |
      auth_enabled: false
      server:
        http_listen_port: 3100
      ingester:
        lifecycler:
          address: 127.0.0.1
          ring:
            kvstore:
              store: inmemory
            replication_factor: 1
      limits_config:
        enforce_metric_name: false
        reject_old_samples: true
        reject_old_samples_max_age: 168h
      schema_config:
        configs:
          - from: 2020-10-24
            store: boltdb-shipper
            object_store: filesystem
            schema: v11
            index:
              prefix: index_
              period: 24h
      storage_config:
        boltdb_shipper:
          active_directory: /tmp/loki/boltdb-shipper-active
          cache_location: /tmp/loki/boltdb-shipper-cache
          shared_store: filesystem
        filesystem:
          directory: /tmp/loki/chunks
      ruler:
        enable: false
  ---
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: loki
    namespace: observability
  spec:
    replicas: 1
    selector:
      matchLabels:
        app: loki
    template:
      metadata:
        labels:
          app: loki
      spec:
        containers:
        - name: loki
          image: grafana/loki:2.9.2
          args:
          - -config.file=/etc/loki/loki-config.yaml
          volumeMounts:
          - name: config
            mountPath: /etc/loki
          - name: storage
            mountPath: /tmp/loki
          ports:
          - containerPort: 3100
            name: http-metrics
            protocol: TCP
        volumes:
        - name: config
          configMap:
            name: loki-config
        - name: storage
          emptyDir: {}
  ---
  apiVersion: v1
  kind: Service
  metadata:
    name: loki
    namespace: observability
  spec:
    selector:
      app: loki
    ports:
    - port: 3100
      targetPort: 3100
      name: http
  ```
- **MIRROR**: Follow K8s deployment pattern from earlier tasks (use ConfigMaps, Services, Deployments)
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Loki uses filesystem storage (use PersistentVolume in production), retention 168h (7 days) by default
- **VALIDATE**: `kubectl get pods -n observability | grep loki`, pod Running, access http://localhost:3100/ready (returns ready)

### Task 10: Configure Promtail to Ship Logs
- **ACTION**: Deploy Promtail to send logs from pods to Loki
- **IMPLEMENT**:
  ```yaml
  # k8s/observability/promtail-config.yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: promtail-config
    namespace: observability
  data:
    promtail.yaml: |
      server:
        http_listen_port: 3101
      positions:
        filename: /tmp/positions.yaml
      clients:
        - url: http://loki:3100/loki/api/v1/push
      scrape_configs:
        - job_name: pods
          kubernetes_sd_configs:
            - role: pod
          relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_label_app
              target_label: app
            - source_labels:
              - __meta_kubernetes_pod_node_name
              target_label: node
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - replacement: /var/log/pods/*$1/*.log
              separator: /
              source_labels:
              - __meta_kubernetes_pod_uid
              - __meta_kubernetes_pod_container_name
              target_label: __path__
          pipeline_stages:
            - json:
                expressions:
                  correlation_id: correlation_id
                  level: level
                  message: message
            - labels:
                correlation_id:
                level:
  ---
  apiVersion: apps/v1
  kind: DaemonSet
  metadata:
    name: promtail
    namespace: observability
  spec:
    selector:
      matchLabels:
        app: promtail
    template:
      metadata:
        labels:
          app: promtail
      spec:
        serviceAccountName: promtail
        containers:
        - name: promtail
          image: grafana/promtail:2.9.2
          args:
          - -config.file=/etc/promtail/promtail.yaml
          volumeMounts:
          - name: config
            mountPath: /etc/promtail
          - name: varlog
            mountPath: /var/log
            readOnly: true
          - name: varlibdockercontainers
            mountPath: /var/lib/docker/containers
            readOnly: true
          env:
          - name: HOSTNAME
            valueFrom:
              fieldRef:
                fieldPath: spec.nodeName
        volumes:
        - name: config
          configMap:
            name: promtail-config
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRole
  metadata:
    name: promtail
  rules:
  - apiGroups: [""]
    resources:
    - nodes
    - nodes/proxy
    - services
    - endpoints
    - pods
    verbs: ["get", "list", "watch"]
  ---
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: promtail
    namespace: observability
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRoleBinding
  metadata:
    name: promtail
  roleRef:
    apiGroup: rbac.authorization.k8s.io
    kind: ClusterRole
    name: promtail
  subjects:
  - kind: ServiceAccount
    name: promtail
    namespace: observability
  ```
- **MIRROR**: Follow DaemonSet pattern for node-level agents
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Promtail needs RBAC permissions to access pod metadata, DaemonSet ensures one pod per node
- **VALIDATE**: `kubectl get pods -n observability | grep promtail`, logs show "Connected to Loki", Loki receives logs

### Task 11: Deploy Jaeger All-in-One
- **ACTION**: Install Jaeger for distributed tracing visualization
- **IMPLEMENT**:
  ```yaml
  # k8s/observability/jaeger-deployment.yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: jaeger
    namespace: observability
  spec:
    replicas: 1
    selector:
      matchLabels:
        app: jaeger
    template:
      metadata:
        labels:
          app: jaeger
      spec:
        containers:
        - name: jaeger
          image: jaegertracing/all-in-one:1.50
          env:
          - name: COLLECTOR_OTLP_ENABLED
            value: "true"
          ports:
          - containerPort: 5775  # accept zipkin.thrift over compact thrift protocol
            protocol: UDP
          - containerPort: 6831  # accept jaeger.thrift over compact thrift protocol
            protocol: UDP
          - containerPort: 6832  # accept jaeger.thrift over binary thrift protocol
            protocol: UDP
          - containerPort: 5778  # serve configs
            protocol: TCP
          - containerPort: 16686  # serve frontend (Jaeger UI)
            protocol: TCP
          - containerPort: 14268  # accept model.proto
            protocol: TCP
          - containerPort: 14250  # accept model.proto (gRPC)
            protocol: TCP
          - containerPort: 9411   # Zipkin compatible endpoint
            protocol: TCP
  ---
  apiVersion: v1
  kind: Service
  metadata:
    name: jaeger
    namespace: observability
  spec:
    selector:
      app: jaeger
    ports:
    - name: ui
      port: 16686
      targetPort: 16686
      protocol: TCP
    - name: collector
      port: 14268
      targetPort: 14268
      protocol: TCP
    - name: agent-compact
      port: 6831
      targetPort: 6831
      protocol: UDP
    type: ClusterIP
  ```
- **MIRROR**: Follow deployment pattern from earlier tasks
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Use `all-in-one` image for development (not production), agent port 6831 must match backend config
- **VALIDATE**: `kubectl port-forward -n observability svc/jaeger 16686:16686`, access http://localhost:16686, see Jaeger UI

### Task 12: Deploy Grafana with Dashboards
- **ACTION**: Install Grafana and configure datasources
- **IMPLEMENT**:
  ```bash
  # Add Grafana Helm repo
  helm repo add grafana https://grafana.github.io/helm-charts
  helm repo update

  # Install Grafana
  helm install grafana grafana/grafana \
    --namespace observability \
    --set persistence.enabled=true \
    --set persistence.size=10Gi \
    --set adminPassword=admin \
    --set service.type=ClusterIP \
    --set plugins="grafana-piechart-panel,grafana-worldmap-panel" \
    --set datasources."datasources.yaml".apiVersion=1 \
    --set datasources."datasources.yaml".datasources[0].name=Prometheus \
    --set datasources."datasources.yaml".datasources[0].type=prometheus \
    --set datasources."datasources.yaml".datasources[0].url=http://prometheus-server.observability.svc.cluster.local:9090 \
    --set datasources."datasources.yaml".datasources[1].name=Loki \
    --set datasources."datasources.yaml".datasources[1].type=loki \
    --set datasources."datasources.yaml".datasources[1].url=http://loki:3100 \
    --set datasources."datasources.yaml".datasources[2].name=Jaeger \
    --set datasources."datasources.yaml".datasources[2].type=jaeger \
    --set datasources."datasources.yaml".datasources[2].url=http://jaeger:16686

  # Port-forward to access Grafana
  kubectl port-forward -n observability svc/grafana 3000:80
  ```
- **MIRROR**: Follow Helm deployment pattern from Task 8
- **IMPORTS**: N/A (shell commands)
- **GOTCHA**: Change default admin password immediately, use ClusterIP (not LoadBalancer) for security
- **VALIDATE**: Access http://localhost:3000 (admin/admin), see 3 datasources (Prometheus, Loki, Jaeger) in Configuration > Datasources

### Task 13: Create Grafana Overview Dashboard
- **ACTION**: Build main system overview dashboard
- **IMPLEMENT**:
  ```json
  {
    "dashboard": {
      "title": "Claude Test Runner - Overview",
      "tags": ["claude-test-runner", "overview"],
      "timezone": "browser",
      "panels": [
        {
          "title": "Request Rate (req/s)",
          "targets": [
            {
              "expr": "rate(http_requests_total[5m])",
              "legendFormat": "{{method}} {{endpoint}}"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Error Rate (%)",
          "targets": [
            {
              "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100",
              "legendFormat": "Errors"
            }
          ],
          "type": "graph"
        },
        {
          "title": "P95 Latency (ms)",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000",
              "legendFormat": "P95"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Active Requests",
          "targets": [
            {
              "expr": "fastapi_inprogress_requests_total",
              "legendFormat": "In Progress"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Log Volume (logs/sec)",
          "targets": [
            {
              "expr": "sum(rate({job=\"pods\"}[5m]))",
              "legendFormat": "Logs/sec"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Recent Errors (Loki)",
          "targets": [
            {
              "expr": "{level=\"error\"} |= \"\"",
              "legendFormat": "{{message}}"
            }
          ],
          "type": "logs"
        }
      ]
    }
  }
  ```
- **MIRROR**: Follow dashboard JSON structure from Grafana docs
- **IMPORTS**: N/A (Grafana dashboard JSON)
- **GOTCHA**: Use `histogram_quantile` for P95/P99 latency, Loki queries use LogQL syntax (`{label="value"} |= "search"`)
- **VALIDATE**: Import dashboard in Grafana (Dashboards > Import), see panels with data, time range selector works

### Task 14: Create API Performance Dashboard
- **ACTION**: Build detailed API performance dashboard
- **IMPLEMENT**:
  ```json
  {
    "dashboard": {
      "title": "API Performance Details",
      "tags": ["claude-test-runner", "api", "performance"],
      "panels": [
        {
          "title": "Requests by Endpoint",
          "targets": [
            {
              "expr": "sum by (endpoint) (rate(http_requests_total[5m]))",
              "legendFormat": "{{endpoint}}"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Latency Distribution",
          "targets": [
            {
              "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
              "legendFormat": "P50"
            },
            {
              "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
              "legendFormat": "P95"
            },
            {
              "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
              "legendFormat": "P99"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Status Code Distribution",
          "targets": [
            {
              "expr": "sum by (status) (rate(http_requests_total[5m]))",
              "legendFormat": "{{status}}"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Slowest Endpoints (P95)",
          "targets": [
            {
              "expr": "topk(10, histogram_quantile(0.95, sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))) * 1000)",
              "legendFormat": "{{endpoint}}"
            }
          ],
          "type": "table"
        }
      ]
    }
  }
  ```
- **MIRROR**: Follow dashboard pattern from Task 13
- **IMPORTS**: N/A (Grafana dashboard JSON)
- **GOTCHA**: Use `topk()` for top-N lists, convert seconds to milliseconds for latency
- **VALIDATE**: Import dashboard, see endpoint breakdown, sort by slowest endpoints

### Task 15: Create Database Metrics Dashboard
- **ACTION**: Build database performance dashboard
- **IMPLEMENT**:
  ```json
  {
    "dashboard": {
      "title": "Database Performance",
      "tags": ["claude-test-runner", "database", "postgres"],
      "panels": [
        {
          "title": "Database Connection Pool",
          "targets": [
            {
              "expr": "active_connections",
              "legendFormat": "Active Connections"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Query Latency (ms)",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(sqlalchemy_query_duration_seconds_bucket[5m])) by (le)) * 1000",
              "legendFormat": "P95 Query Latency"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Query Rate (qps)",
          "targets": [
            {
              "expr": "sum(rate(sqlalchemy_query_duration_seconds_count[5m]))",
              "legendFormat": "Queries/sec"
            }
          ],
          "type": "graph"
        },
        {
          "title": "Slow Queries (>1s)",
          "targets": [
            {
              "expr": "sum(rate(sqlalchemy_query_duration_seconds_bucket{le=\"1.0\"}[5m]))",
              "legendFormat": "Slow Queries"
            }
          ],
          "type": "graph"
        }
      ]
    }
  }
  ```
- **MIRROR**: Follow dashboard pattern from Task 13
- **IMPORTS**: N/A (Grafana dashboard JSON)
- **GOTCHA**: SQLAlchemy metrics auto-instrumented, use `sqlalchemy_query_duration_seconds` metric name
- **VALIDATE**: Import dashboard, see connection pool metrics, query latency trends

### Task 16: Write Observability Setup Guide
- **ACTION**: Document installation and configuration steps
- **IMPLEMENT**:
  ```markdown
  # Observability Setup Guide

  ## Overview
  Claude Code Test Runner uses 4-pillar observability:
  - **Metrics**: Prometheus for time-series data
  - **Logs**: Loki for centralized log aggregation
  - **Traces**: Jaeger for distributed tracing
  - **Dashboards**: Grafana for visualization

  ## Prerequisites
  - Kubernetes cluster (v1.24+)
  - kubectl configured
  - Helm 3.x installed

  ## Installation

  ### 1. Install Observability Stack
  ```bash
  # Deploy all components
  kubectl apply -f k8s/observability/

  # Wait for pods to be ready
  kubectl wait --for=condition=ready pod -l app=prometheus -n observability --timeout=300s
  kubectl wait --for=condition=ready pod -l app=loki -n observability --timeout=300s
  kubectl wait --for=condition=ready pod -l app=jaeger -n observability --timeout=300s
  ```

  ### 2. Configure Backend Service
  Add to `service/.env`:
  ```bash
  # Enable observability
  PROMETHEUS_ENABLED=true
  JAEGER_ENABLED=true
  LOKI_ENABLED=true
  LOG_FORMAT=json

  # Jaeger agent
  JAEGER_AGENT_HOST=jaeger.observability.svc.cluster.local
  JAEGER_AGENT_PORT=6831
  TRACE_SAMPLE_RATE=0.1

  # Loki endpoint
  LOKI_ENDPOINT=http://loki:3100/loki/api/v1/push
  ```

  ### 3. Access Dashboards
  ```bash
  # Grafana
  kubectl port-forward -n observability svc/grafana 3000:80
  open http://localhost:3000

  # Prometheus
  kubectl port-forward -n observability svc/prometheus-server 9090:9090
  open http://localhost:9090

  # Jaeger
  kubectl port-forward -n observability svc/jaeger 16686:16686
  open http://localhost:16686
  ```

  ## Troubleshooting
  See `docs/observability/troubleshooting.md`
  ```
- **MIRROR**: Follow documentation style from `CLAUDE.md`
- **IMPORTS**: N/A (documentation)
- **GOTCHA**: Include port-forward commands for local access, note that Jaeger agent hostname uses K8s service DNS
- **VALIDATE**: Follow guide from scratch, all components deploy successfully

### Task 17: Write Troubleshooting Guide
- **ACTION**: Document common issues and solutions
- **IMPLEMENT**:
  ```markdown
  # Observability Troubleshooting

  ## Issue: No metrics in Prometheus
  **Symptoms**: `/metrics` endpoint returns 404, Prometheus targets show DOWN

  **Solutions**:
  1. Check if Prometheus enabled: `echo $PROMETHEUS_ENABLED`
  2. Verify middleware loaded: Check startup logs for "Prometheus metrics enabled"
  3. Check port conflicts: Ensure port 9090 not already in use
  4. Verify scrape config: `kubectl get configmap prometheus-config -n observability`

  ## Issue: Logs not appearing in Loki
  **Symptoms**: Grafana Loki datasource shows "No data"

  **Solutions**:
  1. Check Promtail logs: `kubectl logs -n observability -l app=promtail`
  2. Verify log format: Ensure `LOG_FORMAT=json` in backend .env
  3. Check Loki connection: Promtail logs should show "Connected to Loki"
  4. Verify labels: Use `{namespace="claude-test-runner"}` query in Loki

  ## Issue: No traces in Jaeger
  **Symptoms**: Jaeger UI shows "No traces"

  **Solutions**:
  1. Check if tracing enabled: `echo $JAEGER_ENABLED`
  2. Verify agent connection: Backend logs should show "Jaeger agent at jaeger:6831"
  3. Check sampling rate: Ensure `TRACE_SAMPLE_RATE > 0` (e.g., 1.0 for dev, 0.1 for prod)
  4. Make API request: Traces only appear after requests are made
  5. Check time range: Jaeger UI defaults to "Last hour", adjust if needed

  ## Issue: High memory usage in Grafana
  **Symptoms**: Grafana pod OOMKilled

  **Solutions**:
  1. Increase memory limit: `kubectl edit deployment grafana -n observability`
  2. Reduce dashboard refresh rate: Change from 5s to 30s
  3. Reduce time range in queries: Use shorter time ranges
  4. Clear cache: Grafana UI > Configuration > Users > Clear cache

  ## Issue: Correlation ID missing in logs
  **Symptoms**: Logs don't have `correlation_id` field

  **Solutions**:
  1. Verify logging middleware loaded: Check startup logs for "Structured logging enabled"
  2. Check middleware order: `setup_observability()` must be called before `app.add_middleware(CORSMiddleware)`
  3. Test manually: Make request with `curl -H "X-Correlation-ID: test-123" http://localhost:8001/api/v1/health`
  ```
- **MIRROR**: Follow troubleshooting format from runbooks
- **IMPORTS**: N/A (documentation)
- **GOTCHA**: Include kubectl commands for verification, link to Task 16 setup guide
- **VALIDATE**: Follow each troubleshooting step, commands work as documented

### Task 18: Verify End-to-End Observability
- **ACTION**: Integration test of all observability systems
- **IMPLEMENT**:
  ```bash
  #!/bin/bash
  # test-observability.sh

  echo "=== Observability Integration Test ==="

  # 1. Test Prometheus metrics
  echo "Testing Prometheus metrics..."
  response=$(curl -s http://localhost:8001/metrics)
  if echo "$response" | grep -q "http_requests_total"; then
      echo "✓ Prometheus metrics accessible"
  else
      echo "✗ Prometheus metrics not found"
      exit 1
  fi

  # 2. Test structured logging
  echo "Testing structured logging..."
  response=$(curl -s -H "X-Correlation-ID: test-123" http://localhost:8001/health)
  if [ $? -eq 0 ]; then
      echo "✓ Request successful"
      # Check logs for correlation_id
      sleep 2
      logs=$(kubectl logs -n claude-test-runner -l app=backend --tail=10)
      if echo "$logs" | grep -q "correlation_id"; then
          echo "✓ Structured logs with correlation_id"
      else
          echo "✗ Correlation ID not found in logs"
      fi
  fi

  # 3. Test Jaeger tracing
  echo "Testing Jaeger tracing..."
  # Make a request to generate a trace
  curl -s http://localhost:8001/api/v1/schedules > /dev/null
  sleep 2
  # Check Jaeger API for traces
  traces=$(curl -s "http://localhost:16686/api/traces?service=claude-test-runner")
  if echo "$traces" | grep -q "traceID"; then
      echo "✓ Traces found in Jaeger"
  else
      echo "⚠ No traces found (may need more requests or higher sampling rate)"
  fi

  # 4. Test Loki logs
  echo "Testing Loki log aggregation..."
  logs=$(curl -s "http://localhost:3100/loki/api/v1/query" \
    --data-urlencode 'query={app="backend"}' \
    --data-urlencode 'limit=10')
  if echo "$logs" | grep -q "streams"; then
      echo "✓ Logs found in Loki"
  else
      echo "✗ No logs found in Loki"
  fi

  # 5. Test Grafana dashboards
  echo "Testing Grafana datasources..."
  prometheus_status=$(curl -s "http://admin:admin@localhost:3000/api/datasources" | jq '.[] | select(.name=="Prometheus") | .status')
  if [ "$prometheus_status" == "\"OK\"" ]; then
      echo "✓ Prometheus datasource OK"
  else
      echo "✗ Prometheus datasource not OK"
  fi

  loki_status=$(curl -s "http://admin:admin@localhost:3000/api/datasources" | jq '.[] | select(.name=="Loki") | .status')
  if [ "$loki_status" == "\"OK\"" ]; then
      echo "✓ Loki datasource OK"
  else
      echo "✗ Loki datasource not OK"
  fi

  echo "=== Observability Test Complete ==="
  ```
- **MIRROR**: Follow test script pattern from existing `test-*.js` files
- **IMPORTS**: N/A (shell script)
- **GOTCHA**: Jaeger traces may not appear immediately (need 2-3 requests), Loki logs take 10-30s to index
- **VALIDATE**: Run script, all checks pass, see output showing ✓ marks

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| Prometheus middleware | HTTP GET /metrics | 200 OK, Prometheus format | Metrics endpoint excluded from instrumentation |
| Logging middleware | Request with X-Correlation-ID | Logs with correlation_id | Missing header generates new UUID |
| Tracing middleware | API request | Trace ID in Jaeger | Sampling rate affects trace visibility |
| Structured logging | Log with dict | JSON formatted log | Non-serializable objects handled |

### Integration Tests

| Test | Scenario | Expected Result |
|---|---|---|
| End-to-end observability | Make API request, check all systems | Metrics in Prometheus, logs in Loki, trace in Jaeger |
| Correlation ID propagation | Multi-service request | Same correlation_id in all logs |
| Dashboard queries | Query Grafana dashboards | All panels show data |
| High-traffic scenario | 100 req/s for 60 seconds | No data loss, sampling works |

### Edge Cases Checklist
- [ ] Prometheus endpoint blocked by authentication
- [ ] Loki storage full (retention policy)
- [ ] Jaeger agent unreachable (fallback behavior)
- [ ] High sampling rate causing overhead
- [ ] Log injection attacks (malicious input in logs)
- [ ] Time series cardinality explosion (high label cardinality)
- [ ] Missing correlation ID header
- [ ] Grafana datasource connection failures
- [ ] Structlog serialization errors
- [ ] Tracer provider not initialized

---

## Validation Commands

### Backend Validation
```bash
# Check if observability is enabled
curl http://localhost:8001/metrics | grep http_requests_total
EXPECT: Prometheus metrics output

# Test structured logging
curl -H "X-Correlation-ID: test-123" http://localhost:8001/health
kubectl logs -n claude-test-runner -l app=backend --tail=1 | jq
EXPECT: JSON log with correlation_id field

# Verify tracing
curl http://localhost:8001/api/v1/schedules
curl http://localhost:16686/api/traces?service=claude-test-runner | jq '.data[0].traceID'
EXPECT: Trace ID returned (not empty)
```

### Observability Stack Validation
```bash
# Check Prometheus targets
kubectl port-forward -n observability svc/prometheus-server 9090:9090
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
EXPECT: All targets show "up"

# Check Loki logs
kubectl logs -n observability -l app=loki --tail=10
EXPECT: No errors, "Loki started" message

# Check Jaeger
kubectl port-forward -n observability svc/jaeger 16686:16686
curl http://localhost:16686/api/services | jq '.data[] | .serviceName'
EXPECT: "claude-test-runner" in list

# Check Grafana datasources
kubectl port-forward -n observability svc/grafana 3000:80
curl -s "http://admin:admin@localhost:3000/api/datasources" | jq '.[] | {name: .name, status: .status}'
EXPECT: All datasources show "OK"
```

### Integration Validation
```bash
# Run integration test script
chmod +x test-observability.sh
./test-observability.sh
EXPECT: All checks pass (✓ marks)

# Test correlation ID propagation
CORRELATION_ID=$(uuidgen)
curl -H "X-Correlation-ID: $CORRELATION_ID" http://localhost:8001/api/v1/schedules
sleep 2
kubectl logs -n claude-test-runner -l app=backend --tail=5 | jq "select(.correlation_id == \"$CORRELATION_ID\")"
EXPECT: Logs with matching correlation_id

# Test trace query in Jaeger
curl http://localhost:8001/api/v1/schedules
sleep 2
curl -s "http://localhost:16686/api/traces?service=claude-test-runner&limit=1" | jq '.data[0].traceID'
EXPECT: Valid trace ID (32-char hex string)
```

### Dashboard Validation
```bash
# Import dashboards to Grafana
for dashboard in grafana/dashboards/*.json; do
  curl -X POST \
    -H "Content-Type: application/json" \
    -d @"$dashboard" \
    "http://admin:admin@localhost:3000/api/dashboards/import"
done
EXPECT: Dashboard IDs returned, status 200

# Query dashboard data
curl "http://localhost:3000/api/dashboards/uid/overview" | jq '.dashboard.title'
EXPECT: "Claude Test Runner - Overview"

# Verify panel queries
curl "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up" | jq '.data.result[] | .metric.job'
EXPECT: Prometheus targets visible
```

### Manual Validation
- [ ] Access Grafana at http://localhost:3000, login with admin/admin
- [ ] Change Grafana admin password
- [ ] Verify all 3 datasources (Prometheus, Loki, Jaeger) are green/OK
- [ ] Open "Overview" dashboard, see real-time data
- [ ] Make API request, see trace in Jaeger UI
- [ ] Search logs in Loki by correlation_id
- [ ] Create test alert in Grafana, verify delivery
- [ ] Check time series cardinality in Prometheus (should be <100k)
- [ ] Verify log rotation in Loki (7-day retention)
- [ ] Test dashboard refresh rates (5s, 30s, 1m)

---

## Acceptance Criteria
- [ ] All 18 tasks completed
- [ ] Prometheus metrics accessible at `/metrics` endpoint
- [ ] Structured JSON logs with correlation_id
- [ ] Traces visible in Jaeger UI
- [ ] Logs searchable in Loki
- [ ] Grafana dashboards showing real-time data
- [ ] All datasources configured and healthy
- [ ] Integration test script passes all checks
- [ ] Documentation complete (setup + troubleshooting)
- [ ] No hardcoded values in middleware code
- [ ] Sampling rate configurable via environment variable
- [ ] Log level configurable via environment variable
- [ ] Observability can be disabled individually (metrics, traces, logs)
- [ ] No breaking changes to existing API endpoints
- [ ] Performance overhead <5% (CPU, memory)

## Completion Checklist
- [ ] Code follows discovered patterns (middleware, logging, config)
- [ ] Error handling matches codebase style
- [ ] Logging follows JSON format for Loki
- [ ] Metrics use Prometheus best practices (label cardinality)
- [ ] Tracing follows OpenTelemetry standards
- [ ] No hardcoded credentials or endpoints
- [ ] Documentation includes setup, troubleshooting, and validation
- [ ] Dashboards cover all 4 signals (latency, traffic, errors, saturation)
- [ ] Integration tests validate end-to-end observability
- [ ] Manual testing checklist completed

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **High metrics cardinality** | Medium | High | Use low sampling rate (0.1), avoid high-cardinality labels (user_id, request_id) |
| **Observability overhead** | Low | Medium | Configurable sampling, disable in hot path if needed |
| **Loki storage full** | Low | Medium | Set retention policy (7 days), monitor disk usage |
| **Jaeger agent unreachable** | Medium | Low | Graceful degradation, logging fallback |
| **Grafana performance** | Low | Medium | Limit dashboard refresh rate, use time range limits |
| **Missing correlation IDs** | Low | High | Always generate UUID if header missing, log warnings |
| **Prometheus scraping fails** | Low | High | Health check on `/metrics`, alert on scrape failures |
| **Tracing breaks existing code** | Low | High | Use non-breaking middleware pattern, feature flags |

## Notes

### Observability Signal Levels

**Metrics (Prometheus)**:
- RED: Latency (P95, P99)
- RED: Errors (5xx rate, error percentage)
- RED: Saturation (CPU, memory, connection pool)
- YELLOW: Traffic (request rate, active connections)

**Logs (Loki)**:
- ERROR: Application errors, exceptions
- WARN: Deprecation warnings, retries
- INFO: Request lifecycle, state changes
- DEBUG: Detailed execution flow (development only)

**Traces (Jaeger)**:
- All requests sampled at 10% (configurable)
- 100% sampling for error requests
- Span includes: HTTP method, path, status, duration

**Dashboards (Grafana)**:
- Overview: High-level system health
- API Performance: Endpoint-level metrics
- Database Performance: Query latency, connection pool

### Performance Considerations

**Sampling Rates**:
- Development: `TRACE_SAMPLE_RATE=1.0` (100%)
- Staging: `TRACE_SAMPLE_RATE=0.5` (50%)
- Production: `TRACE_SAMPLE_RATE=0.1` (10%)

**Log Levels**:
- Development: `LOG_LEVEL=DEBUG`
- Staging: `LOG_LEVEL=INFO`
- Production: `LOG_LEVEL=WARN`

**Metrics Collection**:
- Scrape interval: 15 seconds (Prometheus default)
- Retention: 15 days (Prometheus default)
- Cardinality limit: <100k unique time series

### Cost Implications

**Storage Requirements** (for 100 RPS backend):
- Prometheus: 50GB/month (15-day retention)
- Loki: 20GB/month (7-day log retention)
- Jaeger: 30GB/month (7-day trace retention)
- **Total**: ~100GB/month

**Compute Resources**:
- Prometheus: 2 CPU, 4GB RAM
- Loki: 1 CPU, 2GB RAM
- Jaeger: 1 CPU, 2GB RAM
- Grafana: 0.5 CPU, 1GB RAM
- **Total**: 4.5 CPU, 9GB RAM

### Future Enhancements

**Phase 2** (NOT in scope):
- Alerting rules (Prometheus AlertManager)
- Metrics-based auto-scaling (KEDA)
- Log-based alerting (Loki ruler)
- Synthetic monitoring (Blackbox exporter)
- APM dashboards (business metrics)
- SLI/SLO tracking (SLO-based alerting)

**Tools to Consider**:
- AlertManager: Alert routing and de-duplication
- KEDA: Kubernetes Event-driven Autoscaling
- Pyroscope: Continuous profiling
- Phantom: Panic monitoring and alerting
