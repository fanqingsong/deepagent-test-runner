#!/bin/bash
# Observability Stack Integration Test
# Validates that all observability components are properly configured

set -e

echo "=================================="
echo "Observability Stack Integration Test"
echo "=================================="
echo

# Test 1: Verify Python middleware files exist
echo "Test 1: Checking Python middleware files..."
files=(
    "service/backend/app/middleware/logging.py"
    "service/backend/app/middleware/prometheus.py"
    "service/backend/app/middleware/tracing.py"
    "service/backend/app/core/observability.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done
echo

# Test 2: Verify Python syntax
echo "Test 2: Validating Python syntax..."
for file in "${files[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "  ✓ $file syntax valid"
    else
        echo "  ✗ $file syntax error"
        exit 1
    fi
done
echo

# Test 3: Verify observability is integrated in main.py
echo "Test 3: Checking main.py integration..."
if grep -q "from app.core.observability import setup_observability" service/backend/app/main.py; then
    echo "  ✓ Observability import found"
else
    echo "  ✗ Observability import missing"
    exit 1
fi

if grep -q "setup_observability(app)" service/backend/app/main.py; then
    echo "  ✓ Observability setup call found"
else
    echo "  ✗ Observability setup call missing"
    exit 1
fi
echo

# Test 4: Verify configuration in config.py
echo "Test 4: Checking configuration fields..."
config_fields=(
    "PROMETHEUS_ENABLED"
    "PROMETHEUS_PORT"
    "LOKI_ENABLED"
    "LOKI_ENDPOINT"
    "JAEGER_ENABLED"
    "JAEGER_AGENT_HOST"
    "TRACE_SAMPLE_RATE"
    "LOG_FORMAT"
)

for field in "${config_fields[@]}"; do
    if grep -q "$field" service/backend/app/core/config.py; then
        echo "  ✓ $field configured"
    else
        echo "  ✗ $field missing"
        exit 1
    fi
done
echo

# Test 5: Verify Kubernetes manifests
echo "Test 5: Checking Kubernetes manifests..."
k8s_files=(
    "k8s/observability/prometheus-config.yaml"
    "k8s/observability/loki-stack.yaml"
    "k8s/observability/promtail-config.yaml"
    "k8s/observability/jaeger-deployment.yaml"
)

for file in "${k8s_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done
echo

# Test 6: Verify Grafana dashboards
echo "Test 6: Checking Grafana dashboards..."
dashboards=(
    "k8s/observability/grafana-dashboards/overview-dashboard.json"
    "k8s/observability/grafana-dashboards/api-performance-dashboard.json"
    "k8s/observability/grafana-dashboards/database-metrics-dashboard.json"
)

for dashboard in "${dashboards[@]}"; do
    if [ -f "$dashboard" ]; then
        echo "  ✓ $dashboard exists"
    else
        echo "  ✗ $dashboard missing"
        exit 1
    fi
done
echo

# Test 7: Verify documentation
echo "Test 7: Checking documentation..."
docs=(
    "docs/observability/setup.md"
    "docs/observability/troubleshooting.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo "  ✓ $doc exists"
    else
        echo "  ✗ $doc missing"
        exit 1
    fi
done
echo

# Test 8: Verify dependencies in requirements.txt
echo "Test 8: Checking observability dependencies..."
deps=(
    "prometheus-fastapi-instrumentator"
    "opentelemetry-api"
    "opentelemetry-sdk"
    "opentelemetry-instrumentation-fastapi"
    "structlog"
)

for dep in "${deps[@]}"; do
    if grep -q "$dep" service/backend/requirements.txt; then
        echo "  ✓ $dep in requirements.txt"
    else
        echo "  ✗ $dep missing from requirements.txt"
        exit 1
    fi
done
echo

echo "=================================="
echo "All tests passed! ✓"
echo "=================================="
echo
echo "Observability stack is ready for deployment."
echo "See docs/observability/setup.md for deployment instructions."
