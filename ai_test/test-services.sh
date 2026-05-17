#!/bin/bash

# Claude Code Tests - Microservices Test Script
# This script tests all services after they start

set -e

echo "=== Claude Code Tests Microservices - Test Script ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service ports
TEST_CASE_PORT=8011
SCHEDULER_PORT=8012
DASHBOARD_PORT=8013
POSTGRES_PORT=5433
REDIS_PORT=6380

echo "1. Checking if all services are running..."
echo ""

# Check if services are up
check_service() {
    local name=$1
    local port=$2
    if docker compose ps | grep -q "$name.*Up"; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT running"
        return 1
    fi
}

check_service "test-case-service" $TEST_CASE_PORT
check_service "scheduler-service" $SCHEDULER_PORT
check_service "dashboard-service" $DASHBOARD_PORT
check_service "postgres" $POSTGRES_PORT
check_service "redis" $REDIS_PORT

echo ""
echo "2. Waiting for services to be healthy..."
echo ""

# Wait for health checks
wait_for_health() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=0

    echo -n "   Waiting for $name..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" | grep -q "ok\|running\|healthy"; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
        echo -n "."
    done
    echo -e " ${RED}FAILED${NC}"
    return 1
}

wait_for_health "Test Case Service" "http://localhost:$TEST_CASE_PORT/health"
wait_for_health "Scheduler Service" "http://localhost:$SCHEDULER_PORT/health"
wait_for_health "Dashboard Service" "http://localhost:$DASHBOARD_PORT/health"

echo ""
echo "3. Testing API endpoints..."
echo ""

# Test authentication
echo "   Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:$TEST_CASE_PORT/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}')
if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    echo -e "   ${GREEN}✓${NC} User registration successful"
    TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
else
    echo -e "   ${YELLOW}⚠${NC} User registration failed (may already exist)"
    # Try to login instead
    LOGIN_RESPONSE=$(curl -s -X POST http://localhost:$TEST_CASE_PORT/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}')
    if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
        TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        echo -e "   ${GREEN}✓${NC} Admin login successful"
    else
        echo -e "   ${RED}✗${NC} Authentication failed"
        TOKEN=""
    fi
fi

if [ -n "$TOKEN" ]; then
    echo "   Testing protected endpoints..."
    TEST_DEFS=$(curl -s -X GET http://localhost:$TEST_CASE_PORT/api/v1/test-definitions \
        -H "Authorization: Bearer $TOKEN")
    if echo "$TEST_DEFS" | grep -q "test_definitions\|items"; then
        echo -e "   ${GREEN}✓${NC} Get test definitions successful"
    else
        echo -e "   ${RED}✗${NC} Get test definitions failed"
    fi
fi

echo ""
echo "4. Testing Dashboard..."
echo ""

DASHBOARD_RESPONSE=$(curl -s http://localhost:$DASHBOARD_PORT/)
if echo "$DASHBOARD_RESPONSE" | grep -q "Claude Code Tests\|Dashboard\|Test Analytics"; then
    echo -e "   ${GREEN}✓${NC} Dashboard HTML loads"
else
    echo -e "   ${RED}✗${NC} Dashboard HTML failed to load"
fi

DASHBOARD_API=$(curl -s http://localhost:$DASHBOARD_PORT/api/dashboard)
if echo "$DASHBOARD_API" | grep -q "total_tests\|total_runs"; then
    echo -e "   ${GREEN}✓${NC} Dashboard API responding"
else
    echo -e "   ${RED}✗${NC} Dashboard API failed"
fi

echo ""
echo "5. Checking database connectivity..."
echo ""

if docker exec cc-test-postgres pg_isready -U testuser -d claude_code_tests > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} PostgreSQL is ready"

    # Check if tables exist
    TABLES=$(docker exec cc-test-postgres psql -U testuser -d claude_code_tests -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs)
    if [ "$TABLES" -gt 0 ]; then
        echo -e "   ${GREEN}✓${NC} Database tables initialized ($TABLES tables)"
    else
        echo -e "   ${RED}✗${NC} Database tables not found"
    fi
else
    echo -e "   ${RED}✗${NC} PostgreSQL is not ready"
fi

echo ""
echo "6. Checking Redis..."
echo ""

if docker exec cc-test-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Redis is responding"
else
    echo -e "   ${RED}✗${NC} Redis is not responding"
fi

echo ""
echo "7. Checking service logs for errors..."
echo ""

check_logs() {
    local service=$1
    local errors=$(docker compose logs --tail=50 $service 2>&1 | grep -i "error\|exception\|failed" | wc -l)
    if [ "$errors" -eq 0 ]; then
        echo -e "   ${GREEN}✓${NC} $service: No errors in logs"
    else
        echo -e "   ${YELLOW}⚠${NC} $service: $errors potential errors in logs"
    fi
}

check_logs "test-case-service"
check_logs "scheduler-service"
check_logs "dashboard-service"

echo ""
echo "=== Test Summary ==="
echo ""
echo "All services have been deployed and basic tests completed."
echo ""
echo "Service URLs:"
echo "  - Test Case Service: http://localhost:$TEST_CASE_PORT"
echo "  - Scheduler Service:  http://localhost:$SCHEDULER_PORT"
echo "  - Dashboard Service:  http://localhost:$DASHBOARD_PORT"
echo "  - API Docs:           http://localhost:$TEST_CASE_PORT/api/docs"
echo ""
echo "Database:"
echo "  - PostgreSQL:         localhost:$POSTGRES_PORT"
echo "  - Redis:              localhost:$REDIS_PORT"
echo ""
echo "Next steps:"
echo "  1. Run full test suite: cd test-case-service && pytest tests/"
echo "  2. Create test jobs via API"
echo "  3. View dashboard for analytics"
echo ""
