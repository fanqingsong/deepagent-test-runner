#!/bin/bash

# 开发环境停止脚本
# Usage: ./bin/stop-dev.sh [service-name]

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
SERVICE_DIR="${PROJECT_ROOT}/platform"

# 检查服务目录
if [ ! -d "${SERVICE_DIR}" ]; then
    echo -e "${RED}错误: platform 目录不存在于 ${SERVICE_DIR}${NC}"
    exit 1
fi

# 检查 docker-compose.yml
if [ ! -f "${SERVICE_DIR}/docker-compose.yml" ]; then
    echo -e "${RED}错误: docker-compose.yml 不存在于 ${SERVICE_DIR}${NC}"
    exit 1
fi

# 切换到服务目录
cd "${SERVICE_DIR}"

# 解析参数
SERVICE_NAME="$1"

# 清理僵尸进程函数
cleanup_processes() {
    echo -e "${BLUE}检查僵尸进程...${NC}"

    local pids=$(pgrep -f "docker compose" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}发现 docker compose 进程: $pids${NC}"
        read -p "是否终止这些进程? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$pids" | xargs kill -TERM 2>/dev/null || true
            sleep 2
            echo -e "${GREEN}进程已终止${NC}"
        fi
    fi

    # 检查僵尸进程
    local zombie_pids=$(ps aux | grep -E "\[docker-compose\] <defunct>" | awk '{print $2}' 2>/dev/null || true)
    if [ -n "$zombie_pids" ]; then
        echo -e "${YELLOW}发现僵尸进程，正在清理...${NC}"
        for pid in $zombie_pids; do
            echo "  清理僵尸进程 PID: $pid"
            kill -KILL $pid 2>/dev/null || true
        done
    fi
}

# 检查端口占用
check_ports() {
    echo -e "${BLUE}检查端口占用...${NC}"

    local ports=(5433 6380 7233 8088 8011 8085 5174 9002 8091)
    local occupied_ports=()

    for port in "${ports[@]}"; do
        if command -v lsof >/dev/null 2>&1; then
            local pid=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$pid" ]; then
                occupied_ports+=("$port (PID: $pid)")
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -tuln 2>/dev/null | grep -q ":$port "; then
                occupied_ports+=("$port")
            fi
        fi
    done

    if [ ${#occupied_ports[@]} -gt 0 ]; then
        echo -e "${YELLOW}以下端口仍被占用:${NC}"
        for port in "${occupied_ports[@]}"; do
            echo -e "${YELLOW}  - $port${NC}"
        done
    else
        echo -e "${GREEN}所有端口已释放${NC}"
    fi
}

echo -e "${BLUE}停止开发环境...${NC}"
echo ""

if [ -n "${SERVICE_NAME}" ]; then
    echo -e "${GREEN}停止服务: ${SERVICE_NAME}${NC}"
    docker compose -f docker-compose.yml stop "${SERVICE_NAME}"
    echo -e "${GREEN}服务 ${SERVICE_NAME} 已停止${NC}"
else
    echo -e "${GREEN}停止所有服务...${NC}"
    docker compose -f docker-compose.yml down
    echo -e "${GREEN}所有服务已停止${NC}"
fi

# 等待服务停止
sleep 2

# 检查是否仍有容器运行
RUNNING_CONTAINERS=$(docker compose ps --quiet 2>/dev/null || true)
if [ -n "$RUNNING_CONTAINERS" ]; then
    echo -e "${YELLOW}警告: 部分容器仍在运行${NC}"
    docker compose ps
fi

# 可选清理
echo ""
read -p "是否运行清理检查? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cleanup_processes
    check_ports
fi

# 可选资源清理
echo ""
read -p "是否清理未使用的 Docker 资源? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}清理 Docker 资源...${NC}"

    echo "清理停止的容器..."
    docker container prune -f

    echo "清理未使用的镜像..."
    docker image prune -f

    echo "清理未使用的网络..."
    docker network prune -f

    echo -e "${GREEN}Docker 清理完成${NC}"
fi

echo ""
echo -e "${GREEN}开发环境已停止！${NC}"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  启动服务:       ./bin/start-dev.sh"
echo "  查看容器:       docker ps -a"
echo "  删除数据卷:     docker compose down -v  (警告: 删除数据)"
echo ""
