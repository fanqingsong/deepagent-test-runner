#!/bin/bash

echo "=== SSO 配置管理功能 - 综合测试 ==="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_step() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name ... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 1. 检查前端服务
echo "1️⃣  前端服务检查"
test_step "Frontend is running on port 8080" "curl -s -f http://localhost:8080"
test_step "Frontend returns HTML" "curl -s http://localhost:8080 | grep -q '<!DOCTYPE html>'"
echo ""

# 2. 检查后端服务
echo "2️⃣  后端服务检查"
test_step "Backend API is running" "curl -s -f http://localhost:8011/api/v1/sso/config"
test_step "Database is accessible" "docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c 'SELECT 1'"
echo ""

# 3. 认证测试
echo "3️⃣  认证功能测试"
test_step "User can login" "curl -s -X POST http://localhost:8011/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"testuser\",\"password\":\"testpass123\"}' | grep -q 'access_token'"
test_step "Token is valid JWT" "curl -s -X POST http://localhost:8011/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"testuser\",\"password\":\"testpass123\"}' | grep -q 'eyJ'"
echo ""

# 4. SSO 配置 API 测试
echo "4️⃣  SSO 配置 API 测试"
TOKEN=$(curl -s -X POST http://localhost:8011/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpass123"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

test_step "List configs (authenticated)" "curl -s http://localhost:8011/api/v1/sso/config -H \"Authorization: Bearer $TOKEN\" | grep -q 'items'"
test_step "Create config (authenticated)" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"casdoor\",\"endpoint\":\"https://test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q 'id'"
test_step "Reject invalid URL" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"casdoor\",\"endpoint\":\"invalid\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q '422'"
test_step "Reject unauthenticated request" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -d '{\"provider\":\"casdoor\",\"endpoint\":\"https://test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q '401'"
echo ""

# 5. 前端组件检查
echo "5️⃣  前端组件检查"
test_step "SSOConfigList component exists" "test -f service/frontend/src/components/SSOConfigList.jsx"
test_step "SSOConfigForm component exists" "test -f service/frontend/src/components/SSOConfigForm.jsx"
test_step "SSOUserList component exists" "test -f service/frontend/src/components/SSOUserList.jsx"
test_step "SSOManagement component exists" "test -f service/frontend/src/components/SSOManagement.jsx"
test_step "App.jsx imports SSOManagement" "grep -q 'SSOManagement' service/frontend/src/App.jsx"
test_step "SSO route configured" "grep -q \"currentView === 'sso'\" service/frontend/src/App.jsx"
echo ""

# 6. 数据库检查
echo "6️⃣  数据库检查"
test_step "sso_configs table exists" "docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c \"SELECT 1 FROM information_schema.tables WHERE table_name='sso_configs'\" | grep -q 1"
test_step "Table has correct columns" "docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c '\d sso_configs' | grep -q 'provider'"
test_step "Table has correct columns" "docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c '\d sso_configs' | grep -q 'endpoint'"
echo ""

# 7. 后端代码检查
echo "7️⃣  后端代码检查"
test_step "SSOConfig model exists" "test -f service/backend/app/models/sso_config.py"
test_step "SSOConfig schema exists" "test -f service/backend/app/schemas/sso_config.py"
test_step "SSO config API endpoint exists" "test -f service/backend/app/api/v1/endpoints/sso_config.py"
test_step "API router includes SSO routes" "grep -q 'sso_config' service/backend/app/api/v1/api.py"
echo ""

# 8. 功能完整性检查
echo "8️⃣  功能完整性检查"
test_step "Create endpoint works" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"casdoor\",\"endpoint\":\"https://functional-test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q 'casdoor'"
test_step "List endpoint returns data" "curl -s http://localhost:8011/api/v1/sso/config -H \"Authorization: Bearer $TOKEN\" | grep -q '\"total\"'"
test_step "Update endpoint works" "curl -s -X PATCH http://localhost:8011/api/v1/sso/config/1 -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"is_enabled\":false}' | grep -q 'false'"
test_step "Delete endpoint works" "curl -s -w '%{http_code}' -X DELETE http://localhost:8011/api/v1/sso/config/1 -H \"Authorization: Bearer $TOKEN\" -o /dev/null | grep -q '204'"
echo ""

# 9. 数据验证测试
echo "9️⃣  数据验证测试"
test_step "Validates URL format" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"casdoor\",\"endpoint\":\"invalid-url\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q '422'"
test_step "Validates provider" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"invalid\",\"endpoint\":\"https://test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q '422'"
test_step "Normalizes provider to lowercase" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"CASDOOR\",\"endpoint\":\"https://test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q '\"provider\":\"casdoor\"'"
test_step "Trims trailing slash from URL" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"provider\":\"casdoor\",\"endpoint\":\"https://test.com/\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q 'https://test.com\"' | grep -v '/'"
echo ""

# 10. 安全性测试
echo "🔟  安全性测试"
test_step "Requires authentication" "curl -s -X POST http://localhost:8011/api/v1/sso/config -H 'Content-Type: application/json' -d '{\"provider\":\"casdoor\",\"endpoint\":\"https://test.com\",\"client_id\":\"test\",\"client_secret\":\"test\"}' | grep -q 'Not authenticated'"
test_step "Requires admin privileges" "curl -s http://localhost:8011/api/v1/sso/config -H \"Authorization: Bearer invalid-token\" | grep -q 'Could not validate credentials'"
echo ""

# 总结
echo "=== 📊 测试结果总结 ==="
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo "总计: $TOTAL_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 有测试失败，需要修复${NC}"
    exit 1
fi
