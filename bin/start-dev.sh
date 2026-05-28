#!/bin/bash

# 开发环境启动脚本
# Usage: ./bin/start-dev.sh [service-name]

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

# 检查 docker-compose.yml
if [ ! -f "${SERVICE_DIR}/docker-compose.yml" ]; then
    echo -e "${RED}错误: docker-compose.yml 不存在于 ${SERVICE_DIR}${NC}"
    exit 1
fi

# 检查 .env 文件
ENV_FILE="${SERVICE_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在于 ${SERVICE_DIR}${NC}"
    echo -e "${YELLOW}正在复制 .env.example 到 .env...${NC}"
    if [ -f "${SERVICE_DIR}/.env.example" ]; then
        cp "${SERVICE_DIR}/.env.example" "${ENV_FILE}"
        echo -e "${GREEN}已创建 .env 文件 - 请在运行服务前配置${NC}"
    else
        echo -e "${RED}错误: .env.example 不存在${NC}"
        exit 1
    fi
fi

# 检查必需的环境变量
check_required_vars() {
    local required_vars=("POSTGRES_PASSWORD" "SECRET_KEY")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "${ENV_FILE}" 2>/dev/null; then
            missing_vars+=("${var}")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${YELLOW}警告: .env 中可能缺少以下环境变量:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${YELLOW}  - ${var}${NC}"
        done
        echo -e "${YELLOW}请在 ${ENV_FILE} 中配置它们${NC}"
    fi

    # 特别检查 LLM_API_KEY
    if ! grep -q "^LLM_API_KEY=" "${ENV_FILE}" 2>/dev/null || grep -q "^LLM_API_KEY=$" "${ENV_FILE}"; then
        echo -e "${YELLOW}警告: LLM_API_KEY 未设置，LLM 功能将不可用${NC}"
    fi
}

check_required_vars

# 切换到服务目录
cd "${SERVICE_DIR}"

# 解析参数
SERVICE_NAME="$1"

echo -e "${BLUE}启动开发环境...${NC}"
echo ""

if [ -n "${SERVICE_NAME}" ]; then
    echo -e "${GREEN}启动服务: ${SERVICE_NAME}${NC}"
    docker compose -f docker-compose.yml up -d "${SERVICE_NAME}"
else
    echo -e "${GREEN}启动所有服务...${NC}"
    docker compose -f docker-compose.yml up -d
fi

# 等待服务健康
echo ""
echo -e "${BLUE}等待服务就绪...${NC}"

# 检查服务健康状态
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker compose ps --services --filter "status=running" | grep -q "^${service}$"; then
            local health_status=$(docker compose ps --format json | grep -A10 "\"name\":\"deepagent-tester-${service}\"" | grep "\"Health\"" | cut -d'"' -f4 2>/dev/null || echo "")
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

# 最终状态检查
echo ""
echo -e "${BLUE}检查服务状态...${NC}"
UNHEALTHY_SERVICES=$(docker compose ps --format json | jq -r 'select(.Health != "healthy" and .State == "running") | .Name' 2>/dev/null || true)

if [ -n "$UNHEALTHY_SERVICES" ]; then
    echo -e "${YELLOW}以下服务状态异常:${NC}"
    echo "$UNHEALTHY_SERVICES" | while read service; do
        echo -e "${YELLOW}  - ${service}${NC}"
    done
    echo ""
    echo -e "${YELLOW}查看日志: docker compose logs [service-name]${NC}"
fi

echo ""
echo -e "${GREEN}开发环境启动完成！${NC}"
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  前端应用:       http://localhost:8085"
echo "  后端 API:       http://localhost:8085/api/v1/"
echo "  后端直连:       http://localhost:8011"
echo "  PostgreSQL:     localhost:5433"
echo "  Redis:          localhost:6380"
echo "  Temporal UI:    http://localhost:8088"
echo "  SonarQube:      http://localhost:9002"
echo "  OWASP ZAP:      http://localhost:8091"
echo ""
echo -e "${BLUE}开发特性:${NC}"
echo "  热重载:         backend/app 和 frontend/src 自动刷新"
echo "  源码挂载:       代码修改即时生效"
echo "  Vite 开发服务器: 前端使用 Vite dev server"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  查看日志:       docker compose logs -f [service]"
echo "  停止服务:       ./bin/stop-dev.sh"
echo "  服务状态:       docker compose ps"
echo ""
