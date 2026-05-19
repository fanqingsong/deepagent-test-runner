# AI Test Runner - 架构详解

## 概述

AI Test Runner 是一个使用 AI SDK 和 MCP (Model Context Protocol) 服务器实现的端到端自动化测试框架。它通过自然语言描述测试步骤，利用 AI 的理解能力和决策能力来执行浏览器自动化测试。

## 核心架构

### 系统组件

```
┌─────────────────────────────────────────────────────────────────┐
│                      Test Runner CLI                            │
│                    (Bun + TypeScript)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 启动 MCP State Server (localhost:3001)                      │
│     - 管理测试用例状态                                            │
│     - 提供 get_test_plan 和 update_test_step 工具               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 遍历每个测试用例，调用 startTest(testCase)                  │
│     - 使用 @anthropic-ai/claude-code SDK                        │
│     - 配置两个 MCP 服务器：                                       │
│       a) Playwright MCP (浏览器自动化)                           │
│       b) Test State MCP (状态管理)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. AI 执行流程：                                       │
│     a) 接收系统提示词（system prompt）                           │
│     b) 调用 get_test_plan 获取测试步骤                           │
│     c) 使用 Playwright MCP 工具执行每个步骤                      │
│     d) 调用 update_test_step 更新步骤状态                        │
│     e) 重复直到所有步骤完成或达到 maxTurns                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 收集结果并生成报告                                           │
│     - CTRF 格式 JSON 报告                                        │
│     - Markdown 测试摘要                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 三大核心组件

#### 1. Test Runner CLI ([cli/src/index.ts](cli/src/index.ts))

**职责**: 测试编排和结果收集

**关键流程**:
```typescript
// 启动 MCP State Server
const server = new MCPStateServer(3001);
await server.start();

// 遍历每个测试用例
for (const testCase of inputs.testCases) {
    // 设置当前测试状态
    server.setTestState(testCase);
    
    // 启动 AI 执行测试
    for await (const message of startTest(testCase)) {
        logger.debug("Received AI message", {...});
    }
    
    // 收集结果
    const testState = server.getState();
    reporter.addTestResult(testState, startTime, endTime);
}

// 生成报告
reporter.saveResults(inputs.resultsPath);
```

**关键点**:
- 在 [index.ts:22-27](cli/src/index.ts#L22-L27) 使用异步生成器接收 AI 的消息流
- 在 [index.ts:29](cli/src/index.ts#L29) 通过 `server.getState()` 获取最终测试状态
- 使用 TestReporter 生成 CTRF 和 Markdown 报告

#### 2. MCP State Server ([cli/src/mcp/test-state/server.ts](cli/src/mcp/test-state/server.ts))

**职责**: 维护测试执行状态，提供 Test Runner 和 AI 之间的双向通信

**技术实现**:
- 使用 Express 创建 HTTP 服务器（端口 3001）
- 使用 MCP SDK 的 `StreamableHTTPServerTransport` 处理 MCP 协议
- 在内存中存储当前测试用例的状态

**提供的 MCP 工具**:

1. **get_test_plan**: 获取当前测试计划和所有步骤状态
```typescript
case "get_test_plan":
    return {
        content: [{
            type: "text",
            text: JSON.stringify(this.testState, null, 2),
        }],
    };
```

2. **update_test_step**: 更新特定步骤的状态
```typescript
case "update_test_step": {
    const { stepId, status, error } = updateTestPlanToolInput.parse(args);
    const step = this.testState?.steps.find((s) => s.id === stepId);
    
    if (!step) {
        throw new Error(`Step ${stepId} not found`);
    }
    
    step.status = status;  // "passed" | "failed"
    if (error) {
        step.error = error;
    }
    
    return {...};
}
```

**为什么需要 MCP State Server**:
- **状态同步**: AI 是无状态的，需要外部存储测试进度
- **双向通信**: Test Runner 需要实时获取测试结果
- **工具隔离**: 通过 MCP 协议隔离状态管理逻辑

### MCP State Server 深度解析

#### 核心问题：为什么需要专门的状态服务器？

**问题背景**：
AI 的设计理念是作为**无状态**的 AI 助手，它：
- 不维护内部状态
- 每次调用都是独立的
- 不能保证在同一会话中记住之前的信息

**在测试场景中的挑战**：
```
无状态的问题：

Test Runner:  "执行步骤1：导航到首页"
     │
     ▼
AI:  [执行导航] "完成"
     │
     ▼
Test Runner:  "执行步骤2：点击登录按钮"
     │
     ▼
AI:  "等等，我要执行什么步骤？当前在哪？"
              (因为它是无状态的，不记得之前的上下文)
```

**MCP State Server 的解决方案**：
```
有状态的解决方案：

Test Runner:  "执行步骤1：导航到首页"
     │
     ├─────────────────────────────>│
     │                              │
     │                              │
     ▼                              │
AI:  [调用 get_test_plan]  │
     │<─────────────────────────────┤
     │  返回: {                     │
     │    steps: [                  │
     │      {id: 1, desc: "导航..."},│
     │      {id: 2, desc: "点击..."} │
     │    ]                         │
     │  }                           │
     │                              │
     │  [执行导航]                   │
     │  [调用 update_test_step(1, "passed")]
     │─────────────────────────────>│
     │                              │ 更新状态
     │                              │
     ▼                              │
Test Runner:  "继续执行步骤2"        │
     │                              │
     ▼                              │
AI:  [调用 get_test_plan]  │
     │<─────────────────────────────┤
     │  返回: {                     │
     │    steps: [                  │
     │      {id: 1, status: "passed"}, ✅
     │      {id: 2, status: "pending"} ⏳
     │    ]                         │
     │  }                           │
     │  "好的，步骤1已完成，现在执行步骤2"
```

#### 设计原理

**1. 单一数据源 (Single Source of Truth)**
```typescript
// 在 server.ts 中
private testState: TestCase | null = null;

public setTestState(testState: TestCase) {
    this.testState = testState;  // 唯一的状态存储
}

public getState(): TestCase | null {
    return this.testState;  // 所有的状态读取都通过这里
}
```

**为什么重要**：
- 避免状态不一致（Test Runner 和 AI 看到不同的状态）
- 简化状态管理（只有一个地方存储状态）
- 易于调试和监控

**2. 双向通信机制**

**Test Runner → State Server**：
```typescript
// 在 index.ts:20
server.setTestState(testCase);  // 设置初始状态

// 在 index.ts:29
const testState = server.getState();  // 获取最终状态
```

**AI → State Server**：
```typescript
// 通过 MCP 工具调用
// AI 调用 get_test_plan
case "get_test_plan":
    return {
        content: [{
            type: "text",
            text: JSON.stringify(this.testState, null, 2),
        }],
    };

// AI 调用 update_test_step
case "update_test_step": {
    const { stepId, status, error } = updateTestPlanToolInput.parse(args);
    const step = this.testState?.steps.find((s) => s.id === stepId);
    step.status = status;  // 直接修改内存中的状态
    if (error) step.error = error;
    return {...};
}
```

**3. MCP 协议的标准化接口**

**工具定义**：
```typescript
// 在 server.ts:45-63
this.mcpServer.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "get_test_plan",
                description: "Get the entire test plan with current state",
                inputSchema: {
                    type: "object",
                    properties: {},
                    additionalProperties: false,
                },
            },
            {
                name: "update_test_step",
                description: "Update a test step with passed/failed status",
                inputSchema: z.toJSONSchema(updateTestPlanToolInput),
            },
        ],
    };
});
```

**输入验证**：
```typescript
// 在 update-test-plan-tool-input.ts
export const updateTestPlanToolInput = z.object({
    stepId: z.number().describe("The ID of the step to update"),
    status: z.enum(["passed", "failed"]).describe("The status of the step"),
    error: z.string().optional().describe("The error message if the step failed"),
});
```

**为什么使用 Zod**：
- 自动类型推导
- 运行时验证
- 清晰的 API 文档
- 防止无效输入

#### 技术实现细节

**1. HTTP + MCP 传输层**

```typescript
// Express 路由处理
this.app.post("/", async (req: Request, res: Response) => {
    this.transport.handleRequest(req, res, req.body);
});

// MCP 服务器连接
this.mcpServer.connect(this.transport);
```

**请求流程**：
```
AI                MCP State Server              Express
     │                            │                          │
     │ 1. HTTP POST               │                          │
     ├───────────────────────────>│                          │
     │    {                       │                          │
     │      "method": "tools/call",│                       │
     │      "params": {           │                          │
     │        "name": "get_test_plan",                     │
     │        "arguments": {}     │                          │
     │      }                     │                          │
     │    }                       │                          │
     │                            │  2. 转发到 MCP Server    │
     │                            ├──────────────────────────>│
     │                            │  3. 处理请求              │
     │                            │<──────────────────────────┤
     │                            │  4. 返回结果              │
     │  5. HTTP Response          │                          │
     │<───────────────────────────┤                          │
     │    {                       │                          │
     │      "content": [{         │                          │
     │        "type": "text",     │                          │
     │        "text": "{...}"     │                          │
     │      }]                    │                          │
     │    }                       │                          │
```

**2. StreamableHTTPServerTransport 的作用**

```typescript
private transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
});
```

**功能**：
- 实现 MCP 协议的 HTTP 传输层
- 处理请求/响应的序列化和反序列化
- 管理会话状态（可选）
- 支持 SSE（Server-Sent Events）流式响应

**3. 内存存储 vs 持久化存储**

**当前实现**（内存存储）：
```typescript
private testState: TestCase | null = null;
```

**优势**：
- 快速访问（无 I/O 开销）
- 简单实现
- 适合短生命周期的测试

**限制**：
- 服务器重启后状态丢失
- 只支持单测试用例
- 无法跨会话共享状态

**如果需要持久化**：
```typescript
// 可能的改进
class MCPStateServer {
    private stateDB: Map<string, TestCase> = new Map();

    setTestState(testId: string, testCase: TestCase) {
        this.stateDB.set(testId, testCase);
        // 可选：写入文件或数据库
    }

    getTestState(testId: string): TestCase | undefined {
        return this.stateDB.get(testId);
    }
}
```

#### 在测试执行流程中的关键作用

**完整的测试生命周期**：

```typescript
// 1. 初始化阶段 ([index.ts:9-10](cli/src/index.ts#L9-L10))
const server = new MCPStateServer(3001);
await server.start();
// → HTTP 服务器启动在 localhost:3001

// 2. 测试开始前 ([index.ts:20](cli/src/index.ts#L20))
server.setTestState(testCase);
// → 测试用例加载到内存

// 3. 测试执行中 (AI 通过 MCP 工具)
// → AI 调用 get_test_plan 获取步骤
// → AI 调用 update_test_step 更新状态
// → 实时同步测试进度

// 4. 测试结束后 ([index.ts:29](cli/src/index.ts#L29))
const testState = server.getState();
// → 获取最终状态用于报告生成

// 5. 所有测试完成后 ([index.ts:49](cli/src/index.ts#L49))
server.stop();
// → 关闭 HTTP 服务器
```

#### 如果没有 MCP State Server 会怎样？

**方案 A：AI 内部维护状态**
```typescript
// ❌ 不可行的方案
const systemPrompt = `
You will maintain your own list of test steps.
Mark each step as passed/failed as you complete them.
`;

// 问题：
// 1. AI 可能忘记状态
// 2. Test Runner 无法知道实时进度
// 3. 无法生成准确的测试报告
// 4. 调试困难（无法查看内部状态）
```

**方案 B：通过文件系统共享状态**
```typescript
// ⚠️ 可行但不优雅
fs.writeFileSync('test-state.json', JSON.stringify(testCase));

// AI 读取文件
const testState = JSON.parse(fs.readFileSync('test-state.json'));

// 问题：
// 1. 文件 I/O 性能问题
// 2. 并发访问冲突
// 3. 状态同步延迟
// 4. 跨平台兼容性问题
```

**方案 C：通过 HTTP API 共享状态**
```typescript
// ✅ MCP State Server 的方案
app.get('/api/test-state', (req, res) => {
    res.json(testState);
});

app.post('/api/test-state/:stepId', (req, res) => {
    updateStep(req.params.stepId, req.body);
    res.json({success: true});
});

// 优势：
// 1. 标准化接口
// 2. 实时同步
// 3. 易于监控和调试
// 4. 符合 MCP 协议规范
```

#### 关键设计决策

**1. 为什么使用 HTTP 而不是 stdin/stdout？**
- **独立性**：可以作为独立服务运行
- **调试性**：可以用 curl 或 Postman 测试
- **扩展性**：支持远程访问（如果需要）
- **标准化**：MCP 协议官方推荐的传输方式

**2. 为什么使用 MCP 而不是 REST API？**
- **工具发现**：MCP 支持自动工具发现和文档生成
- **类型安全**：强类型输入验证
- **标准化**：符合 MCP 生态系统
- **集成性**：与 AI 无缝集成

**3. 为什么存储在内存而不是数据库？**
- **简单性**：当前用例不需要持久化
- **性能**：内存访问速度快
- **隔离性**：每个测试用例独立执行
- **可扩展**：需要时可以轻松升级到数据库

#### 扩展性和未来改进

**可能的改进方向**：

1. **持久化支持**
```typescript
interface StateStorage {
    get(testId: string): Promise<TestCase>;
    set(testId: string, state: TestCase): Promise<void>;
    delete(testId: string): Promise<void>;
}

class FileStorage implements StateStorage { ... }
class RedisStorage implements StateStorage { ... }
class DatabaseStorage implements StateStorage { ... }
```

2. **并发测试支持**
```typescript
class MCPStateServer {
    private states: Map<string, TestCase> = new Map();

    setTestState(testId: string, testCase: TestCase) {
        this.states.set(testId, testCase);
    }

    getTestState(testId: string): TestCase | undefined {
        return this.states.get(testId);
    }
}
```

3. **状态变更事件**
```typescript
class MCPStateServer {
    private events: EventEmitter = new EventEmitter();

    updateTestStep(stepId: number, status: string) {
        // ... 更新状态
        this.events.emit('step-updated', { stepId, status });
    }
}
```

4. **状态快照和回滚**
```typescript
class MCPStateServer {
    private snapshots: Map<string, TestCase[]> = new Map();

    createSnapshot(testId: string) {
        const state = this.states.get(testId);
        this.snapshots.set(testId, [...(this.snapshots.get(testId) || []), state]);
    }

    rollback(testId: string, version: number) {
        const snapshots = this.snapshots.get(testId);
        this.states.set(testId, snapshots[version]);
    }
}
```

#### 总结

MCP State Server 是整个测试框架的**状态管理中心**，它：

1. **解决核心问题**：为无状态的 AI 提供状态存储
2. **标准化接口**：通过 MCP 协议提供统一的工具接口
3. **双向通信**：支持 Test Runner 和 AI 之间的状态同步
4. **简单高效**：内存存储提供快速访问
5. **易于扩展**：可以升级到持久化存储或支持并发

没有 MCP State Server，测试框架将无法：
- 追踪测试进度
- 生成准确的测试报告
- 实时监控测试状态
- 在 AI 无状态的情况下维护测试上下文

它是连接 Test Runner 和 AI 的**关键桥梁**，使整个测试架构成为可能。

#### 3. AI 集成 ([cli/src/prompts/start-test.ts](cli/src/prompts/start-test.ts))

**职责**: 启动和管理 AI 进程，配置 MCP 服务器

#### AI SDK 工作原理

**架构层次**：
```
┌─────────────────────────────────────────────────────────────┐
│         你的代码 (Test Runner)                               │
│         startTest(testCase)                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│         @anthropic-ai/claude-code SDK                        │
│         query() 函数                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│         AI CLI (/home/fqs/.nvm/.../bin/claude)     │
│         独立的进程，处理 MCP 服务器、工具调用等                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│         Anthropic API                                        │
│         GPT-4/Claude 模型调用                                 │
└─────────────────────────────────────────────────────────────┘
```

**核心概念**：
- **SDK 是对 AI CLI 的程序化封装**
- `query()` 函数启动独立的 AI 进程
- 通过进程间通信 (IPC) 与 AI 交互
- 返回异步生成器，流式返回消息

**消息流**：
```
AI 进程                    SDK (异步生成器)              你的代码
     │                                  │                          │
     │ 1. 启动进程                       │                          │
     ├─────────────────────────────────>│                          │
     │                                  │                          │
     │ 2. 读取系统提示词                 │                          │
     │<─────────────────────────────────┤                          │
     │                                  │                          │
     │ 3. 调用 get_test_plan             │                          │
     │ 4. 返回测试计划                   │                          │
     ├─────────────────────────────────>│  yield message            │
     │                                  ├─────────────────────────>│
     │                                  │                          │
     │ 5. 执行浏览器操作                 │                          │
     │ 6. 更新步骤状态                   │                          │
     ├─────────────────────────────────>│  yield message            │
     │                                  ├─────────────────────────>│
     │                                  │                          │
     │ ... (重复) ...                   │                          │
     │                                  │                          │
     │ 7. 完成测试                       │                          │
     ├─────────────────────────────────>│  yield message            │
     │                                  ├─────────────────────────>│
     │                                  │  (循环结束)               │
```

**SDK vs CLI 职责分工**：

| 层级 | 组件 | 职责 |
|------|------|------|
| **你的代码** | Test Runner | 业务逻辑、测试编排 |
| **SDK** | `query()` 函数 | 进程管理、消息流封装、配置传递 |
| **CLI** | AI | MCP 服务器管理、工具调用、API 通信 |
| **API** | Anthropic API | 模型推理、响应生成 |

**为什么需要这种架构？**

1. **进程隔离**：AI 运行在独立进程，崩溃不影响主程序
2. **资源复用**：多个 `query()` 调用可以共享同一个 AI 进程
3. **简化集成**：开发者不需要直接处理 MCP 协议、进程通信等细节
4. **流式响应**：异步生成器提供实时的消息流

**启动流程**:

1. **查找 AI 可执行文件** ([start-test.ts:14](cli/src/prompts/start-test.ts#L14)):
```typescript
const claudePath = which("claude");
if (!claudePath) {
    throw new Error("Claude not found on PATH. Did you run `bun install`?");
}
```

2. **配置 AI SDK** ([start-test.ts:18-44](cli/src/prompts/start-test.ts#L18-L44)):
```typescript
return query({
    prompt: "Query the test plan from mcp__testState__get_test_plan MCP tool to get started.",
    options: {
        customSystemPrompt: systemPrompt(),
        maxTurns: inputs.maxTurns,
        pathToClaudeCodeExecutable: claudePath,
        model: inputs.model,
        mcpServers: {
            // Playwright MCP - 浏览器自动化
            "cctr-playwright": {
                command: "bunx",
                args: [
                    "@playwright/mcp@v0.0.31",
                    "--output-dir", `${inputs.resultsPath}/${testCase.id}/playwright`,
                    "--save-trace",
                    "--image-responses", "omit",
                ],
            },
            // Test State MCP - 状态管理
            "cctr-state": {
                type: "http",
                url: "http://localhost:3001/",
                headers: {"Content-Type": "application/json"},
            },
        },
        allowedTools: [
            // Playwright MCP 工具（浏览器操作）
            "mcp__cctr-playwright__browser_navigate",
            "mcp__cctr-playwright__browser_click",
            "mcp__cctr-playwright__browser_type",
            "mcp__cctr-playwright__browser_snapshot",
            // ... 更多工具
            
            // 自定义状态管理工具
            "mcp__cctr-state__get_test_plan",
            "mcp__cctr-state__update_test_step",
        ],
    },
});
```

**关键配置说明**:
- **customSystemPrompt**: 定义 AI 的角色和行为规则
- **maxTurns**: 限制每轮测试的最大交互次数，防止无限循环
- **pathToClaudeCodeExecutable**: 指向 AI CLI 的路径
- **model**: 可选，覆盖默认模型（如使用 Haiku 加快速度）
- **mcpServers**: 配置两个 MCP 服务器的连接参数
- **allowedTools**: 白名单机制，只允许使用必要的工具

## 系统提示词 (System Prompt)

[cli/src/prompts/system.ts](cli/src/prompts/system.ts) 定义的系统提示词是整个系统的核心：

```typescript
export const systemPrompt = () => `
You are a software tester that can use the Playwright MCP to interact with a web app.

You will be executing a test plan made available via the mcp__cctr-state__get_test_plan tool.
Always ask for the test plan before executing any steps.
Do not deviate from the test plan. Do not ask any follow up questions.

## Browser Actions
- Use the mcp__cctr-playwright__* tools to interact with the browser to perform test steps.
  DO NOT USE ANY OTHER MCP TOOLS TO INTERACT WITH THE BROWSER.

## Test Execution State
- Use the mcp__cctr-state__get_test_plan tool from the testState MCP server to get the current test plan.
- Use the mcp__cctr-state__update_test_step tool from the testState MCP server to update the current test step with a passed or failed status.
- DO NOT MAINTAIN YOUR OWN LIST OF STEPS. USE THE MCP TOOLS TO MANAGE THE TEST PLAN.
  IF ANY STEPS ARE NOT UPDATED, WE WILL CONSIDER THE TEST FAILED.

## Security and privacy
- Do not share any sensitive information (e.g. passwords, API keys, PII, etc.) in chat.
`;
```

**提示词设计原则**:
1. **明确角色**: "software tester that can use the Playwright MCP"
2. **强制流程**: "Always ask for the test plan before executing any steps"
3. **工具约束**: 明确指定使用哪些 MCP 工具
4. **状态管理**: 强制使用 MCP 工具管理步骤状态
5. **安全提醒**: 防止泄露敏感信息

## AI SDK 深度解析

### SDK 的本质

**@anthropic-ai/claude-code SDK** 是对 AI CLI 的程序化封装，它：
- 不是直接调用 Anthropic API
- 而是启动和管理 AI CLI 进程
- 通过进程间通信 (IPC) 与 AI 交互
- 提供异步生成器接口，流式返回消息

### 与直接使用 CLI 的区别

**直接使用 CLI**：
```bash
claude --prompt "执行测试" \
  --mcp-server playwright=bunx@playwright/mcp \
  --allowed-tools mcp__playwright__browser_navigate
```

**使用 SDK**：
```typescript
const messages = query({
  prompt: "执行测试",
  mcpServers: { playwright: {...} },
  allowedTools: ["mcp__playwright__browser_navigate"],
});

for await (const message of messages) {
  // 程序化处理每个消息
}
```

### SDK 提供的核心价值

1. **类型安全**：完整的 TypeScript 类型定义
2. **错误处理**：统一的错误处理机制
3. **消息解析**：自动解析 AI 的输出格式
4. **配置管理**：结构化的配置选项
5. **集成便利**：轻松嵌入到现有应用中
6. **流式响应**：异步生成器提供实时消息流

### query() 函数的工作机制

#### 函数签名（简化）
```typescript
function query(options: {
  prompt: string;
  options: {
    customSystemPrompt?: string;
    maxTurns?: number;
    pathToClaudeCodeExecutable: string;
    model?: string;
    mcpServers: Record<string, MCPServerConfig>;
    allowedTools: string[];
  };
}): AsyncGenerator<Message, void, unknown>;
```

#### 内部实现原理（简化版）
```typescript
class ClaudeCodeSDK {
  async *query(options: QueryOptions): AsyncGenerator<Message> {
    // 1. 启动 AI 进程
    const process = spawn(options.pathToClaudeCodeExecutable, [
      '--mcp-servers', JSON.stringify(options.mcpServers),
      '--allowed-tools', JSON.stringify(options.allowedTools),
      '--model', options.model || 'default',
      '--max-turns', String(options.maxTurns || 30),
    ]);

    // 2. 发送初始请求
    process.stdin.write(JSON.stringify({
      prompt: options.prompt,
      systemPrompt: options.customSystemPrompt,
    }));

    // 3. 从 stdout 读取消息流
    const readline = createInterface(process.stdout);
    for await (const line of readline) {
      if (line.trim()) {
        const message = JSON.parse(line);
        yield message;  // 产生消息到调用者
      }
    }

    // 4. 等待进程结束
    await process.waitForExit();
  }
}
```

### MCP 服务器配置详解

在 [start-test.ts:25-44](cli/src/prompts/start-test.ts#L25-L44) 中的 `mcpServers` 配置：

```typescript
mcpServers: {
    "cctr-playwright": {
        command: "bunx",
        args: [
            "@playwright/mcp@v0.0.31",
            "--output-dir", `${inputs.resultsPath}/${testCase.id}/playwright`,
            "--save-trace",
            "--image-responses", "omit",
        ],
    },
    "cctr-state": {
        type: "http",
        url: "http://localhost:3001/",
        headers: {"Content-Type": "application/json"},
    },
}
```

#### 配置类型

**Command 类型**（Playwright MCP）：
```typescript
{
  command: string;      // 执行的命令（如 "bunx"）
  args: string[];       // 命令参数
}
```
- SDK 会启动这个命令作为子进程
- 通过 stdio 与 MCP 服务器通信
- 适合需要独立进程的 MCP 服务器

**HTTP 类型**（Test State MCP）：
```typescript
{
  type: "http";
  url: string;          // MCP 服务器 URL
  headers?: Record<string, string>;
}
```
- SDK 通过 HTTP 请求连接到 MCP 服务器
- 适合已经运行的 HTTP 服务器
- 我们的 Test State Server 就是这种类型

#### MCP 通信流程

```
Test Runner                    AI CLI                MCP Server
     │                              │                            │
     │ 1. 启动时配置 mcpServers     │                            │
     ├────────────────────────────>│                            │
     │                              │                            │
     │                              │ 2. 连接到 cctr-state        │
     │                              ├───────────────────────────>│
     │                              │                            │
     │                              │ 3. 启动 cctr-playwright     │
     │                              ├───────────────────────────>│
     │                              │                            │
     │                              │ 4. 列出可用工具             │
     │                              │<───────────────────────────┤
     │                              │                            │
     │ 5. 执行测试                   │                            │
     │                              │                            │
     │                              │ 6. 调用 get_test_plan       │
     │                              ├───────────────────────────>│
     │                              │ 7. 返回测试计划             │
     │                              │<───────────────────────────┤
     │                              │                            │
     │                              │ 8. 调用 browser_navigate    │
     │                              ├───────────────────────────>│
     │                              │ 9. 执行浏览器操作           │
     │                              │<───────────────────────────┤
     │                              │                            │
     │                              │ 10. 调用 update_test_step   │
     │                              ├───────────────────────────>│
     │                              │ 11. 更新步骤状态            │
     │                              │<───────────────────────────┤
```

### allowedTools 配置的作用

```typescript
allowedTools: [
    // Playwright MCP 工具
    "mcp__cctr-playwright__browser_navigate",
    "mcp__cctr-playwright__browser_click",
    // ... 更多工具
    
    // 自定义状态管理工具
    "mcp__cctr-state__get_test_plan",
    "mcp__cctr-state__update_test_step",
]
```

**白名单机制**：
1. SDK 将白名单传递给 AI CLI
2. AI 只能使用列出的工具
3. 任何未列出的工具调用都会被拒绝
4. 提高了测试的可预测性和安全性

**工具命名规范**：
- 格式：`mcp__{server-name}__{tool-name}`
- `server-name`: MCP 服务器的配置键名（如 `cctr-playwright`）
- `tool-name`: MCP 服务器提供的工具名称（如 `browser_navigate`）

### 异步生成器的使用

在 [index.ts:22-27](cli/src/index.ts#L22-L27) 中的使用：

```typescript
for await (const message of startTest(testCase)) {
    logger.debug("Received AI message", {
        test_id: testCase.id,
        message: JSON.stringify(message),
    });
}
```

**消息类型**：
```typescript
type Message =
  | { type: "user"; content: string }
  | { type: "assistant"; content: string }
  | { type: "tool_use"; name: string; input: any }
  | { type: "tool_result"; content: string }
  | { type: "error"; error: string }
  | { type: "status"; status: string };
```

**实时监控**：
- 每个消息都会立即被处理
- 可以实时记录日志
- 可以实现进度条
- 可以检测错误并及时中断

### maxTurns 参数的作用

```typescript
maxTurns: inputs.maxTurns,  // 默认 30
```

**作用**：
- 限制 AI 的最大交互次数
- 防止无限循环
- 控制成本（API 调用次数）
- 超过后会自动终止测试

**什么是 "Turn"**：
- 一次 Turn = 一次工具调用 + 一次响应
- 例如：调用 `browser_navigate` + 返回导航结果 = 1 Turn
- 复杂的测试可能需要更多的 Turn

## 完整执行流程示例

以 [samples/pdca-e2e-tests.json](samples/pdca-e2e-tests.json) 中的登录测试为例：

### 测试定义
```json
{
  "id": "login-test-case",
  "description": "Test logging into localhost:5173",
  "steps": [
    {"id": 1, "description": "Navigate to localhost:5173"},
    {"id": 2, "description": "Enter email address: admin@example.com"},
    {"id": 3, "description": "Enter password: changethis"},
    {"id": 4, "description": "Click login button"},
    {"id": 5, "description": "Verify successful login"}
  ]
}
```

### 执行时序

```
Test Runner                    MCP State Server              AI                    Playwright MCP
     │                                │                              │                               │
     │ 1. setTestState(testCase)      │                              │                               │
     ├──────────────────────────────>│                              │                               │
     │                                │ 存储测试到内存                │                               │
     │                                │                              │                               │
     │ 2. startTest(testCase)         │                              │                               │
     │                                │                              │                               │
     │                                │                              │ 3. 接收系统提示               │
     │                                │                              │<─────────────────────────────┤
     │                                │                              │                               │
     │                                │                              │ 4. 调用 get_test_plan         │
     │                                │<─────────────────────────────┤                               │
     │                                │ 5. 返回测试计划               │                               │
     │                                │─────────────────────────────>│                               │
     │                                │                              │                               │
     │                                │                              │ 6. 调用 browser_navigate     │
     │                                │                              │──────────────────────────────>│
     │                                │                              │ 7. 导航到 localhost:5173      │
     │                                │                              │<──────────────────────────────┤
     │                                │                              │                               │
     │                                │                              │ 8. 调用 update_test_step(1, "passed") │
     │                                │<─────────────────────────────┤                               │
     │                                │ 9. 更新步骤1状态              │                               │
     │                                │─────────────────────────────>│                               │
     │                                │                              │                               │
     │                                │                              │ 10. 调用 browser_type (email) │
     │                                │                              │──────────────────────────────>│
     │                                │                              │ 11. 输入邮箱地址              │
     │                                │                              │<──────────────────────────────┤
     │                                │                              │                               │
     │                                │                              │ 12. 调用 update_test_step(2, "passed") │
     │                                │<─────────────────────────────┤                               │
     │                                │ 13. 更新步骤2状态             │                               │
     │                                │─────────────────────────────>│                               │
     │                                │                              │                               │
     │                                │                              │ ... 重复步骤3-5 ...            │
     │                                │                              │                               │
     │ 14. getState()                 │                              │                               │
     │<───────────────────────────────┤                              │                               │
     │ 15. 返回最终状态                │                              │                               │
     │───────────────────────────────>│                              │                               │
     │                                │                              │                               │
     │ 16. 生成报告                    │                              │                               │
     │                                │                              │                               │
```

### 关键创新点

#### 1. **状态同步机制**
- 通过 MCP State Server 实现 Test Runner 和 AI 之间的双向通信
- AI 无需维护内部状态，所有状态通过 MCP 工具管理
- Test Runner 可以随时获取测试进度

#### 2. **工具白名单机制**
- `allowedTools` 配置限制 AI 只能使用必要的工具
- 防止 AI 使用其他可能干扰测试的工具
- 提高测试的可预测性和稳定性

#### 3. **异步生成器模式**
- `startTest()` 返回异步生成器，产生 AI 的消息流
- Test Runner 可以实时监控执行过程
- 支持日志记录和调试

#### 4. **自适应测试执行**
- AI 根据实际情况调整操作，而不是硬编码选择器
- 可以处理网络延迟、动态内容等变化
- 利用 AI 的理解能力进行智能验证

#### 5. **模块化架构**
- MCP 服务器独立运行，可以单独测试
- Playwright MCP 和 Test State MCP 职责分离
- 易于扩展新的 MCP 工具

## 数据流

### 输入数据
```
JSON 测试文件 (TestCase[])
  ↓
Test Runner (index.ts)
  ↓
MCP State Server (内存)
  ↓
AI (通过 get_test_plan)
```

### 输出数据
```
AI 执行步骤
  ↓
调用 update_test_step (更新状态)
  ↓
MCP State Server (内存状态更新)
  ↓
Test Runner (通过 getState 获取)
  ↓
TestReporter (生成报告)
  ↓
CTRF JSON + Markdown
```

## 扩展性考虑

### 添加新的 MCP 工具
1. 在 [server.ts](cli/src/mcp/test-state/server.ts) 的 `setupMCPHandlers` 中添加新工具
2. 在 [start-test.ts](cli/src/prompts/start-test.ts) 的 `allowedTools` 中添加工具名称
3. 更新 [system.ts](cli/src/prompts/system.ts) 的提示词

### 支持新的浏览器操作
1. 确保 Playwright MCP 提供相应的工具
2. 在 `allowedTools` 中添加工具名称
3. 在系统提示词中说明如何使用

### 集成其他 MCP 服务器
1. 在 `mcpServers` 配置中添加新服务器
2. 配置连接参数（command、args 或 url、headers）
3. 在 `allowedTools` 中添加允许的工具名称

## 性能优化

1. **模型选择**: 使用 `--model` 参数选择更快的模型（如 Haiku）
2. **maxTurns 限制**: 防止无限循环，控制成本
3. **工具白名单**: 减少不必要的工具调用
4. **异步执行**: 支持并行执行多个测试用例（需修改代码）

## 调试技巧

1. **启用 verbose 模式**: `--verbose` 查看所有 AI 消息
2. **检查 Playwright traces**: 在 `{resultsPath}/{testId}/playwright` 目录
3. **查看截图**: 启用 `--screenshots` 保存关键步骤截图
4. **查看 MCP 通信**: 在代码中添加更多日志记录

## 安全考虑

1. **敏感信息**: 系统提示词提醒不要分享密码、API 密钥等
2. **工具限制**: `allowedTools` 白名单防止意外操作
3. **本地执行**: MCP State Server 只在本地运行
4. **网络隔离**: 浏览器在沙盒环境中运行

## 总结

AI Test Runner 通过巧妙的架构设计，将 AI 的理解能力与传统浏览器自动化结合：

- **MCP 协议**: 实现了组件间的松耦合通信
- **状态管理**: 通过独立的 MCP Server 解决了状态同步问题
- **工具约束**: 白名单机制确保测试的可控性
- **异步流式**: 生成器模式实现了实时监控
- **AI 决策**: AI 自适应执行，提高测试鲁棒性

### AI SDK 的关键作用

在整个架构中，**AI SDK 扮演了桥梁的角色**：

1. **程序化接口**: 将命令行工具转换为可编程的 SDK
2. **进程管理**: 优雅地启动和管理 AI 进程
3. **通信封装**: 隐藏了进程间通信的复杂性
4. **流式响应**: 通过异步生成器提供实时的消息流
5. **配置管理**: 结构化的配置选项，易于使用和维护

**没有 SDK 的情况下**，我们需要：
- 手动启动 AI 进程
- 处理进程间的 stdin/stdout 通信
- 解析 AI 的输出格式
- 管理进程生命周期
- 处理错误和异常情况

**有了 SDK**，这些复杂性都被封装起来，我们只需要：
```typescript
for await (const message of query({ prompt, options })) {
  // 处理消息
}
```

这个架构为 E2E 测试提供了一个全新的范式，利用 AI 的智能决策能力，使测试更加灵活和可靠。

## 参考资料

- [@anthropic-ai/claude-code - npm](https://www.npmjs.com/package/@anthropic-ai/claude-code)
- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)
- [AI Documentation](https://code.claude.com/docs)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/)
- [Playwright MCP Documentation](https://github.com/microsoft/playwright-mcp)

