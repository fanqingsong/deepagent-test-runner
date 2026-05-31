# Nginx反向代理配置

## 概述

Nginx作为API网关，反向代理所有后端微服务：
- 统一的API入口（端口8080）
- 负载均衡能力
- WebSocket支持（Dashboard实时更新）
- 静态文件缓存
- Gzip压缩

## ⚠️ 重要说明

### 前端访问方式

**开发环境** (推荐):
```
前端: http://localhost:5173
```
直接访问Vite开发服务器以获得：
- ✅ 热模块替换 (HMR)
- ✅ 快速刷新
- ✅ 开发工具支持
- ✅ 源码映射

**生产环境**:
```
前端: http://localhost:8080/
```
通过Nginx访问打包后的静态文件

## 服务端口映射

| 服务 | 容器内部端口 | 直接访问 | 通过Nginx |
|------|-------------|---------|----------|
| 前端(Vite) | 5173 | ✅ http://localhost:5173 | ⚠️ 生产环境 |
| Test Case API | 8001 | http://localhost:8011 | http://localhost:8080/api/v1/test-definitions |
| Scheduler API | 8002 | http://localhost:8012 | http://localhost:8080/api/v1/schedules |
| Dashboard API | 8003 | http://localhost:8013 | http://localhost:8080/api/dashboard |

## 使用方式

### 开发环境 (推荐)

```bash
# 启动所有服务
docker compose up -d

# 访问前端 - 直接连接Vite
open http://localhost:5173

# API调用 - 可以直接调用或通过nginx
curl http://localhost:8080/api/v1/schedules/
curl http://localhost:8080/api/dashboard?days=30
```

### 生产环境配置

1. 构建前端静态文件：
```bash
cd dashboard-service/frontend
npm run build
```

2. 修改nginx配置指向打包后的文件

3. 通过nginx访问：
```bash
open http://localhost:8080/
```

## API路由规则

通过Nginx统一访问后端API：

**Test Case Service:**
- `/api/v1/test-definitions` → 测试定义管理
- `/api/v1/test-steps` → 测试步骤管理

**Scheduler Service:**
- `/api/v1/schedules` → 调度配置管理
- `/api/v1/test-generation` → AI测试生成

**Dashboard Service:**
- `/api/dashboard` → 仪表板统计数据
- `/api/test-runs` → 测试运行记录
- `/ws` → WebSocket实时更新

## 健康检查

```bash
# Nginx健康检查
curl http://localhost:8080/health

# 检查所有服务状态
docker ps
```

## 故障排查

### API返回307重定向
在URL末尾添加斜杠 `/`：
```bash
curl http://localhost:8080/api/v1/schedules/
```

### 前端白屏问题
**开发环境**: 使用 http://localhost:5173 而不是 http://localhost:8080/

**原因**: Vite开发服务器的HMR和模块解析特性需要直接连接
