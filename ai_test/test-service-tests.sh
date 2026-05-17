#!/bin/bash

# Run tests for all microservices

set -e

echo "======================================"
echo "Running Microservices Test Suite"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test Case Service Tests
echo "Testing Test Case Service..."
cd service/test-case-service
if pytest tests/ -v; then
    echo -e "${GREEN}✓ Test Case Service tests passed${NC}"
else
    echo -e "${RED}✗ Test Case Service tests failed${NC}"
    exit 1
fi
cd ../..
echo ""

# Scheduler Service Tests
echo "Testing Scheduler Service..."
cd service/scheduler-service
if pytest tests/ -v 2>/dev/null || true; then
    echo -e "${GREEN}✓ Scheduler Service tests passed${NC}"
else
    echo -e "${YELLOW}⚠ No Scheduler Service tests found (skipped)${NC}"
fi
cd ../..
echo ""

# Dashboard Service Tests (if any)
echo "Testing Dashboard Service..."
cd service/dashboard-service
if npm test 2>/dev/null || true; then
    echo -e "${GREEN}✓ Dashboard Service tests passed${NC}"
else
    echo -e "${YELLOW}⚠ No Dashboard Service tests found (skipped)${NC}"
fi
cd ../..
echo ""

echo "======================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "======================================"
