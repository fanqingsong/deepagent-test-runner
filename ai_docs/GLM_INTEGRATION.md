# GLM (智谱AI) 集成指南

## 概述

Claude Code Test Runner 现在支持使用智谱AI（GLM）的兼容API来进行AI驱动的测试执行。智谱AI提供了与Anthropic Claude API兼容的接口，可以直接用于自然语言测试步骤的理解和执行。

## 配置步骤

### 1. 获取智谱AI API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并登录账号
3. 进入API密钥管理页面
4. 创建新的API密钥
5. 复制您的API密钥

### 2. 配置环境变量

编辑 `.env` 文件，添加以下配置：

```bash
# 智谱AI API配置
ANTHROPIC_API_KEY=your-glm-api-key-here
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
API_TIMEOUT_MS=3000000
```

### 3. 重启服务

```bash
cd /path/to/docker-compose
docker compose restart scheduler-service scheduler-worker
```

### 4. 验证配置

检查服务日志确认智谱AI已正确配置：

```bash
docker compose logs scheduler-worker | grep "Claude interpreter initialized"
```

应该看到类似输出：
```
Claude interpreter initialized with base_url: https://open.bigmodel.cn/api/anthropic
```

## 配置参数说明

### ANTHROPIC_API_KEY
- **描述**: 智谱AI的API密钥
- **格式**: `id.secret` (例如: ``)
- **必需**: 是 (用于AI功能)
- **获取方式**: https://open.bigmodel.cn/

### ANTHROPIC_BASE_URL
- **描述**: 智谱AI的API端点
- **默认值**: `https://open.bigmodel.cn/api/anthropic`
- **说明**: 智谱AI提供的Anthropic兼容API端点

### API_TIMEOUT_MS
- **描述**: API请求超时时间（毫秒）
- **默认值**: `3000000` (50分钟)
- **建议值**: `300000` (5分钟) 足够大多数测试场景

## 使用示例

### 基础测试步骤

配置完成后，您可以像使用Claude一样使用自然语言编写测试步骤：

```json
{
  "name": "GLM AI测试",
  "description": "使用智谱AI进行智能测试执行",
  "test_id": "glm-ai-test",
  "url": "https://example.com",
  "tags": ["glm-ai", "chinese-support"]
}
```

### 添加测试步骤

1. **导航到示例网站**
   ```json
   {"id": 1, "description": "导航到 example.com"}
   ```

2. **等待页面加载完成**
   ```json
   {"id": 2, "description": "等待页面完全加载"}
   ```

3. **查找页面标题并验证**
   ```json
   {"id": 3, "description": "查找页面的标题元素并验证其内容"}
   ```

4. **截图保存当前状态**
   ```json
   {"id": 4, "description": "截取当前页面的屏幕截图"}
   ```

## 智谱AI vs Anthropic Claude

### 相同点
- ✅ API接口完全兼容
- ✅ 支持相同的自然语言理解能力
- ✅ 使用相同的Python SDK (`anthropic`)
- ✅ 配置方式基本一致

### 智谱AI的优势
- 🇨🇳 **中文支持更好**: 对中文指令的理解更准确
- 💰 **成本优势**: 智谱AI的定价可能更有优势
- 🚀 **响应速度**: 国内网络访问更快
- 📋 **合规性**: 符合国内数据合规要求

### 使用建议
- **中文测试**: 优先使用智谱AI
- **英文测试**: 两者都可以，智谱AI也有很好的英文支持
- **混合使用**: 可以在不同测试中使用不同的API

## 高级配置

### 自定义超时时间

对于长时间运行的测试，可以增加超时时间：

```bash
# .env文件
API_TIMEOUT_MS=600000  # 10分钟
```

### 多环境配置

为不同环境配置不同的API密钥：

```bash
# 开发环境使用智谱AI
ANTHROPIC_API_KEY=dev-glm-key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic

# 生产环境使用Anthropic
# ANTHROPIC_API_KEY=prod-anthropic-key
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

### API密钥轮换

定期更换API密钥以提高安全性：

```bash
# 1. 生成新的API密钥
# 2. 更新.env文件
ANTHROPIC_API_KEY=new-glm-api-key

# 3. 重启服务
docker compose restart scheduler-service scheduler-worker
```

## 监控和调试

### 查看API调用日志

```bash
# 实时查看worker日志
docker compose logs -f scheduler-worker

# 过滤AI相关日志
docker compose logs scheduler-worker | grep -i "claude\|glm\|anthropic"
```

### 测试API连接

```bash
# 进入容器
docker compose exec scheduler-worker bash

# 测试Python API
python3 << EOF
import os
from anthropic import Anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
base_url = os.getenv("ANTHROPIC_BASE_URL")

client = Anthropic(api_key=api_key, base_url=base_url)
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hello, 智谱AI!"}]
)
print(response.content[0].text)
EOF
```

### 性能监控

检查API响应时间：

```bash
# 查看测试执行时间
curl -s "http://localhost:8012/api/v1/jobs/{job_id}" | python3 -m json.tool
```

## 故障排除

### 问题1: API连接失败

**症状**: 测试回退到规则模式

**解决方案**:
1. 检查API密钥是否正确
2. 验证BASE_URL设置
3. 测试网络连接: `curl https://open.bigmodel.cn/api/anthropic`
4. 查看防火墙设置

### 问题2: 超时错误

**症状**: 测试执行中断，显示超时

**解决方案**:
1. 增加 `API_TIMEOUT_MS` 值
2. 检查网络稳定性
3. 简化复杂的测试步骤

### 问题3: 理解错误

**症状**: AI无法正确理解指令

**解决方案**:
1. 使用更明确的指令描述
2. 添加更多上下文信息
3. 测试时使用中文指令（智谱AI对中文支持更好）

### 问题4: 配额限制

**症状**: API调用被拒绝

**解决方案**:
1. 检查智谱AI账户余额
2. 验证API调用配额
3. 考虑升级套餐

## 成本优化

### 智谱AI定价参考

- 按token计费
- 输入token + 输出token
- 通常比Anthropic Claude更经济

### 优化建议

1. **使用明确指令**: 减少不必要的token消耗
2. **缓存常用模式**: 避免重复调用API
3. **混合模式**: 简单步骤用规则模式，复杂步骤用AI
4. **批量测试**: 合理安排测试时间，利用优惠

## 中文测试示例

智谱AI对中文的理解特别优秀，以下是一些中文测试示例：

### 表单填写测试
```json
{
  "description": "在登录页面输入用户名和密码"
}
```

### 导航测试
```json
{
  "description": "点击首页的导航菜单，选择产品中心"
}
```

### 验证测试
```json
{
  "description": "验证页面上显示了欢迎消息，并且字体大小合适"
}
```

### 复杂交互
```json
{
  "description": "找到页面右下角的蓝色按钮，点击它，然后等待弹窗出现"
}
```

## 最佳实践

### 1. 指令设计原则
- ✅ **明确具体**: "点击提交按钮" 而不是 "点击那个东西"
- ✅ **包含上下文**: "在登录表单中点击提交按钮"
- ✅ **描述期望结果**: "验证登录成功后跳转到首页"

### 2. 错误处理
- 智谱AI会自动重试失败的操作
- 提供多种执行策略
- 自动回退到规则模式确保稳定性

### 3. 性能考虑
- 合理设置超时时间
- 避免过于复杂的单步指令
- 必要时拆分为多个简单步骤

## 与现有功能集成

### 完全兼容
- ✅ 所有现有测试用例
- ✅ 规则模式回退
- ✅ 测试报告和日志
- ✅ UI界面操作

### 无缝切换
```bash
# 使用智谱AI
ANTHROPIC_API_KEY=glm-key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic

# 切换到Anthropic
ANTHROPIC_API_KEY=anthropic-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

## 技术支持

### 智谱AI官方文档
- API文档: https://open.bigmodel.cn/dev/api
- 控制台: https://open.bigmodel.cn/
- 技术支持: 通过智谱AI官方渠道

### 项目相关
- GitHub Issues: 报告项目相关问题
- 文档: 查看项目README和其他文档
- 社区: 参与讨论和分享经验

## 示例配置文件

### 完整的.env配置
```bash
# 数据库配置
POSTGRES_DB=cc_test_db
POSTGRES_USER=cc_test_user
POSTGRES_PASSWORD=test_password_123

# Redis配置
REDIS_PASSWORD=redis_password_123

# JWT密钥
SECRET_KEY=your-secret-key-change-in-production-12345678

# GLM AI配置 (智谱AI)
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
API_TIMEOUT_MS=3000000
```

### Docker Compose覆盖
```yaml
# docker-compose.override.yml
services:
  scheduler-service:
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}
      - API_TIMEOUT_MS=${API_TIMEOUT_MS}

  scheduler-worker:
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}
      - API_TIMEOUT_MS=${API_TIMEOUT_MS}
```

## 总结

使用智谱AI兼容API，您可以：

- ✅ **保持国内合规**: 数据不跨境
- ✅ **更好的中文支持**: 理解中文指令更准确
- ✅ **成本优势**: 通常比直接使用Anthropic更经济
- ✅ **快速响应**: 国内网络延迟更低
- ✅ **无缝集成**: 配置简单，即插即用

现在就开始使用智谱AI来增强您的测试自动化吧！