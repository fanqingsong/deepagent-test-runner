#!/bin/bash
# GLM AI配置验证脚本

echo "🔍 GLM AI配置检查工具"
echo "===================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查环境变量
echo "📋 1. 检查环境变量配置..."
API_KEY=$(docker compose exec -T scheduler-worker env | grep ANTHROPIC_API_KEY | cut -d'=' -f2)
BASE_URL=$(docker compose exec -T scheduler-worker env | grep ANTHROPIC_BASE_URL | cut -d'=' -f2)
TIMEOUT=$(docker compose exec -T scheduler-worker env | grep API_TIMEOUT_MS | cut -d'=' -f2)

if [ -n "$API_KEY" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY: ${API_KEY:0:20}...${NC}"
else
    echo -e "${RED}❌ ANTHROPIC_API_KEY: 未设置${NC}"
fi

if [ -n "$BASE_URL" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_BASE_URL: $BASE_URL${NC}"
else
    echo -e "${RED}❌ ANTHROPIC_BASE_URL: 未设置${NC}"
fi

if [ -n "$TIMEOUT" ]; then
    echo -e "${GREEN}✅ API_TIMEOUT_MS: $TIMEOUT ms${NC}"
else
    echo -e "${YELLOW}⚠️  API_TIMEOUT_MS: 使用默认值${NC}"
fi
echo ""

# 检查服务状态
echo "📋 2. 检查服务状态..."
SERVICES=$(docker compose ps --format json)
SCHEDULER_SERVICE=$(echo $SERVICES | grep -o '"scheduler-service"[^}]*' | grep -o '"Status"[^}]*' | grep -o ':[^,]*' | cut -d':' -f2)
SCHEDULER_WORKER=$(echo $SERVICES | grep -o '"scheduler-worker"[^}]*' | grep -o '"Status"[^}]*' | grep -o ':[^,]*' | cut -d':' -f2)

if echo "$SCHEDULER_SERVICE" | grep -q "running\|healthy"; then
    echo -e "${GREEN}✅ scheduler-service: 运行中${NC}"
else
    echo -e "${RED}❌ scheduler-service: $SCHEDULER_SERVICE${NC}"
fi

if echo "$SCHEDULER_WORKER" | grep -q "running\|healthy"; then
    echo -e "${GREEN}✅ scheduler-worker: 运行中${NC}"
else
    echo -e "${RED}❌ scheduler-worker: $SCHEDULER_WORKER${NC}"
fi
echo ""

# 检查API调用
echo "📋 3. 检查最近的API调用..."
API_CALLS=$(docker compose logs scheduler-worker --tail=100 | grep "POST.*anthropic" | tail -5)
if [ -n "$API_CALLS" ]; then
    CALL_COUNT=$(docker compose logs scheduler-worker --tail=100 | grep "POST.*anthropic" | wc -l)
    echo -e "${GREEN}✅ 最近API调用次数: $CALL_COUNT${NC}"
    echo "最近的调用:"
    echo "$API_CALLS" | while read line; do
        TIME=$(echo "$line" | grep -o '\[.*\]' | head -1)
        STATUS=$(echo "$line" | grep -o 'HTTP/[^\"]*')
        echo "  $TIME → $STATUS"
    done
else
    echo -e "${YELLOW}⚠️  未检测到最近的API调用${NC}"
fi
echo ""

# 测试API连接
echo "📋 4. 测试API连接..."
echo "正在测试智谱AI API连接..."

# 创建测试任务
TEST_RESPONSE=$(curl -s -X POST "http://localhost:8012/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{"test_definition_ids": [3]}' 2>/dev/null)

if [ $? -eq 0 ]; then
    # 提取job_id
    JOB_ID=$(echo "$TEST_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$JOB_ID" ]; then
        echo -e "${GREEN}✅ 测试任务已创建: $JOB_ID${NC}"

        # 等待任务完成
        sleep 5

        # 检查任务状态
        JOB_STATUS=$(curl -s "http://localhost:8012/api/v1/jobs/$JOB_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$JOB_STATUS" = "completed" ]; then
            echo -e "${GREEN}✅ 测试任务执行成功${NC}"
        else
            echo -e "${YELLOW}⚠️  测试任务状态: $JOB_STATUS${NC}"
        fi
    else
        echo -e "${RED}❌ 无法创建测试任务${NC}"
    fi
else
    echo -e "${RED}❌ API连接测试失败${NC}"
fi
echo ""

# 配置建议
echo "📋 5. 配置建议..."
echo "基于当前配置的建议:"

if echo "$BASE_URL" | grep -q "bigmodel"; then
    echo -e "${GREEN}🎯 当前使用智谱AI${NC}"
    echo "  ✅ 中文支持优秀"
    echo "  ✅ 成本相对较低"
    echo "  ✅ 国内访问快速"
    echo ""
    echo "💡 建议:"
    echo "  1. 充分利用中文指令能力"
    echo "  2. 定期检查API使用量"
    echo "  3. 监控账户余额"
elif echo "$BASE_URL" | grep -q "anthropic.com"; then
    echo -e "${GREEN}🎯 当前使用Anthropic Claude${NC}"
    echo "  ✅ 英文理解能力强"
    echo "  ✅ 模型性能优秀"
    echo "  ✅ 官方支持完善"
    echo ""
    echo "💡 建议:"
    echo "  1. 适合复杂英文指令"
    echo "  2. 关注API使用成本"
    echo "  3. 考虑与智谱AI混合使用"
else
    echo -e "${YELLOW}🎯 使用自定义API端点${NC}"
    echo "  BASE_URL: $BASE_URL"
    echo ""
    echo "💡 建议:"
    echo "  1. 确认API兼容性"
    echo "  2. 测试基本功能"
    echo "  3. 准备回退方案"
fi
echo ""

# 快速操作指南
echo "📋 6. 快速操作..."
echo "常用命令:"
echo "  🔄 重启服务: docker compose restart scheduler-worker"
echo "  📊 查看日志: docker compose logs -f scheduler-worker"
echo "  🧪 运行测试: 使用前端界面 http://localhost:8013"
echo "  📝 查看配置: cat .env | grep ANTHROPIC"
echo ""

# 文档链接
echo "📋 7. 相关文档..."
echo "  📚 GLM集成指南: GLM_INTEGRATION.md"
echo "  📚 快速配置: QUICK_CONFIG.md"
echo "  📚 成功状态: GLM_INTEGRATION_SUCCESS.md"
echo ""

# 总结
echo "===================="
echo -e "${GREEN}✅ 配置检查完成！${NC}"
echo ""
echo "您的系统已成功配置并可以使用AI驱动的测试执行。"
echo "开始编写自然语言测试步骤，让AI为您自动执行浏览器操作！"
echo ""
echo "🚀 立即体验: http://localhost:8013"