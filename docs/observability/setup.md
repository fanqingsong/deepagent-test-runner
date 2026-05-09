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
# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/prometheus \
  --namespace observability \
  --create-namespace \
  --set server.service.type=ClusterIP \
  --set server.service.port=9090 \
  --set server.persistentVolume.enabled=true \
  --set server.persistentVolume.size=50Gi

# Install Loki
kubectl apply -f k8s/observability/loki-stack.yaml

# Install Promtail
kubectl apply -f k8s/observability/promtail-config.yaml

# Install Jaeger
kubectl apply -f k8s/observability/jaeger-deployment.yaml

# Install Grafana
helm install grafana grafana/grafana \
  --namespace observability \
  --set persistence.enabled=true \
  --set persistence.size=10Gi \
  --set adminPassword=admin \
  --set service.type=ClusterIP
```

### 2. Configure Backend Service

Add to `service/.env`:

```bash
# Enable observability
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=false
LOKI_ENABLED=true
LOG_FORMAT=json

# Jaeger agent (enable when tracing needed)
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

# Jaeger (when enabled)
kubectl port-forward -n observability svc/jaeger 16686:16686
open http://localhost:16686
```

## Usage

### Viewing Metrics
1. Access Grafana at http://localhost:3000
2. Login (default: admin/admin)
3. Open "Claude Test Runner - Overview" dashboard
4. View real-time request rate, latency, and errors

### Searching Logs
1. In Grafana, go to Explore → Loki
2. Query: `{app="backend"} |= "error"`
3. Filter by `correlation_id` to trace request flow

### Tracing Requests
1. Enable tracing: `JAEGER_ENABLED=true`
2. Restart backend service
3. Make API requests
4. Access Jaeger UI: http://localhost:16686
5. Search traces by service name or operation

## Troubleshooting
See `docs/observability/troubleshooting.md` for common issues.
