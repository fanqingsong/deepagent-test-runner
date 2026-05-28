#!/bin/bash

# 生产环境启动脚本
# Usage: ./bin/start-prod.sh [service-name]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录检测
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_DIR="${PROJECT_ROOT}/service"

# 检查服务目录
if [ ! -d "${SERVICE_DIR}" ]; then
    echo -e "${RED}错误: service 目录不存在于 ${SERVICE_DIR}${NC}"
    exit 1
fi

# 检查 docker-compose 文件
if [ ! -f "${SERVICE_DIR}/docker-compose.yml" ] || [ ! -f "${SERVICE_DIR}/docker-compose.prod.yml" ]; then
    echo -e "${RED}错误: docker-compose 文件不存在${NC}"
    exit 1
fi

# 检查 .env 文件
ENV_FILE="${SERVICE_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${RED}错误: .env 文件不存在于 ${SERVICE_DIR}${NC}"
    echo -e "${YELLOW}请配置生产环境的环境变量${NC}"
    exit 1
fi

# 检查生产环境必需的变量
check_prod_vars() {
    local critical_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "LLM_API_KEY")
    local missing_vars=()

    for var in "${critical_vars[@]}"; do
        if ! grep -q "^${var}=" "${ENV_FILE}" 2>/dev/null; then
            missing_vars+=("${var}")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}错误: .env 中缺少必需的环境变量:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${RED}  - ${var}${NC}"
        done
        echo -e "${RED}请在 ${ENV_FILE} 中配置后再启动生产环境${NC}"
        exit 1
    fi

    # 检查是否为默认值
    if grep -q "SECRET_KEY=your-secret-key" "${ENV_FILE}"; then
        echo -e "${RED}错误: SECRET_KEY 使用默认值，请修改为强密码${NC}"
        exit 1
    fi

    # 检查 LLM_API_KEY
    if ! grep -q "^LLM_API_KEY=" "${ENV_FILE}" 2>/dev/null || grep -q "^LLM_API_KEY=$" "${ENV_FILE}"; then
        echo -e "${RED}错误: LLM_API_KEY 未设置${NC}"
        exit 1
    fi
}

check_prod_vars

# 切换到服务目录
cd "${SERVICE_DIR}"

# 解析参数
SERVICE_NAME="$1"

echo -e "${BLUE}启动生产环境...${NC}"
echo ""
echo -e "${YELLOW}警告: 正在启动生产环境配置${NC}"
echo ""

read -p "确认启动生产环境? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

if [ -n "${SERVICE_NAME}" ]; then
    echo -e "${GREEN}启动服务: ${SERVICE_NAME}${NC}"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d "${SERVICE_NAME}"
else
    echo -e "${GREEN}启动所有服务...${NC}"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
fi

# 等待服务健康
echo ""
echo -e "${BLUE}等待服务就绪...${NC}"

check_service_health() {
    local service=$1
    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --services --filter "status=running" | grep -q "^${service}$"; then
            local health_status=$(docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format json | grep -A10 "\"name\":\"deepagent-tester-${service}\"" | grep "\"Health\"" | cut -d'"' -f4 2>/dev/null || echo "")
            if [ -z "$health_status" ] || [ "$health_status" = "healthy" ]; then
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    return 1
}

# 等待核心服务
for service in postgres redis backend; do
    if [ -z "${SERVICE_NAME}" ] || [ "${SERVICE_NAME}" = "${service}" ]; then
        echo -n "等待 ${service}..."
        if check_service_health "${service}"; then
            echo -e " ${GREEN}OK${NC}"
        else
            echo -e " ${YELLOW}警告${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}生产环境启动成功！${NC}"
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  前端应用:       http://localhost:8081"
echo "  后端 API:       http://localhost:8081/api/v1/"
echo "  后端直连:       http://localhost:8011"
echo "  PostgreSQL:     localhost:5433"
echo "  Redis:          localhost:6380"
echo "  Temporal UI:    http://localhost:8088"
echo ""
echo -e "${BLUE}生产特性:${NC}"
echo "  多 Worker:      后端使用 2 个 worker 进程"
echo "  生产构建:       前端使用优化后的生产构建"
echo "  无热重载:       代码修改需要重新构建"
echo "  DEBUG=false:    关闭调试模式"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  查看日志:       docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f [service]"
echo "  停止服务:       ./bin/stop-prod.sh"
echo "  服务状态:       docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
echo ""
