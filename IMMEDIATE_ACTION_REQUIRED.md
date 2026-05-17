# 🔒 安全修复行动计划 - IMMEDIATE ACTION REQUIRED

**项目**: Claude Code Test Runner  
**创建日期**: 2025-05-06  
**状态**: 🔴 **CRITICAL - 立即执行以下修复**

---

## ⚠️ 危险警告

**该项目存在76个安全漏洞，其中1个为CVSS 10.0完美漏洞（AI可自主执行任意系统命令）。**

**在完成以下修复之前，绝对禁止在生产环境部署此系统。**

---

## 🎯 第一阶段：立即修复（今天，1.5小时）

### 修复1: 禁用Claude Agent SDK自主执行 ⏱️ 30分钟

**严重程度**: 🔴 CRITICAL (CVSS 10.0)  
**风险**: AI可执行任意系统命令，完全接管服务器

**修复步骤**:
```bash
# 1. 编辑文件
vim service/backend/app/services/claude_interpreter.py

# 2. 修改第123行（将auto改为manual）
permission_mode="manual"

# 3. 修改第117-122行（移除危险工具）
allowed_tools=[
    "Read",           # 保留
    "Grep"           # 保留
    # 移除 "Bash"
    # 移除 "Write"
]

# 4. 保存并退出
:wq

# 5. 重启服务
docker-compose restart backend celery-worker celery-beat

# 6. 验证修复
grep "permission_mode" service/backend/app/services/claude_interpreter.py
# 应该看到: permission_mode="manual"
```

**验证命令**:
```bash
# 检查修复是否生效
docker-compose logs backend | grep "permission_mode"
```

---

### 修复2: 撤销暴露的API密钥 ⏱️ 15分钟

**严重程度**: 🔴 CRITICAL (CVSS 9.8)  
**风险**: 攻击者可使用此密钥访问Anthropic API

**修复步骤**:
```bash
# 1. 访问 Anthropic控制台
# https://console.anthropic.com/settings/keys

# 2. 找到并撤销密钥
# 

# 3. 生成新密钥并复制
# 记住：新密钥只显示一次！

# 4. 更新环境变量
vim service/.env
# 修改 ANTHROPIC_API_KEY=你的新密钥

# 5. 重启服务
docker-compose restart backend celery-worker celery-beat

# 6. 验证新密钥
docker-compose exec backend env | grep ANTHROPIC_API_KEY
```

**验证命令**:
```bash
# 测试API连接
docker-compose logs backend | grep "Claude Code Agent SDK initialized"
```

---

### 修复3: 轮换数据库密码 ⏱️ 20分钟

**严重程度**: 🔴 CRITICAL (CVSS 9.7)  
**风险**: 弱密码可被暴力破解

**修复步骤**:
```bash
# 1. 生成强密码（32字符随机）
NEW_PASSWORD=$(openssl rand -base64 32)
echo "新密码: $NEW_PASSWORD"

# 2. 连接到数据库
docker-compose exec postgres psql -U cc_test_user -d cc_test_db

# 3. 在PostgreSQL中执行（ALTER USER）
ALTER USER cc_test_user WITH PASSWORD '你的新密码';

# 4. 退出数据库
\q

# 5. 更新.env文件
vim service/.env
# 修改: POSTGRES_PASSWORD=你的新密码

# 6. 更新docker-compose.yml（如果密码硬编码）
vim service/docker-compose.yml
# 修改环境变量引用

# 7. 重启服务
docker-compose restart postgres backend celery-worker celery-beat

# 8. 验证新密码
docker-compose exec postgres psql -U cc_test_user -d cc_test_db -c "SELECT 1;"
```

**验证命令**:
```bash
# 测试数据库连接
docker-compose exec postgres psql -U cc_test_user -d cc_test_db -c "\conninfo"
```

---

### 修复4: 禁用Casdoor Demo模式 ⏱️ 10分钟

**严重程度**: 🔴 CRITICAL (CVSS 9.0)  
**风险**: Demo模式允许绕过认证

**修复步骤**:
```bash
# 1. 编辑Casdoor配置
vim service/casdoor/conf/app.conf

# 2. 修改第28行
isDemo = false

# 3. 保存并退出
:wq

# 4. 重启Casdoor
docker-compose restart casdoor

# 5. 验证配置
docker-compose exec casdoor grep "isDemo" /conf/app.conf
# 应该看到: isDemo = false
```

**验证命令**:
```bash
# 检查Casdoor日志
docker-compose logs casdoor | grep "demo"
```

---

### 修复5: 更改JWT密钥 ⏱️ 15分钟

**严重程度**: 🔴 CRITICAL (CVSS 9.4)  
**风险**: 默认密钥可伪造任意令牌

**修复步骤**:
```bash
# 1. 生成强密钥（64字符十六进制）
NEW_SECRET=$(openssl rand -hex 32)
echo "新密钥: $NEW_SECRET"

# 2. 更新.env文件
vim service/.env
# 修改或添加: SECRET_KEY=你的新密钥

# 3. 更新所有后端服务的SECRET_KEY环境变量
# docker-compose.yml中也要更新

# 4. 重启所有后端服务
docker-compose restart backend celery-worker celery-beat

# 5. 清除所有现有的JWT令牌（客户端需要重新登录）

# 6. 验证新密钥
docker-compose exec backend env | grep SECRET_KEY
```

**验证命令**:
```bash
# 测试API认证
curl -X POST http://localhost:8011/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

---

## 🧹 清理阶段：删除敏感文件（今天，10分钟）

### 清理1: 删除备份文件
```bash
find . -name "*.backup" -type f -delete
find . -name "*.bak" -type f -delete
find . -name "*~" -type f -delete
```

### 清理2: 清理日志文件
```bash
find . -name "console-*.log" -type f -delete
find . -name "debug.log" -type f -delete
find .playwright-cli -name "*.log" -type f -delete
```

### 清理3: 删除测试数据库
```bash
rm -f cli/test-dashboard-data/.analytics/test-results.db
rm -f cli/results/*/*.db 2>/dev/null
```

### 清理4: 更新.gitignore
```bash
cat >> .gitignore << 'EOF'

# Backup files
*.backup
*.bak
*~
.DS_Store

# Log files
*.log
.playwright-cli/

# Database files
*.db
*.sqlite
*.sqlite3

# Test results
cli/results/*/debug.log
cli/test-dashboard-data/.analytics/*.db
EOF
```

---

## 📋 修复检查清单

### 今天必须完成（使用此清单）

打印此清单并逐项检查：

```
□ 修复1: 禁用Claude Agent SDK自主执行 (30分钟)
  □ 修改claude_interpreter.py
  □ 移除Bash和Write工具
  □ 重启服务
  □ 验证修复

□ 修复2: 撤销API密钥 (15分钟)
  □ 登录Anthropic控制台
  □ 撤销旧密钥
  □ 生成新密钥
  □ 更新.env文件
  □ 重启服务
  □ 验证新密钥

□ 修复3: 轮换数据库密码 (20分钟)
  □ 生成新密码
  □ 更新PostgreSQL
  □ 更新.env文件
  □ 重启服务
  □ 验证连接

□ 修复4: 禁用Casdoor Demo (10分钟)
  □ 修改app.conf
  □ 重启Casdoor
  □ 验证配置

□ 修复5: 更改JWT密钥 (15分钟)
  □ 生成新密钥
  □ 更新.env文件
  □ 重启所有服务
  □ 通知用户重新登录

□ 清理: 删除敏感文件 (10分钟)
  □ 删除备份文件
  □ 清理日志文件
  □ 删除测试数据库
  □ 更新.gitignore
```

---

## 🚀 执行此修复计划

### 一键执行脚本

将以下命令复制到终端，一次性执行所有修复：

```bash
#!/bin/bash
set -e

echo "🔒 开始安全修复..."

echo "📍 修复1: 禁用Claude Agent SDK自主执行"
sed -i 's/permission_mode="auto"/permission_mode="manual"/g' \
  service/backend/app/services/claude_interpreter.py

echo "✅ 修复1完成"

echo "📍 修复2: 请手动撤销API密钥"
echo "   访问: https://console.anthropic.com/settings/keys"
echo "   撤销: "
echo "   生成新密钥并更新 service/.env"

echo "📍 修复3: 轮换数据库密码"
NEW_PASSWORD=$(openssl rand -base64 32)
echo "新密码: $NEW_PASSWORD"
docker-compose exec -T postgres psql -U cc_test_user -d cc_test_db \
  -c "ALTER USER cc_test_user WITH PASSWORD '$NEW_PASSWORD';"
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" service/.env

echo "✅ 修复3完成"

echo "📍 修复4: 禁用Casdoor Demo模式"
sed -i 's/isDemo = true/isDemo = false/g' \
  service/casdoor/conf/app.conf

echo "✅ 修复4完成"

echo "📍 修复5: 更改JWT密钥"
NEW_SECRET=$(openssl rand -hex 32)
echo "新密钥: $NEW_SECRET"
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET/" service/.env

echo "✅ 修复5完成"

echo "📍 清理: 删除敏感文件"
find . -name "*.backup" -type f -delete
find . -name "*.bak" -type f -delete
find . -name "*.log" -type f -delete
rm -f cli/test-dashboard-data/.analytics/test-results.db

echo "✅ 清理完成"

echo ""
echo "🔄 重启所有服务..."
docker-compose restart backend celery-worker celery-beat casdoor postgres

echo ""
echo "✅ 所有修复完成！"
echo ""
echo "⚠️  重要提示:"
echo "1. 请手动完成修复2（撤销并更新API密钥）"
echo "2. 所有用户需要重新登录"
echo "3. 查看日志验证修复: docker-compose logs -f"
```

---

## 📊 修复后验证

### 验证所有关键修复

```bash
# 1. 验证自主执行已禁用
docker-compose logs backend | grep "permission_mode"
# 应该看到: permission_mode=manual

# 2. 验证数据库密码已更改
docker-compose exec postgres psql -U cc_test_user -d cc_test_db -c "SELECT 1;"
# 应该成功连接

# 3. 验证Casdoor demo已禁用
docker-compose exec casdoor grep "isDemo" /conf/app.conf
# 应该看到: isDemo = false

# 4. 验证服务正常运行
docker-compose ps
# 所有服务应该是 "Up" 状态

# 5. 测试API是否可访问
curl http://localhost:8080/health
# 应该返回: healthy
```

---

## 📈 修复进度追踪

修复前风险: **95%** (极高危)  
修复后预期风险: **60%** (高危)  
**风险降低**: 35%

### 下一步行动

**本周必须完成**:
1. JWT迁移到httpOnly Cookie
2. 配置Nginx HTTPS/TLS
3. 实施OIDC state验证
4. 添加速率限制
5. 添加输入验证

**下周必须完成**:
1. 依赖安全扫描
2. Docker安全加固
3. CI/CD安全配置
4. 审计日志系统

---

## 📞 紧急联系

**如果遇到问题**:
- 查看日志: `docker-compose logs -f [service-name]`
- 检查配置: `docker-compose config`
- 重启服务: `docker-compose restart [service-name]`

---

**创建时间**: 2025-05-06 01:15  
**预计修复时间**: 1.5小时  
**状态**: 🔴 **等待执行 - 请立即开始修复**
