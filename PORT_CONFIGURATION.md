# DeepAgent Test Runner - Port Configuration

## Port Mapping (避免与 Foundation 项目冲突)

### 主机端口 → 容器端口映射

| 服务 | 主机端口 | 容器端口 | 说明 | 避免冲突 |
|------|----------|----------|------|----------|
| **Nginx** | **8085** | 80 | 反向代理 | Foundation 使用 8081, 8082, 8084 |
| **Frontend** | **5174** | 5173 | React 前端 | Foundation 使用 5173 |
| **Backend** | **8011** | 8001 | FastAPI 后端 | Foundation 内部使用 8001 |
| **PostgreSQL** | **5433** | 5432 | 数据库 | Foundation 使用 5434 |
| **Redis** | **6380** | 6379 | 缓存 | Foundation 内部使用 6379 |
| **Casdoor** | **8006** | 8000 | 认证服务 | Foundation 使用 8003 |
| **SonarQube** | **9002** | 9000 | 代码分析 | Foundation 使用 9000-9001 |
| **OWASP ZAP** | **8091** | 8080 | 安全测试 | Foundation 使用 8082 |

### 访问端点

**前端访问:**
- 主页: http://localhost:8085
- 直接前端: http://localhost:5174

**后端API:**
- API: http://localhost:8011
- API文档: http://localhost:8011/docs

**数据库管理:**
- PostgreSQL: localhost:5433
- Redis: localhost:6380

**其他服务:**
- Casdoor: http://localhost:8006
- SonarQube: http://localhost:9002/sonarqube
- OWASP ZAP: http://localhost:8091

### 与 Foundation 项目端口对比

| 端口 | DeepAgent Test Runner | Foundation | 状态 |
|------|----------------------|-----------|------|
| 5173 | ❌ (改为 5174) | ✅ (Nginx前端) | 已解决冲突 |
| 8001 | ✅ (内部端口) | ✅ (内部端口) | 无冲突 |
| 8003 | ❌ (改为 8006) | ✅ (Casdoor) | 已解决冲突 |
| 8080 | ❌ (改为 8085) | ❌ | 已解决冲突 |
| 8082 | ❌ | ✅ (Adminer) | 无冲突 |
| 9000-9001 | ❌ (改为 9002) | ✅ (MinIO) | 已解决冲突 |
| 5434 | ❌ (使用 5433) | ✅ (PostgreSQL) | 无冲突 |

### 启动服务

使用新的端口配置启动服务：

```bash
cd /home/song/workspace/me/deepagent-test-runner/service
docker compose up -d
```

### 验证服务状态

检查所有服务是否正常运行：

```bash
docker ps --filter "name=cc-test"
```

测试主要端点：

```bash
# 测试前端
curl http://localhost:8085

# 测试后端API
curl http://localhost:8011/health

# 测试数据库连接
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db
```
