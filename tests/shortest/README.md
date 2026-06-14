# Shortest 自然语言 E2E 测试

基于 [fanqingsong/shortest](https://github.com/fanqingsong/shortest)，覆盖 AI Test Runner 全部主要功能。

## 快速开始

```bash
cd tests/shortest
npm install && npx playwright install chromium
cp .env.local.example .env.local   # 配置 ZHIPU_API_KEY 和管理员账号

npm test                  # 全部测试
npm run test:smoke        # 冒烟（登录 + 仪表板）
npm run test:headless     # headless 模式
```

## 功能覆盖

| 测试文件 | 覆盖功能 | npm script |
|----------|----------|------------|
| `smoke.test.ts` | 登录 → 仪表板 | `test:smoke` |
| `login.test.ts` | 登录、注册、忘记密码、登出 | `test:login` |
| `dashboard.test.ts` | Test Dashboard、角色视图、时间范围 | `test:dashboard` |
| `test-cases.test.ts` | Test Cases 工作区 | `test:test-cases` |
| `test-cases-marketplace.test.ts` | Test Case Marketplace | `test:test-cases-marketplace` |
| `test-suites.test.ts` | Test Suites 工作区 | `test:suites` |
| `test-suites-marketplace.test.ts` | Test Suite Marketplace | `test:suites-marketplace` |
| `token-usage.test.ts` | Token Usage Dashboard | `test:token-usage` |
| `token-budget.test.ts` | Budget Management | `test:token-budget` |
| `token-quota.test.ts` | Quota Management | `test:token-quota` |
| `token-alert.test.ts` | Alert Management | `test:token-alert` |
| `token-analytics.test.ts` | Token Analytics | `test:token-analytics` |
| `users.test.ts` | User Management | `test:users` |
| `roles.test.ts` | Role Management | `test:roles` |
| `reviews.test.ts` | Review Management | `test:reviews` |
| `profile.test.ts` | My Profile | `test:profile` |
| `chat-monitor.test.ts` | Chat Monitor | `test:chat-monitor` |
| `monitoring.test.ts` | System Monitoring | `test:monitoring` |
| `nanjing-weather.test.ts` | Nanjing Weather | `test:weather` |
| `chat-assistant.test.ts` | 浮动聊天助手 | `test:chat` |
| `navigation.test.ts` | 全路由导航（一次跑完所有页面） | `test:navigation` |

批量运行：

```bash
npm run test:token    # 全部 Token Management
npm run test:admin    # 全部 System Management
```

## 约定

- 断言文案与 UI **英文标题**一致（如 `Test Dashboard`，非「测试仪表板」）
- 通过 URL hash 导航（sidebar 默认折叠时更可靠）
- 需要管理员账号访问 System Management 页面

默认 `BASE_URL`: `http://localhost:8085`
