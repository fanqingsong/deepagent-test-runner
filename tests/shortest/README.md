# Shortest 自然语言 E2E 测试

基于 [fanqingsong/shortest](https://github.com/fanqingsong/shortest)，覆盖 AI Test Runner 全部主要功能。

## 目录结构

```
tests/shortest/
├── cases/           # 测试用例（*.test.ts）
├── helpers/         # 共享辅助（认证、路由、提示词）
├── results/         # 运行日志与汇总
├── shortest.config.ts
├── run-all.sh
├── run-one.sh
└── ...
```

## 快速开始

```bash
cd tests/shortest
npm install && npx playwright install chromium
cp .env.local.example .env.local   # 配置 ZHIPU_API_KEY 和管理员账号

npm test                  # 全部测试（cases/*.test.ts）
npm run test:smoke        # 冒烟（登录 + 仪表板）
npm run test:headless     # headless 模式
```

## 功能覆盖

| 测试文件 | 覆盖功能 | npm script |
|----------|----------|------------|
| `cases/smoke.test.ts` | 登录 → 仪表板 | `test:smoke` |
| `cases/login.test.ts` | 登录、注册、忘记密码、登出 | `test:login` |
| `cases/dashboard.test.ts` | Test Dashboard | `test:dashboard` |
| `cases/chat-monitor.test.ts` | Chat Monitor | `test:chat-monitor` |
| `cases/navigation.test.ts` | 全路由导航 | `test:navigation` |

批量：`./run-one.sh chat-monitor.test.ts`、`./run-all.sh`

默认 `BASE_URL`: `http://localhost:8085`

