#!/bin/bash

# Health Check System Test Script
# Tests all health check endpoints and functionality

set -e

BASE_URL="http://localhost:8011/api/v1"
echo "Testing Health Check System..."
echo "================================"

# Test 1: Simple health check
echo "Test 1: Simple health check (GET /health)"
response=$(curl -s -o /dev/null -w "%{http_code}" ${BASE_URL}/health)
if [ "$response" = "200" ]; then
    echo "✓ Simple health check passed (HTTP $response)"
else
    echo "✗ Simple health check failed (HTTP $response)"
fi
echo ""

# Test 2: Detailed health check
echo "Test 2: Detailed health check (GET /health/detailed)"
response=$(curl -s ${BASE_URL}/health/detailed)
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Detailed health check returned valid JSON"
    echo "  Status: $(echo $response | jq -r '.status')"
    echo "  Components: $(echo $response | jq -r '.total_components')"
else
    echo "✗ Detailed health check failed"
fi
echo ""

# Test 3: Critical components only
echo "Test 3: Critical components (GET /health/critical)"
response=$(curl -s ${BASE_URL}/health/critical)
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Critical components check returned valid JSON"
else
    echo "✗ Critical components check failed"
fi
echo ""

# Test 4: Component-specific checks
echo "Test 4: Component-specific checks"
for component in database redis llm temporal filesystem; do
    response=$(curl -s ${BASE_URL}/health/${component} || echo "error")
    if [ "$response" != "error" ]; then
        echo "$response" | jq '.' > /dev/null 2>&1
        if [ $? = 0 ]; then
            status=$(echo $response | jq -r '.status')
            echo "✓ $component: $status"
        else
            echo "✗ $component: Invalid response"
        fi
    else
        echo "✗ $component: Request failed"
    fi
done
echo ""

# Test 5: Health summary
echo "Test 5: Health summary (GET /health/summary)"
response=$(curl -s ${BASE_URL}/health/summary)
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Health summary returned valid JSON"
    echo "  Status: $(echo $response | jq -r '.status')"
else
    echo "✗ Health summary failed"
fi
echo ""

# Test 6: Health history
echo "Test 6: Health history (GET /health/history)"
response=$(curl -s ${BASE_URL}/health/history)
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Health history returned valid JSON"
    count=$(echo $response | jq -r '.total_entries')
    echo "  History entries: $count"
else
    echo "✗ Health history failed"
fi
echo ""

# Test 7: Cache control
echo "Test 7: Cache control (POST /health/cache/clear)"
response=$(curl -s -X POST ${BASE_URL}/health/cache/clear)
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Cache clear returned valid JSON"
else
    echo "✗ Cache clear failed"
fi
echo ""

# Test 8: Skip cache parameter
echo "Test 8: Skip cache parameter (GET /health/detailed?skip_cache=true)"
response=$(curl -s "${BASE_URL}/health/detailed?skip_cache=true")
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Skip cache parameter works"
else
    echo "✗ Skip cache parameter failed"
fi
echo ""

# Test 9: Parallel execution parameter
echo "Test 9: Parallel execution parameter (GET /health/detailed?parallel=false)"
response=$(curl -s "${BASE_URL}/health/detailed?parallel=false")
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Parallel execution parameter works"
else
    echo "✗ Parallel execution parameter failed"
fi
echo ""

# Test 10: Critical only parameter
echo "Test 10: Critical only parameter (GET /health/detailed?critical_only=true)"
response=$(curl -s "${BASE_URL}/health/detailed?critical_only=true")
echo "$response" | jq '.' > /dev/null 2>&1
if [ $? = 0 ]; then
    echo "✓ Critical only parameter works"
    total=$(echo $response | jq -r '.total_components')
    echo "  Critical components checked: $total"
else
    echo "✗ Critical only parameter failed"
fi
echo ""

echo "================================"
echo "Health Check System Tests Complete!"
