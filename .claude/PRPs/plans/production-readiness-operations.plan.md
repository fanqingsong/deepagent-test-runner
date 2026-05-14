# Plan: Production Readiness - Operations Capabilities

## Summary
Add comprehensive production operations capabilities including monitoring, logging, security, backup/restore, disaster recovery, CI/CD automation, and deployment orchestration for the Claude Code Test Runner microservices architecture.

## User Story
As a **DevOps engineer**, I want **production-ready operations capabilities**, so that **the system can be safely deployed, monitored, maintained, and recovered in production environments**.

## Problem → Solution
**Current State**: Development-focused Docker Compose setup with basic health checks, no centralized logging/monitoring, no automated backups, no secrets management, no SSL/TLS, no disaster recovery plan, and manual deployment processes.

**Desired State**: Production-ready Kubernetes deployment with comprehensive observability (logging, metrics, tracing), automated backups, secrets management, SSL/TLS termination, CI/CD automation, disaster recovery procedures, and operational runbooks.

## Metadata
- **Complexity**: XL (Cross-cutting infrastructure changes, multiple new systems)
- **Source PRD**: N/A (standalone operations readiness plan)
- **PRD Phase**: N/A
- **Estimated Files**: 35+ files (K8s manifests, monitoring configs, CI/CD workflows, runbooks)

---

## UX Design

### Before
```
┌──────────────────────────────────────────────────────┐
│  Manual docker-compose up                           │
│  No visibility into system health                    │
│  No alerts on failures                               │
│  No backup automation                                │
│  Secrets in .env files (plaintext)                   │
│  HTTP only (no SSL)                                  │
│  Manual deployment                                   │
│  No disaster recovery                                │
└──────────────────────────────────────────────────────┘
```

### After
```
┌─────────────────────────────────────────────────────────────┐
│  Automated GitOps deployment (ArgoCD/Flux)                  │
│  Real-time dashboards (Grafana)                             │
│  Centralized logging (Loki/ELK)                             │
│  Alerting (Prometheus AlertManager → PagerDuty/Slack)       │
│  Automated daily backups with retention policies            │
│  Secrets encryption (Vault/K8s Secrets)                     │
│  SSL/TLS termination (cert-manager/Let's Encrypt)           │
│  CI/CD pipeline (GitHub Actions → Container Registry)       │
│  Disaster recovery runbooks & automated failover            │
│  Health checks & auto-healing                               │
│  Resource limits & auto-scaling                             │
└─────────────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Deployment | Manual `docker-compose up -d` | `git push` → CI/CD → ArgoCD sync | Zero-downtime rolling updates |
| Monitoring | Check logs with `docker logs` | Grafana dashboards with metrics | Historical data and trends |
| Alerts | None (reactive) | Prometheus alerts to Slack/PagerDuty | Proactive issue detection |
| Backups | Manual `pg_dump` when remembered | Automated daily backups + 30-day retention | Scheduled and tested restores |
| Secrets | `.env` files in git (unsafe) | Kubernetes Secrets / Vault | Encrypted at rest |
| SSL | HTTP only | TLS 1.3 with auto-renewal | Let's Encrypt or corporate PKI |
| Troubleshooting | SSH into containers, grep logs | Centralized logging with correlation IDs | Distributed tracing |
| Disaster Recovery | No documented procedure | Runbooks + automated failover | RTO/RPO defined |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 (critical) | `service/docker-compose.yml` | 1-299 | Current service architecture and dependencies |
| P0 (critical) | `service/backend/app/core/config.py` | 1-80 | Environment variable configuration pattern |
| P0 (critical) | `service/nginx/nginx.conf` | 1-225 | Current routing and proxy configuration |
| P1 (important) | `.github/workflows/build-and-publish.yml` | 1-52 | Existing CI/CD foundation |
| P1 (important) | `service/backend/app/main.py` | 19-100 | Application structure and health endpoints |
| P2 (reference) | `service/.env.example` | 1-41 | Configuration requirements |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| Kubernetes Best Practices | Kubernetes.io | Use resource limits, liveness/readiness probes, PodDisruptionBudgets |
| Prometheus Monitoring | Prometheus.io | Expose `/metrics` endpoint, use 4 signal types (counter, gauge, histogram, summary) |
| GitOps Patterns | OpenGitOps.io | Declarative config, versioned, pulled automatically, continuously reconciled |
| SSL/TLS with cert-manager | cert-manager.io | Automatic certificate issuance and renewal from Let's Encrypt |
| Loki Logging Architecture | Grafana Loki | Horizontally scalable, label-based log aggregation |
| Disaster Recovery Planning | AWS/Google Cloud Best Practices | Define RTO/RPO, backup strategies, failover testing |

---

## Patterns to Mirror

### ENVIRONMENT_CONFIGURATION
// SOURCE: `service/backend/app/core/config.py:14-80`
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    SECRET_KEY: str = Field(default="changeme-in-production")
```
**Pattern**: Use pydantic-settings for environment-based configuration with type validation

### HEALTH_CHECK_ENDPOINTS
// SOURCE: `service/backend/app/main.py:96-99`
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```
**Pattern**: Simple `/health` endpoint for Kubernetes liveness/readiness probes

### SERVICE_DEPENDENCIES
// SOURCE: `service/docker-compose.yml:102-109`
```yaml
depends_on:
  postgres:
    condition: service_healthy
  redis:
    condition: service_healthy
```
**Pattern**: Services wait for dependencies to be healthy before starting

### LOGGING_CONFIG
// SOURCE: `service/nginx/nginx.conf:19-22`
```nginx
log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                '$status $body_bytes_sent "$http_referer" '
                '"$http_user_agent" "$http_x_forwarded_for"';
access_log /var/log/nginx/access.log main;
```
**Pattern**: Structured logging with standard fields for parsing

### CORS_CONFIGURATION
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
**Pattern**: Configurable CORS origins via environment variables

---

## Files to Change

### Kubernetes Deployment (8 files)
| File | Action | Justification |
|---|---|---|---|
| `k8s/base/namespace.yaml` | CREATE | Kubernetes namespace for isolation |
| `k8s/base/configmap.yaml` | CREATE | Non-sensitive configuration (CORS origins, URLs) |
| `k8s/base/secrets.yaml` | CREATE | Secret template (encrypted with Sealed Secrets/Vault) |
| `k8s/base/postgres-statefulset.yaml` | CREATE | PostgreSQL with persistent volumes |
| `k8s/base/redis-deployment.yaml` | CREATE | Redis with persistence |
| `k8s/base/backend-deployment.yaml` | CREATE | FastAPI backend with HPA |
| `k8s/base/frontend-deployment.yaml` | CREATE | React frontend with HPA |
| `k8s/base/nginx-ingress.yaml` | CREATE | Ingress controller for routing |

### Monitoring Stack (7 files)
| File | Action | Justification |
|---|---|---|---|
| `k8s/monitoring/prometheus-config.yaml` | CREATE | Prometheus configuration with scrape targets |
| `k8s/monitoring/prometheus-deployment.yaml` | CREATE | Prometheus server deployment |
| `k8s/monitoring/grafana-config.yaml` | CREATE | Grafana datasource and dashboard provisioning |
| `k8s/monitoring/grafana-deployment.yaml` | CREATE | Grafana visualization layer |
| `k8s/monitoring/alertmanager-config.yaml` | CREATE | Alert routing (Slack, PagerDuty, email) |
| `k8s/monitoring/kube-state-metrics.yaml` | CREATE | Kubernetes cluster metrics |
| `k8s/monitoring/node-exporter.yaml` | CREATE | Host-level metrics |

### Logging Stack (5 files)
| File | Action | Justification |
|---|---|---|---|
| `k8s/logging/loki-stack.yaml` | CREATE | Loki log aggregation |
| `k8s/logging/promtail-config.yaml` | CREATE | Log shipping from pods |
| `k8s/logging/fluentd-daemonset.yaml` | CREATE | Alternative: Fluentd log collection |
| `k8s/logging/elasticsearch.yaml` | CREATE | Alternative: ELK stack (if needed) |
| `k8s/logging/kibana.yaml` | CREATE | Alternative: Kibana UI for ELK |

### Observability Instrumentation (3 files)
| File | Action | Justification |
|---|---|---|---|
| `service/backend/app/middleware/prometheus.py` | CREATE | Prometheus metrics middleware |
| `service/backend/app/middleware/logging.py` | CREATE | Structured logging middleware |
| `service/backend/app/middleware/tracing.py` | CREATE | OpenTelemetry distributed tracing |

### SSL/TLS & Security (4 files)
| File | Action | Justification |
|---|---|---|---|
| `k8s/base/cert-manager.yaml` | CREATE | cert-manager for Let's Encrypt |
| `k8s/base/certificate-issuer.yaml` | CREATE | ClusterIssuer for SSL certificates |
| `k8s/base/certificate.yaml` | CREATE | Certificate resource for domain |
| `k8s/network-policies.yaml` | CREATE | Network policies for service isolation |

### Backup & Disaster Recovery (5 files)
| File | Action | Justification |
|---|---|---|---|
| `scripts/backup/postgres-backup.sh` | CREATE | Automated PostgreSQL backup script |
| `scripts/backup/redis-backup.sh` | CREATE | Automated Redis backup script |
| `scripts/backup/restore-postgres.sh` | CREATE | PostgreSQL restore procedure |
| `k8s/cronjobs/backup-cronjob.yaml` | CREATE | Scheduled backup CronJob |
| `docs/runbooks/disaster-recovery.md` | CREATE | Disaster recovery procedures |

### CI/CD Automation (4 files)
| File | Action | Justification |
|---|---|---|---|
| `.github/workflows/build-test-push.yml` | UPDATE | Add security scanning, vulnerability checks |
| `.github/workflows/deploy-staging.yml` | CREATE | Automated staging deployment |
| `.github/workflows/deploy-production.yml` | CREATE | Production deployment with approval gates |
| `argocd/application.yaml` | CREATE | GitOps application manifest |

### Helm Charts (optional, 6 files)
| File | Action | Justification |
|---|---|---|---|
| `helm/claude-test-runner/Chart.yaml` | CREATE | Helm chart metadata |
| `helm/claude-test-runner/values.yaml` | CREATE | Default configuration values |
| `helm/claude-test-runner/templates/*.yaml` | CREATE | Kubernetes resource templates |
| `helm/claude-test-runner/.helmignore` | CREATE | Helm ignore patterns |
| `helm/claude-test-runner/README.md` | CREATE | Helm chart usage documentation |
| `helm/claude-test-runner/templates/NOTES.txt` | CREATE | Post-install notes |

### Documentation & Runbooks (4 files)
| File | Action | Justification |
|---|---|---|---|
| `docs/operations/deployment-guide.md` | CREATE | Step-by-step deployment instructions |
| `docs/operations/runbooks/` | CREATE | Directory for troubleshooting runbooks |
| `docs/operations/slos-slas.md` | CREATE | Service level objectives and agreements |
| `docs/operations/onboarding.md` | CREATE | Operations team onboarding guide |

### Configuration Updates (3 files)
| File | Action | Justification |
|---|---|---|---|
| `service/backend/Dockerfile` | UPDATE | Add non-root user, health check |
| `service/backend/requirements.txt` | UPDATE | Add monitoring dependencies |
| `service/.env.production` | CREATE | Production environment template |

## NOT Building

- Multi-region deployment (single region initially)
- Advanced threat detection (basic security scanning only)
- Custom service mesh (basic K8s networking initially)
- Real-time canary deployments (basic rolling updates only)
- Advanced chaos engineering practices
- Auto-scaling based on custom metrics (CPU/memory-based initially)
- GPU worker nodes (unless specifically needed for Playwright)
- External secrets management integration (AWS Secrets Manager, Azure Key Vault) - use K8s Secrets + Sealed Secrets initially

---

## Step-by-Step Tasks

### Task 1: Add Prometheus Metrics Middleware
- **ACTION**: Create Prometheus instrumentation for FastAPI backend
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/prometheus.py
  from prometheus_fastapi_instrumentator import Instrumentator
  from fastapi import FastAPI

  def setup_prometheus(app: FastAPI) -> None:
      """Expose Prometheus metrics at /metrics endpoint."""
      instrumentator = Instrumentator()
      instrumentator.instrument(app).expose(app, endpoint="/metrics")
  ```
- **MIRROR**: Follow pattern from `service/backend/app/main.py:32-58` (middleware setup)
- **IMPORTS**: `pip install prometheus-fastapi-instrumentator`
- **GOTCHA**: Metrics endpoint must be on a separate port or protected with authentication to prevent abuse
- **VALIDATE**: Access `/metrics` endpoint, see `http_requests_total`, `http_request_duration_seconds` metrics

### Task 2: Add Structured Logging Middleware
- **ACTION**: Implement JSON-structured logging with correlation IDs
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/logging.py
  import logging
  import uuid
  from fastapi import Request
  import json_log_formatter

  formatter = json_log_formatter.JSONFormatter()
  handler = logging.StreamHandler()
  handler.setFormatter(formatter)

  class LoggingMiddleware:
      async def __call__(self, request: Request, call_next):
          correlation_id = str(uuid.uuid4())
          request.state.correlation_id = correlation_id
          # Log request with correlation_id
          response = await call_next(request)
          # Log response with correlation_id
          return response
  ```
- **MIRROR**: Follow nginx logging pattern from `service/nginx/nginx.conf:19-22`
- **IMPORTS**: `pip install json-log-formatter python-json-logger`
- **GOTCHA**: Ensure correlation ID is propagated to downstream services via headers
- **VALIDATE**: Check logs show JSON format with `correlation_id` field

### Task 3: Create Kubernetes Namespace and Resource Quotas
- **ACTION**: Define namespace with resource limits
- **IMPLEMENT**:
  ```yaml
  # k8s/base/namespace.yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: claude-test-runner
  ---
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-quota
    namespace: claude-test-runner
  spec:
    hard:
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
  ```
- **MIRROR**: Follow service dependencies pattern from `service/docker-compose.yml:102-109`
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Resource quotas must be set before deploying workloads to the namespace
- **VALIDATE**: `kubectl describe namespace claude-test-runner` shows resource quotas

### Task 4: Create PostgreSQL StatefulSet with Persistent Volumes
- **ACTION**: Deploy PostgreSQL with persistent storage and backup
- **IMPLEMENT**:
  ```yaml
  # k8s/base/postgres-statefulset.yaml
  apiVersion: apps/v1
  kind: StatefulSet
  metadata:
    name: postgres
  spec:
    serviceName: postgres
    replicas: 1
    template:
      spec:
        containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
          - containerPort: 5432
          env:
          - name: POSTGRES_DB
            valueFrom:
              secretKeyRef:
                name: postgres-secret
                key: database
          volumeMounts:
          - name: postgres-data
            mountPath: /var/lib/postgresql/data
          livenessProbe:
            exec:
              command:
              - pg_isready
              - -U
              - $(POSTGRES_USER)
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
              - pg_isready
              - -U
              - $(POSTGRES_USER)
            initialDelaySeconds: 5
            periodSeconds: 5
    volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
  ```
- **MIRROR**: Follow postgres config from `service/docker-compose.yml:2-22`
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Use StatefulSet (not Deployment) for databases to ensure stable network identity and persistent storage
- **VALIDATE**: `kubectl get statefulset postgres` shows 1/1 ready, data persists across pod restarts

### Task 5: Create Backend Deployment with Health Probes
- **ACTION**: Deploy FastAPI backend with liveness/readiness probes
- **IMPLEMENT**:
  ```yaml
  # k8s/base/backend-deployment.yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: backend
  spec:
    replicas: 2
    selector:
      matchLabels:
        app: backend
    template:
      metadata:
        labels:
          app: backend
      spec:
        containers:
        - name: backend
          image: ghcr.io/your-org/backend:latest
          ports:
          - containerPort: 8001
          env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: backend-secret
                key: database-url
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 5
  ```
- **MIRROR**: Follow backend service config from `service/docker-compose.yml:60-109`
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Readiness probe must check dependencies (database, redis), liveness probe only checks if app is alive
- **VALIDATE**: `kubectl get pods -l app=backend` shows pods in Ready state, `kubectl describe pod` shows probe successes

### Task 6: Deploy Prometheus and Grafana
- **ACTION**: Install monitoring stack with Helm charts
- **IMPLEMENT**:
  ```bash
  # Add Helm repositories
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm repo add grafana https://grafana.github.io/helm-charts
  helm repo update

  # Install Prometheus
  helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --set grafana.adminPassword=admin \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

  # Create ConfigMap for custom scrape configs
  kubectl apply -f k8s/monitoring/prometheus-config.yaml
  ```
- **MIRROR**: Follow service dependencies from `service/docker-compose.yml`
- **IMPORTS**: `helm` CLI tool
- **GOTCHA**: Grafana default password must be changed on first login, store in Secret
- **VALIDATE**: Access Grafana at `localhost:3000` (port-forward), see data sources connected, dashboards populated

### Task 7: Create Backup CronJob
- **ACTION**: Schedule automated PostgreSQL backups
- **IMPLEMENT**:
  ```yaml
  # k8s/cronjobs/backup-cronjob.yaml
  apiVersion: batch/v1
  kind: CronJob
  metadata:
    name: postgres-backup
  spec:
    schedule: "0 2 * * *"  # 2 AM daily
    jobTemplate:
      spec:
        template:
          spec:
            containers:
            - name: backup
              image: postgres:15-alpine
              command:
              - /scripts/backup.sh
              env:
              - name: POSTGRES_HOST
                value: postgres
              - name: POSTGRES_PASSWORD
                valueFrom:
                  secretKeyRef:
                    name: postgres-secret
                    key: password
              volumeMounts:
              - name: backup-script
                mountPath: /scripts
              - name: backup-storage
                mountPath: /backups
            volumes:
            - name: backup-script
              configMap:
                name: backup-script
            - name: backup-storage
              persistentVolumeClaim:
                claimName: backup-pvc
            restartPolicy: OnFailure
  ```
- **MIRROR**: Follow backup pattern from manual `pg_dump` procedures
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Backup storage must use PersistentVolume with sufficient capacity, implement retention policy (e.g., 30 days)
- **VALIDATE**: `kubectl get cronjobs` shows schedule, `kubectl get jobs --sort-by=.metadata.creationTimestamp` shows successful backups

### Task 8: Setup SSL/TLS with cert-manager
- **ACTION**: Configure automatic certificate issuance
- **IMPLEMENT**:
  ```yaml
  # k8s/base/certificate-issuer.yaml
  apiVersion: cert-manager.io/v1
  kind: ClusterIssuer
  metadata:
    name: letsencrypt-prod
  spec:
    acme:
      server: https://acme-v02.api.letsencrypt.org/directory
      email: admin@yourdomain.com
      privateKeySecretRef:
        name: letsencrypt-prod
      solvers:
      - http01:
          ingress:
            class: nginx
  ---
  apiVersion: cert-manager.io/v1
  kind: Certificate
  metadata:
    name: claude-test-runner-cert
    namespace: claude-test-runner
  spec:
    secretName: tls-cert
    issuerRef:
      name: letsencrypt-prod
      kind: ClusterIssuer
    commonName: test-runner.yourdomain.com
    dnsNames:
    - test-runner.yourdomain.com
    - api.test-runner.yourdomain.com
  ```
- **MIRROR**: Follow nginx ingress pattern from `service/nginx/nginx.conf:58-70`
- **IMPORTS**: N/A (Kubernetes manifest, cert-manager CRDs)
- **GOTCHA**: DNS must already point to ingress controller IP, Let's Encrypt has rate limits (50 certs/week per domain)
- **VALIDATE**: `kubectl get certificate` shows Ready status, TLS handshake succeeds

### Task 9: Create Ingress Controller with TLS
- **ACTION**: Expose services via Ingress with SSL termination
- **IMPLEMENT**:
  ```yaml
  # k8s/base/nginx-ingress.yaml
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: claude-test-runner-ingress
    namespace: claude-test-runner
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
      nginx.ingress.kubernetes.io/ssl-redirect: "true"
  spec:
    ingressClassName: nginx
    tls:
    - hosts:
      - test-runner.yourdomain.com
      secretName: tls-cert
    rules:
    - host: test-runner.yourdomain.com
      http:
        paths:
        - path: /api
          pathType: Prefix
          backend:
            service:
              name: backend
              port:
                number: 8001
        - path: /
          pathType: Prefix
          backend:
            service:
              name: frontend
              port:
                number: 80
  ```
- **MIRROR**: Follow nginx routing rules from `service/nginx/nginx.conf:58-223`
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Ingress controller must be installed separately (nginx-ingress-controller via Helm)
- **VALIDATE**: Access https://test-runner.yourdomain.com, browser shows valid TLS certificate

### Task 10: Update CI/CD Pipeline with Security Scanning
- **ACTION**: Add vulnerability scanning to GitHub Actions workflow
- **IMPLEMENT**:
  ```yaml
  # .github/workflows/build-test-push.yml
  - name: Run Trivy vulnerability scanner
    uses: aquasecurity/trivy-action@master
    with:
      image-ref: ${{ steps.meta.outputs.tags }}
      format: 'sarif'
      output: 'trivy-results.sarif'

  - name: Upload Trivy results to GitHub Security
    uses: github/codeql-action/upload-sarif@v2
    with:
      sarif_file: 'trivy-results.sarif'

  - name: Run Grype vulnerability scanner
    uses: anchore/scan-action@v3
    with:
      image: ${{ steps.meta.outputs.tags }}

  - name: Deploy to staging
    if: github.ref == 'refs/heads/main'
    run: |
      kubectl set image deployment/backend backend=${{ steps.meta.outputs.tags }} -n claude-test-runner-staging
      kubectl rollout status deployment/backend -n claude-test-runner-staging
  ```
- **MIRROR**: Extend existing `build-and-publish.yml` workflow
- **IMPORTS**: GitHub Actions syntax
- **GOTCHA**: Security scans must pass before deployment, set appropriate severity thresholds
- **VALIDATE**: GitHub Security tab shows vulnerability scan results, deployment succeeds on main branch push

### Task 11: Create Disaster Recovery Runbook
- **ACTION**: Document step-by-step recovery procedures
- **IMPLEMENT**:
  ```markdown
  # docs/runbooks/disaster-recovery.md

  ## Recovery Time Objective (RTO): 4 hours
  ## Recovery Point Objective (RPO): 24 hours (daily backups)

  ### Scenario 1: PostgreSQL Database Corruption
  1. Identify corruption: `kubectl logs postgres-0`
  2. Stop affected pod: `kubectl scale statefulset postgres --replicas=0`
  3. Restore from latest backup:
     ```bash
  kubectl exec -it postgres-backup-xxxxx -- /scripts/restore-postgres.sh
  ```
  4. Verify data integrity
  5. Restart postgres: `kubectl scale statefulset postgres --replicas=1`

  ### Scenario 2: Complete Cluster Failure
  1. Provision new Kubernetes cluster
  2. Restore PVCs from backup storage (S3/GCS/Azure Blob)
  3. Re-apply all manifests: `kubectl apply -f k8s/base/`
  4. Verify health: `kubectl get pods -n claude-test-runner`
  5. Run smoke tests against staging environment
  6. Update DNS to point to new cluster
  7. Monitor metrics and logs for anomalies
  ```
- **MIRROR**: Follow documentation style from existing `CLAUDE.md`
- **IMPORTS**: N/A (documentation)
- **GOTCHA**: Runbooks must be tested quarterly, document lessons learned from incidents
- **VALIDATE**: Conduct table-top disaster recovery exercise, update runbook with gaps found

### Task 12: Setup ArgoCD for GitOps Deployment
- **ACTION**: Configure continuous deployment from Git to Kubernetes
- **IMPLEMENT**:
  ```yaml
  # argocd/application.yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: claude-test-runner
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://github.com/your-org/claude-code-test-runner.git
      targetRevision: main
      path: k8s/base
    destination:
      server: https://kubernetes.default.svc
      namespace: claude-test-runner
    syncPolicy:
      automated:
        prune: true
        selfHeal: true
      syncOptions:
      - CreateNamespace=true
  ```
- **MIRROR**: Follow existing GitOps principles (declarative config, versioned)
- **IMPORTS**: N/A (ArgoCD CRD)
- **GOTCHA**: ArgoCD must have permissions to manage resources in target namespace, use `--selfHeal` for auto-reconciliation
- **VALIDATE**: Push change to Git, ArgoCD automatically syncs to Kubernetes, verify in ArgoCD UI

### Task 13: Create Horizontal Pod Autoscaler (HPA)
- **ACTION**: Enable auto-scaling based on CPU/memory
- **IMPLEMENT**:
  ```yaml
  # k8s/base/backend-hpa.yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: backend-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: backend
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
        policies:
        - type: Percent
          value: 50
          periodSeconds: 15
      scaleUp:
        stabilizationWindowSeconds: 0
        policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
        selectPolicy: Max
  ```
- **MIRROR**: Follow resource limits from Task 5
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Metrics Server must be installed in cluster (`kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`)
- **VALIDATE**: `kubectl get hpa` shows current metrics, load test triggers scale-out to maxReplicas

### Task 14: Add Network Policies for Security
- **ACTION**: Restrict network traffic between services
- **IMPLEMENT**:
  ```yaml
  # k8s/network-policies.yaml
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: backend-policy
  spec:
    podSelector:
      matchLabels:
        app: backend
    policyTypes:
    - Ingress
    - Egress
    ingress:
    - from:
      - podSelector:
          matchLabels:
            app: nginx-ingress
      ports:
      - protocol: TCP
        port: 8001
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
      - protocol: TCP
        port: 8001
    egress:
    - to:
      - podSelector:
          matchLabels:
            app: postgres
      ports:
      - protocol: TCP
        port: 5432
    - to:
      - podSelector:
          matchLabels:
            app: redis
      ports:
      - protocol: TCP
        port: 6379
    - to:
      - namespaceSelector: {}
      ports:
      - protocol: TCP
        port: 443  # Allow external API calls (Anthropic)
  ```
- **MIRROR**: Follow service communication pattern from `service/docker-compose.yml`
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: Network policies only work with CNI plugins that support them (Calico, Cilium, Weave Net)
- **VALIDATE**: `kubectl exec -it backend-xxxxx -- curl postgres:5432` fails (blocked), `curl nginx-ingress:8001` succeeds (allowed)

### Task 15: Create Grafana Dashboards
- **ACTION**: Build observability dashboards for monitoring
- **IMPLEMENT**:
  ```json
  {
    "dashboard": {
      "title": "Claude Test Runner - Overview",
      "panels": [
        {
          "title": "Request Rate",
          "targets": [
            {
              "expr": "rate(http_requests_total[5m])"
            }
          ]
        },
        {
          "title": "Error Rate",
          "targets": [
            {
              "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
            }
          ]
        },
        {
          "title": "P95 Latency",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
            }
          ]
        },
        {
          "title": "Database Connections",
          "targets": [
            {
              "expr": "pg_stat_database_numbackends{datname=\"cc_test_db\"}"
            }
          ]
        },
        {
          "title": "Celery Queue Length",
          "targets": [
            {
              "expr": "redis_queue_length"
            }
          ]
        }
      ]
    }
  }
  ```
- **MIRROR**: Follow metrics structure from Prometheus `/metrics` endpoint (Task 1)
- **IMPORTS**: N/A (Grafana dashboard JSON)
- **GOTCHA**: Use variables for namespace filtering, set up alerts for threshold breaches
- **VALIDATE**: Dashboard displays real-time metrics, data refreshes correctly

### Task 16: Setup Alerting Rules
- **ACTION**: Configure Prometheus AlertManager for proactive notifications
- **IMPLEMENT**:
  ```yaml
  # k8s/monitoring/alertmanager-config.yaml
  apiVersion: monitoring.coreos.com/v1
  kind: PrometheusRule
  metadata:
    name: claude-test-runner-alerts
    namespace: monitoring
  spec:
    groups:
    - name: backend-alerts
      rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec for {{ $labels.instance }}"
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency detected"
          description: "P95 latency is {{ $value }} seconds"
      - alert: DatabaseConnectionsHigh
        expr: pg_stat_database_numbackends{datname=\"cc_test_db\"} > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool nearly exhausted"
      - alert: PodNotReady
        expr: kube_pod_status_phase{phase=\"Running\"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} is not ready"
  ```
- **MIRROR**: Follow health check pattern from `service/backend/app/main.py:96-99`
- **IMPORTS**: N/A (Prometheus CRD)
- **GOTCHA**: Alert severity must match on-call response expectations, set up routing to Slack/PagerDuty
- **VALIDATE**: Trigger alert condition (e.g., scale backend to 0), receive notification in configured channel

### Task 17: Create Deployment Runbook
- **ACTION**: Document standard deployment procedures
- **IMPLEMENT**:
  ```markdown
  # docs/runbooks/deployment.md

  ## Standard Deployment Process

  ### 1. Pre-Deployment Checklist
  - [ ] All tests passing in CI/CD
  - [ ] Security scan shows no critical vulnerabilities
  - [ ] Database migrations prepared and tested
  - [ ] Feature flags configured
  - [ ] Rollback plan documented

  ### 2. Staging Deployment
  1. Create release branch: `git checkout -b release/v1.2.3`
  2. Update version in `service/backend/app/core/config.py`
  3. Push branch: `git push origin release/v1.2.3`
  4. Monitor staging deployment: `kubectl get pods -n claude-test-runner-staging -w`
  5. Run smoke tests against staging
  6. Verify metrics: Check Grafana dashboards

  ### 3. Production Deployment
  1. Create PR: `release/v1.2.3` → `main`
  2. Get approval from 2 maintainers
  3. Merge PR
  4. Monitor production deployment: `kubectl rollout status deployment/backend -n claude-test-runner`
  5. Verify health endpoints: `kubectl get --raw /api/v1/health`
  6. Check error rates in Grafana
  7. Monitor logs: `kubectl logs -f deployment/backend -n claude-test-runner`

  ### 4. Post-Deployment
  - [ ] Verify key user journeys
  - [ ] Check error budgets
  - [ ] Update deployment documentation
  - [ ] Notify team of successful deployment

  ### Rollback Procedure
  If issues detected:
  1. `kubectl rollout undo deployment/backend -n claude-test-runner`
  2. Verify rollback completed: `kubectl rollout status deployment/backend -n claude-test-runner`
  3. Investigate logs and metrics
  4. Create incident report if SLA breached
  ```
- **MIRROR**: Follow documentation style from existing `CLAUDE.md`
- **IMPORTS**: N/A (documentation)
- **GOTCHA**: Runbook must be version-controlled with the codebase, update with each deployment
- **VALIDATE**: Conduct deployment drill, measure time to deployment and rollback

### Task 18: Implement Secrets Management with Sealed Secrets
- **ACTION**: Encrypt secrets for Git storage
- **IMPLEMENT**:
  ```bash
  # Install Sealed Secrets controller
  kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

  # Create secret locally
  kubectl create secret generic postgres-secret \
    --from-literal=password=changeme \
    --dry-run=client \
    -o yaml > postgres-secret.yaml

  # Seal the secret
  kubeseal -f postgres-secret.yaml -w k8s/base/sealed-secrets.yaml

  # Commit sealed secret to Git
  git add k8s/base/sealed-secrets.yaml
  git commit -m "Add sealed secrets"
  ```
- **MIRROR**: Follow secrets pattern from `service/.env.example:1-41`
- **IMPORTS**: `kubeseal` CLI tool
- **GOTCHA**: Sealed Secrets can only be decrypted in the cluster where the controller is installed
- **VALIDATE**: `kubectl apply -f k8s/base/sealed-secrets.yaml`, secret appears in cluster, deployment uses secret

### Task 19: Add OpenTelemetry Distributed Tracing
- **ACTION**: Implement end-to-end request tracing
- **IMPLEMENT**:
  ```python
  # service/backend/app/middleware/tracing.py
  from opentelemetry import trace
  from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
  from opentelemetry.exporter.jaeger.thrift import JaegerExporter
  from opentelemetry.sdk.trace import TracerProvider
  from opentelemetry.sdk.trace.export import BatchSpanProcessor

  def setup_tracing(app: FastAPI) -> None:
      """Configure OpenTelemetry tracing with Jaeger exporter."""
      trace.set_tracer_provider(TracerProvider())
      jaeger_exporter = JaegerExporter(
          agent_host_name="jaeger",
          agent_port=6831,
      )
      trace.get_tracer_provider().add_span_processor(
          BatchSpanProcessor(jaeger_exporter)
      )
      FastAPIInstrumentor.instrument_app(app)
  ```
- **MIRROR**: Follow middleware pattern from `service/backend/app/main.py:49-56`
- **IMPORTS**: `pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-jaeger`
- **GOTCHA**: Jaeger agent must be deployed (`kubectl apply -f k8s/monitoring/jaeger.yaml`), sampling rate to avoid overhead
- **VALIDATE**: Access Jaeger UI, trace shows request flow through services (frontend → nginx → backend → postgres)

### Task 20: Create PodDisruptionBudgets for High Availability
- **ACTION**: Ensure minimum availability during maintenance
- **IMPLEMENT**:
  ```yaml
  # k8s/base/backend-pdb.yaml
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  metadata:
    name: backend-pdb
  spec:
    minAvailable: 1
    selector:
      matchLabels:
        app: backend
  ---
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  metadata:
    name: postgres-pdb
  spec:
    minAvailable: 1  # At least 1 postgres replica must be available
    selector:
      matchLabels:
        app: postgres
  ```
- **MIRROR**: Follow replica pattern from Task 5
- **IMPORTS**: N/A (Kubernetes manifest)
- **GOTCHA**: PDB only works with voluntary disruptions (node drains), not node failures
- **VALIDATE**: `kubectl drain node --ignore-daemonsets --delete-emptydir-data`, PDB blocks eviction if minAvailable not met

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| Prometheus metrics endpoint | HTTP GET /metrics | 200 OK, Prometheus format | Metrics endpoint protected by auth |
| Health check endpoint | HTTP GET /health | {"status": "healthy"} | Database unavailable returns 503 |
| Structured logging | Any request | Log with correlation_id | Correlation ID propagated to downstream calls |
| Tracing span | HTTP request | Span with trace_id, parent_id | Multi-service trace continuity |

### Integration Tests

| Test | Scenario | Expected Result |
|---|---|---|
| End-to-end deployment | Deploy all K8s manifests | All pods Ready, services accessible |
| Backup/restore | Create backup, delete data, restore | Data restored successfully |
| Auto-scaling | Load test backend | HPA scales to maxReplicas, scales down after load |
| SSL/TLS | Access via HTTPS | Valid certificate, no browser warnings |
| Alerting | Trigger alert condition | Notification sent to Slack/PagerDuty |

### Edge Cases Checklist
- [ ] Pod evicted due to resource pressure
- [ ] Node failure during active request
- [ ] Database connection pool exhausted
- [ ] Redis queue overflow
- [ ] SSL certificate expires
- [ ] Backup restoration fails
- [ ] Deployment rollback mid-deployment
- [ ] Network policy blocks legitimate traffic
- [ ] Secrets decryption failure
- [ ] Monitoring stack unavailable

---

## Validation Commands

### Kubernetes Cluster Validation
```bash
# Verify all resources deployed
kubectl get all -n claude-test-runner

# Check pod health
kubectl get pods -n claude-test-runner -o wide

# Verify PVCs bound
kubectl get pvc -n claude-test-runner

# Check certificate status
kubectl get certificate -n claude-test-runner

# Verify HPA metrics
kubectl get hpa -n claude-test-runner

# Test network policies
kubectl exec -it backend-xxxxx -n claude-test-runner -- curl postgres:5432
```
EXPECT: All pods Ready, PVCs Bound, Certificate Ready, HPA showing metrics, network policies blocking unauthorized traffic

### Monitoring Validation
```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80

# Access Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query metrics
curl http://localhost:9090/api/v1/query?query=up
```
EXPECT: Grafana accessible at localhost:3000, Prometheus targets all UP, metrics returned

### Backup Validation
```bash
# List backup jobs
kubectl get jobs -n claude-test-runner --sort-by=.metadata.creationTimestamp

# Verify backup exists in storage
kubectl exec -it postgres-backup-xxxxx -n claude-test-runner -- ls -lh /backups

# Test restore procedure
./scripts/backup/test-restore.sh
```
EXPECT: Backup jobs completed successfully, backup files present, restore passes integrity check

### SSL/TLS Validation
```bash
# Check certificate
kubectl get certificate claude-test-runner-cert -n claude-test-runner -o yaml

# Verify TLS handshake
openssl s_client -connect test-runner.yourdomain.com:443 -servername test-runner.yourdomain.com

# Check certificate expiration
echo | openssl s_client -connect test-runner.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```
EXPECT: Certificate status Ready, TLS handshake succeeds, certificate not expired

### Disaster Recovery Validation
```bash
# Simulate database failure
kubectl scale statefulset postgres --replicas=0 -n claude-test-runner

# Run restore procedure
./scripts/backup/restore-postgres.sh latest-backup.sql

# Verify data integrity
kubectl exec -it postgres-0 -n claude-test-runner -- psql -U cc_test_user -d cc_test_db -c "SELECT COUNT(*) FROM test_runs"

# Restart postgres
kubectl scale statefulset postgres --replicas=1 -n claude-test-runner
```
EXPECT: Database restored, data intact, service resumes normal operation

### CI/CD Validation
```bash
# Trigger workflow
git push origin main

# Monitor workflow run
gh run view --log

# Verify deployment
kubectl rollout status deployment/backend -n claude-test-runner
```
EXPECT: Workflow completes successfully, all jobs pass, deployment rolled out

### Manual Validation
- [ ] Access production URL via HTTPS, valid certificate shown
- [ ] Login works, session persisted
- [ ] Create test case, verify in dashboard
- [ ] Execute test run, monitor in Grafana
- [ ] Check logs show correlation IDs
- [ ] Verify trace in Jaeger shows full request path
- [ ] Trigger alert (e.g., scale backend to 0), receive notification
- [ ] Create backup, verify backup file exists
- [ ] Check resource usage within limits
- [ ] Verify auto-scaling works under load

---

## Acceptance Criteria
- [ ] All 20 tasks completed
- [ ] Kubernetes cluster deployed with all services healthy
- [ ] Prometheus and Grafana showing metrics and dashboards
- [ ] SSL/TLS certificate valid and auto-renewing
- [ ] Automated backups running daily with retention policy
- [ ] Disaster recovery runbook tested and documented
- [ ] CI/CD pipeline builds, tests, and deploys automatically
- [ ] Alerts configured and routed to notification channels
- [ ] Secrets encrypted and stored in Git (Sealed Secrets)
- [ ] Network policies restricting traffic
- [ ] HPA scaling based on CPU/memory
- [ ] Distributed tracing operational (Jaeger)
- [ ] PodDisruptionBudgets ensuring high availability
- [ ] Deployment runbook documented and tested
- [ ] No hardcoded credentials in code
- [ ] No critical vulnerabilities in security scans
- [ ] All validation commands passing
- [ ] Manual testing checklist completed

## Completion Checklist
- [ ] Kubernetes manifests follow K8s best practices
- [ ] Monitoring covers all 4 signals (latency, traffic, errors, saturation)
- [ ] Logging structured with correlation IDs
- [ ] Tracing end-to-end across services
- [ ] Security follows principle of least privilege
- [ ] Backup strategy meets RPO/RTO objectives
- [ ] Disaster recovery procedures tested quarterly
- [ ] Deployment process zero-downtime (rolling updates)
- [ ] Auto-scaling configured and tested
- [ ] Alerts actionable with runbooks
- [ ] Secrets never committed in plaintext
- [ ] Infrastructure as code (all manifests in Git)
- [ ] GitOps deployment automated (ArgoCD)
- [ ] Documentation up to date
- [ ] Team trained on operations procedures

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Kubernetes cluster misconfiguration** | Medium | High | Use managed K8s (EKS/GKE/AKS), test in dev environment first |
| **Backup restoration failure** | Low | Critical | Test restore monthly, document and validate procedures |
| **SSL certificate expiration** | Low | High | Use cert-manager auto-renewal, set expiry alerts |
| **Resource exhaustion** | Medium | Medium | Set resource limits, configure HPA, monitor usage |
| **Secrets leak in Git history** | Low | Critical | Use git-secrets GHook, scan repo for secrets, rotate if found |
| **Monitoring stack unavailable** | Low | Medium | Deploy monitoring in separate namespace, use managed services |
| **Network policies blocking traffic** | Medium | High | Test policies in staging, start with permissive rules, tighten gradually |
| **Deployment causing downtime** | Medium | High | Use rolling updates, PodDisruptionBudgets, test in staging first |
| **Auto-scaling not triggering** | Low | Medium | Verify Metrics Server installed, test load with ramp-up |
| **Alert fatigue** | High | Low | Tune alert thresholds, use severity levels, implement alert grouping |
| **Vendor lock-in (cloud-specific features)** | Medium | Medium | Use open-source tools, Terraform for infra, avoid cloud-specific APIs |
| **Insufficient backup retention** | Low | Medium | Implement 30-day retention, store backups off-site (S3/GCS) |

## Notes

### Production Readiness Levels (PRL)

**Current PRL: 2/10**
- ✅ Basic Docker containerization
- ✅ Simple health checks
- ❌ No centralized logging/monitoring
- ❌ No automated backups
- ❌ No secrets management
- ❌ No SSL/TLS
- ❌ No disaster recovery plan
- ❌ No CI/CD automation
- ❌ Manual deployment

**Target PRL: 9/10**
- ✅ Kubernetes orchestration
- ✅ Comprehensive observability (logging, metrics, tracing)
- ✅ Automated backups with retention
- ✅ Secrets encryption (Sealed Secrets/Vault)
- ✅ SSL/TLS with auto-renewal
- ✅ Documented disaster recovery
- ✅ CI/CD with security scanning
- ✅ GitOps deployment (ArgoCD)
- ⚠️ Multi-region (future enhancement)

### Implementation Phases

**Phase 1: Foundation (Weeks 1-2)**
- Tasks 1-5: Core infrastructure (K8s, deployments, metrics)
- Deliverable: Services running in K8s with basic monitoring

**Phase 2: Observability (Weeks 3-4)**
- Tasks 6-7, 15-16: Monitoring, logging, alerting
- Deliverable: Grafana dashboards, alerting configured

**Phase 3: Security & Reliability (Weeks 5-6)**
- Tasks 8-9, 13-14, 18: SSL/TLS, network policies, secrets, HPA
- Deliverable: Secure, scalable production environment

**Phase 4: Automation (Weeks 7-8)**
- Tasks 10, 12: CI/CD pipeline, GitOps deployment
- Deliverable: Automated deployment from Git to production

**Phase 5: Resilience (Weeks 9-10)**
- Tasks 11, 17, 19-20: Backup/restore, runbooks, tracing, PDBs
- Deliverable: Full production readiness with documented procedures

### Cost Considerations

**Cloud Resources (monthly estimates for small production deployment):**
- Kubernetes cluster (managed): $100-300/month
- Load balancer: $20/month
- Block storage (200GB): $30/month
- Backup storage (S3/GCS): $10/month
- Domain + SSL: Free (Let's Encrypt)
- Monitoring tools: Free (open-source)
- **Total: ~$160-560/month**

**Alternative: Self-hosted on bare metal**
- Hardware costs (amortized): $200-500/month
- Electricity: $50-100/month
- **Total: ~$250-600/month**

### Team Skills Required

- **DevOps Engineer**: Kubernetes, CI/CD, monitoring
- **Site Reliability Engineer**: SLOs, runbooks, incident response
- **Security Engineer**: Secrets management, network policies
- **Database Administrator**: Backup/restore, replication
- **Software Engineer**: Instrumentation (metrics, tracing)

### Ongoing Maintenance

**Daily:**
- Check Grafana dashboards for anomalies
- Review alert notifications
- Verify backup jobs completed

**Weekly:**
- Review resource usage and costs
- Tune alert thresholds
- Check SSL certificate expiry

**Monthly:**
- Test backup restoration
- Review and update runbooks
- Conduct security audit
- Performance tuning (HPA, resource limits)

**Quarterly:**
- Disaster recovery drill
- Security vulnerability assessment
- Capacity planning review
- Team training and documentation update
