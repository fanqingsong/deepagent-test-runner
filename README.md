# DeepAgent Test Runner

<div align="center">

![DeepAgent Test Runner](https://img.shields.io/badge/AI-Powered%20E2E%20Testing-blue)
![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Desktop-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

[English](#english-version) | [中文文档](#中文文档)

</div>

---

## 中文文档

### 🎯 项目简介

**DeepAgent Test Runner** 是一款基于人工智能的端到端（E2E）自动化测试平台，重新定义了软件测试的编写与执行方式。通过自然语言驱动测试，结合先进的 LLM 技术和浏览器自动化能力，让测试创建变得前所未有的简单。

### ✨ 核心特性

#### 🤖 AI 驱动的测试创作
- **自然语言定义测试**：用描述性语言编写测试用例，无需编程基础
- **智能测试生成**：GLM-4 Plus 大模型驱动的测试计划生成与脚本编写
- **自适应元素定位**：AI 基于上下文而非固定选择器定位元素，自动适应 UI 变化
- **可视化验证**：支持基于视觉外观的 UI 状态验证

#### 🎭 DeepAgents 测试编排
- **DeepAgents 框架集成**：采用业界领先的 DeepAgents 框架进行测试编排
- **沙箱执行环境**：安全的 Playwright 脚本执行环境
- **确定性执行模式**：支持预生成脚本的确定性测试执行
- **实时结果反馈**：测试执行过程中实时更新进度和结果

#### 📊 完整的可观测性
- **Langfuse LLM 监控**：追踪每次 LLM 调用的 Token 使用量、成本和性能
- **测试执行分析**：详细的测试步骤结果、截图和 Playwright 追踪
- **多维度仪表板**：测试通过率、执行时间、成本趋势等可视化图表
- **历史数据对比**：支持测试结果的时序分析和趋势预测

#### 🛠️ 企业级功能
- **RBAC 权限系统**：细粒度的测试套件和工作空间权限管理
- **测试评审流程**：内置同行评审机制，确保测试质量
- **版本控制**：完整的测试用例和套件版本历史
- **标签系统**：灵活的测试分类和组织方式
- **工作空间隔离**：多租户支持，数据完全隔离

#### 🌐 开放生态
- **测试市场**：公开的测试用例和套件市场，支持分享与复用
- **RESTful API**：完整的 API 接口，支持与 CI/CD 集成
- **Cron 调度**：基于 Temporal 的可靠定时任务调度
- **Webhook 通知**：测试结果实时推送

### 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (:8080)                             │
│                   (统一入口 & 反向代理)                            │
└─────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│  React Frontend      │    │    FastAPI Backend (:8011)       │
│  (Vite Dev :5173)    │    │  ┌────────────────────────────┐  │
│                      │    │  │ - Test Composer Agent      │  │
│  - 测试编辑器         │    │  │ - Script Generator         │  │
│  - 分析仪表板         │    │  │ - Execution Service        │  │
│  - 测试市场           │    │  │ - Analytics Service        │  │
└──────────────────────┘    │  └────────────────────────────┘  │
                             └──────────────────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────┐
        │                                │                            │
        ▼                                ▼                            ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
│  PostgreSQL      │   │  Temporal Server  │   │  Redis              │
│  (:5433)         │   │  (:7233)          │   │  (:6380)             │
│                  │   │                   │   │                      │
│  - 测试定义       │   │  - 调度引擎       │   │  - 任务队列          │
│  - 执行结果       │   │  - 工作流编排     │   │  - 会话缓存          │
└──────────────────┘   └───────────────────┘   └─────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────┐
        │                                │                            │
        ▼                                ▼                            ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
│  Playwright      │   │  GLM LLM API      │   │  Langfuse Stack     │
│  Browser         │   │  (智谱 AI)         │   │                     │
│                  │   │                   │   │  - LLM 监控         │
│  - 浏览器自动化   │   │  - 测试计划生成   │   │  - 成本追踪         │
│  - DOM 提取       │   │  - 脚本生成       │   │  - 性能分析         │
└──────────────────┘   └───────────────────┘   └─────────────────────┘
```

### 🔧 核心组件

| 组件 | 技术栈 | 端口 | 功能 |
|------|--------|------|------|
| **测试编排器** | DeepAgents + LangChain | - | AI 测试计划生成与脚本编写 |
| **脚本生成器** | GLM-4 Plus | - | 自然语言转 Playwright 脚本 |
| **执行引擎** | Playwright + Temporal | - | 测试执行与结果收集 |
| **API 服务** | FastAPI | 8011 | 统一后端 API |
| **前端** | React + Vite | 5173 (开发) | Web UI |
| **数据库** | PostgreSQL | 5433 | 数据持久化 |
| **缓存** | Redis | 6380 | 会话与任务队列 |
| **调度器** | Temporal | 7233 | 工作流编排 |

### 🚀 快速开始

#### 环境要求

- Docker & Docker Compose
- 8GB+ 内存
- Linux/macOS/WSL2

#### 一键启动

```bash
# 克隆项目
git clone https://github.com/your-org/deepagent-test-runner.git
cd deepagent-test-runner

# 启动开发环境（包含热重载）
./start-dev.sh

# 启动生产环境
./start-prod.sh
```

#### 访问服务

- **Web 控制台**: http://localhost:8080
- **API 文档**: http://localhost:8011/docs
- **Langfuse 监控**: http://localhost:3000

#### 停止服务

```bash
# 停止开发环境
./stop-dev.sh

# 停止生产环境
./stop-prod.sh
```

### 📖 使用指南

#### 1. 创建测试用例

在测试编辑器中，用自然语言描述测试步骤：

```
1. 打开 https://example.com
2. 点击登录按钮
3. 输入用户名和密码
4. 提交表单
5. 验证登录成功消息
```

AI 将自动生成可执行的 Playwright 脚本。

#### 2. 配置调度

设置 Cron 表达式，实现定时自动化测试：

```yaml
cron: "0 2 * * *"  # 每天凌晨 2 点执行
environment: production
```

#### 3. 查看分析报告

实时查看测试执行结果、通过率趋势和成本分析。

### 🎨 设计系统

采用 IBM Carbon Design System，提供企业级用户体验：

- **零圆角设计**：专业、简洁的视觉风格
- **IBM Plex Sans** 字体家族
- **8px 栅格系统**：精确的布局规范
- **单一强调色**：IBM Blue 60 (#0f62fe)
- **响应式设计**：支持 320px 到 1584px 全覆盖

详见 [DESIGN.md](DESIGN.md)

### 🔌 API 集成

#### 测试执行 API

```bash
# 创建测试运行
curl -X POST http://localhost:8011/api/v1/test-runs/ \
  -H "Content-Type: application/json" \
  -d '{
    "test_definition_id": 123,
    "environment": "production"
  }'

# 获取执行结果
curl http://localhost:8011/api/v1/test-runs/{run_id}/results
```

#### LLM 使用情况 API

```bash
# 查询 Token 使用统计
curl http://localhost:8011/api/v1/llm-usage/summary

# 按天查询使用情况
curl http://localhost:8011/api/v1/llm-usage/by-day?days=30
```

### 📊 数据模型

核心数据表：

- `test_definitions`：测试用例定义
- `test_steps`：测试步骤详情
- `test_runs`：测试执行记录
- `test_cases`：单步测试结果
- `schedules`：调度配置
- `llm_usage`：LLM 调用记录

详见 [数据库文档](.claude/rules/database.md)

### 🔒 安全特性

- **JWT 身份认证**
- **RBAC 权限控制**
- **SQL 注入防护**（ORM 参数化查询）
- **XSS 防护**（前端输入转义）
- **速率限制**（Redis 滑动窗口）
- **审计日志**：90天安全事件记录

### 🌐 国际化

完整的多语言支持（i18n）：

- ✅ 英语（默认）
- 🔄 简体中文（开发中）

### 📦 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。

### 🤝 贡献指南

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 📚 文档索引

- [开发指南](.claude/rules/development.md)
- [数据库架构](.claude/rules/database.md)
- [前端开发](.claude/rules/frontend.md)
- [后端开发](.claude/rules/backend.md)
- [测试执行流程](.claude/rules/test-execution.md)
- [性能优化](.claude/rules/performance.md)
- [故障排查](.claude/rules/troubleshooting.md)
- [配置参考](.claude/rules/config.md)

### 💬 社区

- **问题反馈**: [GitHub Issues](https://github.com/your-org/deepagent-test-runner/issues)
- **功能讨论**: [GitHub Discussions](https://github.com/your-org/deepagent-test-runner/discussions)
- **文档**: [项目 Wiki](https://github.com/your-org/deepagent-test-runner/wiki)

### 🙏 致谢

感谢以下开源项目：

- [Playwright](https://playwright.dev/) - 现代浏览器自动化框架
- [Temporal](https://temporal.io/) - 持久化工作流引擎
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [LangChain](https://langchain.com/) - LLM 应用开发框架
- [DeepAgents](https://deepagents.ai/) - AI 代理框架
- [IBM Carbon Design System](https://carbondesignsystem.com/) - 企业级设计系统

---

## English Version

### 🎯 Overview

**DeepAgent Test Runner** is an AI-powered End-to-End (E2E) automated testing platform that revolutionizes how tests are written and executed. By leveraging natural language to drive tests, combined with advanced LLM technology and browser automation capabilities, test creation has never been easier.

### ✨ Key Features

#### 🤖 AI-Driven Test Authoring
- **Natural language test definitions**: Write tests in descriptive language without coding knowledge
- **Intelligent test generation**: GLM-4 Plus powered test planning and script generation
- **Adaptive element selection**: AI locates elements based on context, not fixed selectors
- **Visual validation**: UI state validation based on visual appearance

#### 🎭 DeepAgents Orchestration
- **DeepAgents framework integration**: Industry-leading orchestration for test execution
- **Sandboxed execution**: Secure Playwright script execution environment
- **Deterministic execution mode**: Support for pre-generated scripts
- **Real-time feedback**: Live progress updates during test execution

#### 📊 Complete Observability
- **Langfuse LLM monitoring**: Token usage, cost, and performance tracking
- **Test execution analytics**: Detailed step results, screenshots, and Playwright traces
- **Multi-dimensional dashboards**: Pass rates, execution time, cost trends
- **Historical comparison**: Time-series analysis and trend prediction

#### 🛠️ Enterprise Features
- **RBAC system**: Granular test suite and workspace permissions
- **Review workflow**: Built-in peer review mechanism
- **Version control**: Complete history of test cases and suites
- **Tag system**: Flexible test categorization
- **Workspace isolation**: Multi-tenant support with data separation

#### 🌐 Open Ecosystem
- **Test marketplace**: Share and discover test cases and suites
- **RESTful API**: Complete API interface for CI/CD integration
- **Cron scheduling**: Reliable Temporal-based scheduling
- **Webhook notifications**: Real-time test result push

### 🏗️ Architecture

```
Frontend (React/Vite :5173) → Nginx (:8080) → Unified Backend (FastAPI :8011)
                                                    ↓
                              PostgreSQL (:5433) ← Temporal Server
                                                    ↓
                              Playwright ← GLM LLM API ← DeepAgents
```

### 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/deepagent-test-runner.git
cd deepagent-test-runner

# Start development environment (with hot-reload)
./start-dev.sh

# Start production environment
./start-prod.sh
```

### 📖 Usage Guide

#### 1. Create Test Cases

Describe test steps in natural language within the test editor:

```
1. Open https://example.com
2. Click login button
3. Enter username and password
4. Submit form
5. Verify login success message
```

AI automatically generates executable Playwright scripts.

#### 2. Configure Scheduling

Set up Cron expressions for scheduled automated testing:

```yaml
cron: "0 2 * * *"  # Daily at 2 AM
environment: production
```

#### 3. View Analytics

Real-time test execution results, pass rate trends, and cost analysis.

### 🎨 Design System

Built with IBM Carbon Design System for enterprise UX:

- **Zero border-radius**: Professional, clean visual style
- **IBM Plex Sans** typography
- **8px grid system**: Precise layout standards
- **Single accent color**: IBM Blue 60 (#0f62fe)
- **Responsive design**: Full support from 320px to 1584px

See [DESIGN.md](DESIGN.md) for details.

### 📚 Documentation

- [Development Guide](.claude/rules/development.md)
- [Database Schema](.claude/rules/database.md)
- [Frontend Development](.claude/rules/frontend.md)
- [Backend Development](.claude/rules/backend.md)
- [Test Execution Flow](.claude/rules/test-execution.md)
- [Performance](.claude/rules/performance.md)
- [Troubleshooting](.claude/rules/troubleshooting.md)

### 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### 📦 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) - Modern browser automation
- [Temporal](https://temporal.io/) - Durable workflow engine
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- [LangChain](https://langchain.com/) - LLM application framework
- [DeepAgents](https://deepagents.ai/) - AI agent framework
- [IBM Carbon Design System](https://carbondesignsystem.com/) - Enterprise design system

---

<div align="center">
Made with ❤️ by the DeepAgent Team
</div>
