# ⚡ 快速配置参考

## 🚀 当前配置状态

### ✅ 已启用功能
- **智谱AI集成**: 已配置并验证
- **中文测试步骤**: 完全支持
- **AI理解**: 真正的自然语言处理
- **自动回退**: API不可用时使用规则模式

### 🔧 环境变量配置

**文件位置**: `/path/to/docker-compose/.env`

```bash
# 智谱AI配置 (当前使用)
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
API_TIMEOUT_MS=3000000
```

### 🔄 切换AI服务提供商

#### 选项1: 智谱AI (当前)
```bash
ANTHROPIC_API_KEY=your-glm-api-key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
```

#### 选项2: Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-your-claude-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

#### 选项3: 其他兼容服务
```bash
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_BASE_URL=https://your-compatible-endpoint
```

### 📡 服务状态检查

```bash
# 检查服务状态
docker compose ps

# 检查环境变量
docker compose exec scheduler-worker env | grep ANTHROPIC

# 查看API调用日志
docker compose logs scheduler-worker | grep "POST.*anthropic"

# 实时监控日志
docker compose logs -f scheduler-worker
```

### 🧪 快速测试

#### 测试1: 英文指令
```json
{
  "description": "Navigate to https://example.com"
}
```

#### 测试2: 中文指令
```json
{
  "description": "导航到示例网站并等待页面加载"
}
```

#### 测试3: 复杂中文指令
```json
{
  "description": "查找页面中的登录按钮，点击它，然后验证是否跳转到首页"
}
```

### ⚙️ 常用配置调整

#### 增加超时时间
```bash
# .env文件
API_TIMEOUT_MS=600000  # 10分钟
```

#### 调整并发数
```yaml
# docker-compose.yml
scheduler-worker:
  command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4
```

#### 启用调试日志
```bash
# docker-compose.yml
environment:
  DEBUG: "1"
  LOG_LEVEL: "DEBUG"
```

### 🔄 服务重启命令

```bash
# 重启单个服务
docker compose restart scheduler-worker

# 重启所有调度服务
docker compose restart scheduler-service scheduler-worker

# 完全重建并启动
docker compose build scheduler-service scheduler-worker
docker compose up -d scheduler-service scheduler-worker
```

### 📊 监控命令

#### 查看测试执行
```bash
# 查看所有jobs
curl http://localhost:8012/api/v1/jobs/ | python3 -m json.tool

# 查看特定job状态
curl http://localhost:8012/api/v1/jobs/{job_id} | python3 -m json.tool
```

#### 查看API使用情况
```bash
# 统计API调用次数
docker compose logs scheduler-worker | grep "POST.*anthropic" | wc -l

# 查看最近的API调用
docker compose logs scheduler-worker --tail=50 | grep "anthropic"
```

### 🎯 测试场景模板

#### 场景1: 网站登录测试
```json
[
  {"description": "导航到登录页面"},
  {"description": "输入用户名和密码"},
  {"description": "点击登录按钮"},
  {"description": "验证登录成功"}
]
```

#### 场景2: 电商购物测试
```json
[
  {"description": "浏览商品列表"},
  {"description": "选择第一个商品加入购物车"},
  {"description": "进入购物车页面"},
  {"description": "点击结算按钮"}
]
```

#### 场景3: 表单提交测试
```json
[
  {"description": "填写联系表单"},
  {"description": "上传头像图片"},
  {"description": "勾选同意条款"},
  {"description": "提交表单并验证成功消息"}
]
```

### 🛠️ 故障排除快速指南

#### 问题: AI不工作
```bash
# 检查API密钥
docker compose exec scheduler-worker env | grep ANTHROPIC_API_KEY

# 检查网络连接
curl https://open.bigmodel.cn/api/anthropic

# 重启服务
docker compose restart scheduler-worker
```

#### 问题: 超时错误
```bash
# 增加超时时间
# .env: API_TIMEOUT_MS=600000
docker compose restart scheduler-worker
```

#### 问题: 理解错误
```bash
# 使用更明确的指令
# 查看AI解释日志
docker compose logs scheduler-worker | grep "details"
```

### 📈 性能优化建议

1. **简单步骤用规则模式**: "等待2秒"
2. **复杂步骤用AI模式**: "找到包含'登录'文字的按钮"
3. **批量测试**: 合理安排测试时间
4. **缓存策略**: 重复使用相同步骤时考虑结果缓存

### 🔗 重要链接

- **前端界面**: http://localhost:8013
- **API文档**: http://localhost:8012/api/docs
- **智谱AI控制台**: https://open.bigmodel.cn/
- **项目根目录**: `/home/fqs/workspace/self/claude-code-test-runner/docker-compose/`

---

**当前配置**: ✅ 智谱AI已启用并正常运行
**测试状态**: ✅ 中英文测试步骤均已验证成功
**生产就绪**: ✅ 可以立即投入使用