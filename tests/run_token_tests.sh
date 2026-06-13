#!/bin/bash

# Token Limitation System Test Runner
# Runs comprehensive tests for all token limitation components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/fqs/workspace/self/deepagent-test-runner"
PLATFORM_DIR="$PROJECT_ROOT/platform"
TEST_DIR="$PROJECT_ROOT/tests"
REPORT_DIR="$TEST_DIR/test-reports"

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Token Limitation System Test Runner${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Change to platform directory
cd "$PLATFORM_DIR"

# Function to run test category
run_test_category() {
    local category=$1
    local test_file=$2
    local description=$3

    echo -e "${YELLOW}Running $description...${NC}"
    echo "================================"

    if python -m pytest "$test_file" -v --tb=short \
        --html="$REPORT_DIR/${category}_report.html" \
        --self-contained-html; then
        echo -e "${GREEN}✓ $description PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ $description FAILED${NC}"
        return 1
    fi
    echo ""
}

# Track overall success
overall_success=true

# Run test categories
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running Token Limitation System Tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. Repository Tests
if ! run_test_category "repositories" "tests/repositories/test_token_repositories.py" "Repository Tests"; then
    overall_success=false
fi

# 2. Service Tests
if ! run_test_category "services" "tests/services/test_token_services.py" "Service Tests"; then
    overall_success=false
fi

# 3. Decorator Tests
if ! run_test_category "decorators" "tests/core/test_token_decorators.py" "Decorator Tests"; then
    overall_success=false
fi

# 4. API Endpoint Tests
if ! run_test_category "api" "tests/api/test_token_endpoints.py" "API Endpoint Tests"; then
    overall_success=false
fi

# 5. Workflow Integration Tests
if ! run_test_category "workflows" "tests/integration/test_token_workflows.py" "Workflow Integration Tests"; then
    overall_success=false
fi

# 6. System Integration Tests
if ! run_test_category "system" "tests/integration/test_token_system.py" "System Integration Tests"; then
    overall_success=false
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Execution Summary${NC}"
echo -e "${GREEN}========================================${NC}"

if [ "$overall_success" = true ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "HTML reports generated in: $REPORT_DIR"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check individual reports in: $REPORT_DIR"
    exit 1
fi
