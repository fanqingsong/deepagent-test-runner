# 🔒 安全工具集成指南

本文档说明如何使用已集成的SonarQube和OWASP ZAP安全工具。

---

## 📊 服务状态

当前运行的安全工具：

| 服务 | 状态 | 端口 | 访问地址 |
|------|------|------|---------|
| SonarQube | 启动中 | 9000 | http://localhost:9000/sonarqube |
| SonarQube DB | ✅ 健康 | 5432 | (内部) |
| OWASP ZAP | 启动中 | 8090 | http://localhost:8090 |

---

## 🔍 SonarQube - 代码质量和安全分析

### 访问SonarQube

1. 等待服务完全启动（约1-2分钟）
2. 访问: http://localhost:9000/sonarqube
3. 默认凭据:
   - 用户名: `admin`
   - 密码: `admin`

首次登录后会提示修改密码。

### 配置SonarQube

#### 1. 创建项目

```bash
# 使用SonarQube Scanner CLI
cd service/backend

# 生成token并配置
export SONAR_TOKEN="your-sonarqube-token"

# 运行扫描
sonar-scanner \
  -Dsonar.projectKey=claude-test-runner \
  -Dsonar.sources=app \
  -Dsonar.host.url=http://localhost:9000/sonarqube \
  -Dsonar.login=${SONAR_TOKEN}
```

#### 2. 使用配置文件

项目已包含SonarQube配置文件：

- **后端**: `service/backend/sonar-project.properties`
- **CLI**: `cli/sonar-project.properties`

配置内容包括：
- 项目密钥: `claude-code-test-runner:backend` / `claude-code-test-runner:cli`
- 源代码位置
- 排除规则
- 覆盖率报告路径

#### 3. 扫描Python代码

```bash
cd service/backend

# 安装SonarQube Scanner
pip install sonarqube-scanner

# 运行扫描
sonar-scanner \
  -Dproject.settings=sonar-project.properties \
  -Dsonar.host.url=http://localhost:9000/sonarqube \
  -Dsonar.login=${SONAR_TOKEN}
```

#### 4. 扫描JavaScript/TypeScript代码

```bash
cd cli

# 安装依赖
npm install

# 运行测试并生成覆盖率报告
npm run test

# 运行SonarQube扫描
sonar-scanner \
  -Dproject.settings=sonar-project.properties \
  -Dsonar.host.url=http://localhost:9000/sonarqube \
  -Dsonar.login=${SONAR_TOKEN}
```

### SonarQube质量门配置

在SonarQube UI中配置质量门：

1. 访问: Quality Profiles → Create Profile
2. 设置规则:
   - 代码覆盖率 > 80%
   - 安全热点 = 0
   - Bug数量 < 10
   - 漏洞数量 = 0

---

## 🛡️ OWASP ZAP - 动态应用安全测试

### 访问ZAP

1. ZAP Web UI: http://localhost:8090
2. ZAP API: http://localhost:8090/JSON

### 基本使用

#### 1. Spider扫描

使用提供的JavaScript脚本：

```bash
cd service/zap

# 安装依赖
npm install node-fetch

# 运行spider扫描
TARGET_URL=http://localhost:8080 \
ZAP_API_URL=http://localhost:8090 \
node spider-scan.js
```

#### 2. 主动扫描

```bash
# 使用ZAP API
curl http://localhost:8090/JSON/ascan/action/scan/ \
  ?url=http://localhost:8080 \
  &recurse=true
```

#### 3. 生成报告

```bash
# 生成HTML报告
python scripts/report-html.py zap-alerts.json report.html
```

### ZAP配置文件

ZAP配置位于: `service/zap/zap.yaml`

可配置项：
- Spider深度和持续时间
- 主动扫描策略
- 报告格式（HTML/JSON/XML）

---

## 🔄 CI/CD集成

### GitHub Actions工作流

已创建安全扫描工作流: `.github/workflows/security-scan.yml`

工作流包含：
1. SonarQube代码扫描
2. OWASP ZAP动态扫描
3. 依赖项漏洞扫描
4. 安全报告生成

### 手动触发扫描

```bash
# 运行完整安全扫描
cd .github/workflows
gh workflow run security-scan.yml
```

---

## 📋 常用命令

### 查看服务状态

```bash
docker compose ps sonarqube-db sonarqube owasp-zap
```

### 查看服务日志

```bash
# SonarQube日志
docker compose logs -f sonarqube

# ZAP日志
docker compose logs -f owasp-zap
```

### 重启服务

```bash
docker compose restart sonarqube owasp-zap
```

### 停止服务

```bash
docker compose stop sonarqube-db sonarqube owasp-zap
```

---

## 🔧 故障排除

### SonarQube无法访问

**问题**: 无法访问 http://localhost:9000/sonarqube

**解决方案**:
```bash
# 检查服务状态
docker compose ps sonarqube

# 查看日志
docker compose logs sonarqube

# 等待服务完全启动（可能需要2-3分钟）
docker compose logs -f sonarqube | grep "SonarQube is operational"
```

### ZAP扫描失败

**问题**: ZAP spider或扫描失败

**解决方案**:
```bash
# 确保目标应用正在运行
curl http://localhost:8080/health

# 检查ZAP状态
curl http://localhost:8090/JSON/core/view/version/

# 重启ZAP
docker compose restart owasp-zap
```

### 数据库连接问题

**问题**: SonarQube无法连接到数据库

**解决方案**:
```bash
# 检查数据库状态
docker compose ps sonarqube-db

# 查看数据库日志
docker compose logs sonarqube-db

# 重启服务
docker compose restart sonarqube-db sonarqube
```

---

## 📚 更多资源

- [SonarQube文档](https://docs.sonarqube.org/)
- [OWASP ZAP文档](https://www.zaproxy.org/docs/)
- [SonarQube Python Analyzer](https://github.com/SonarSource/sonar-python)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**最后更新**: 2026-05-05
**版本**: 1.0
**维护者**: DevOps Team
