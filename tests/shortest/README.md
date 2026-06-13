# Shortest 自然语言 E2E 测试

基于 [fanqingsong/shortest](https://github.com/fanqingsong/shortest)，使用自然语言 + Playwright 测试 AI Test Runner 平台。

## 快速开始

```bash
cd tests/shortest
npm install
npx playwright install chromium
cp .env.local.example .env.local   # 填入 ZHIPU_API_KEY 和测试账号

npm test                  # 全部测试（有界面）
npm run test:headless     # headless 模式
npm run test:smoke        # 冒烟测试
```

## 测试文件

| 文件 | 说明 |
|------|------|
| `smoke.test.ts` | 登录 → 仪表板冒烟流程 |
| `login.test.ts` | 登录相关 |
| `dashboard.test.ts` | 仪表板 |
| `tests-management.test.ts` | 测试管理 |
| `schedules.test.ts` | 调度配置 |

默认 `BASE_URL`: `http://localhost:8085`
