#!/bin/bash
# Quick start script for Observability Stack with Docker Compose

set -e

echo "=================================="
echo "Observability Stack - Docker Compose"
echo "=================================="
echo

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_DIR="$PROJECT_ROOT/service"

# Check if service directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    echo "Error: service/ directory not found at $SERVICE_DIR"
    exit 1
fi

# Change to service directory
cd "$SERVICE_DIR"
echo "Working directory: $SERVICE_DIR"
echo

# Check if Docker Compose is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

echo "Step 1: Checking if main services are running..."
if ! docker ps | grep -q "cc-test-backend"; then
    echo "Main services not running. Starting them..."
    docker compose up -d postgres redis backend nginx
    echo "Waiting for services to be ready..."
    sleep 10
else
    echo "✓ Main services are already running"
fi
echo

echo "Step 2: Starting observability stack..."
docker compose -f docker-compose.yml -f ../infrastructure/observability/docker-compose.observability.yml up -d
echo

echo "Step 3: Waiting for services to be healthy..."
sleep 15

echo "Step 4: Verifying services..."
SERVICES=("prometheus" "loki" "promtail" "jaeger" "grafana")
ALL_HEALTHY=true

for service in "${SERVICES[@]}"; do
    if docker ps | grep -q "cc-test-$service"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is NOT running"
        ALL_HEALTHY=false
    fi
done
echo

if [ "$ALL_HEALTHY" = true ]; then
    echo "=================================="
    echo "✓ Observability stack is ready!"
    echo "=================================="
    echo
    echo "Access URLs:"
    echo "  Grafana:     http://localhost:3000 (admin/admin)"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Jaeger UI:   http://localhost:16686"
    echo
    echo "To view logs:"
    echo "  docker compose -f ../infrastructure/observability/docker-compose.observability.yml logs -f"
    echo
    echo "To stop:"
    echo "  docker compose -f docker-compose.observability.yml down"
    echo
else
    echo "=================================="
    echo "✗ Some services failed to start"
    echo "=================================="
    echo
    echo "Check logs for details:"
    echo "  docker compose -f docker-compose.observability.yml logs"
    exit 1
fi
