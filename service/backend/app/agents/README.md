# Supervisor Pipeline Graph

LangGraph StateGraph 编排测试子智能体（planner → executor → reviewer），通过条件路由实现重试和错误恢复。

## 拓扑图

```
                         ┌──────────┐
                         │  START   │
                         └────┬─────┘
                              │
                   ┌──────────┴──────────┐
                   │  route_from_start   │
                   └──┬──────────────┬───┘
            mode=       │              │    mode=
        full_pipeline   │              │    execute_only
        + goal exists   │              │
                      ┌─▼──────────┐   │
                      │   planner   │   │
                      │    node     │   │
                      └─┬───────┬───┘   │
               success  │       │error  │
                        │       │       │
                        │  ┌────▼─────┐ │
                        │  │  error   │ │
                        │  │ handler  │◄┤◄──────────────┐
                        │  └──┬───┬───┘ │               │
                        │     │   │     │               │
                        │     │   └─────┼──retry────────┤
                        │     │         │               │
                        │  give up      │               │
                        │     │         │               │
           ┌────────────▼─────▼─────┐   │               │
           │       executor         │◄──┘               │
           │         node           │◄──────retry───────┘
           └──┬─────────┬──────┬───┘
      success  │         │error │ mode=
               │         │      │ plan_and_execute
               │    ┌────▼───┐  │
               │    │  error │──┘
               │    │ handler│──retry──► executor_node
               │    └──┬─────┘
               │       │ give up
               │       │
          ┌────▼───────▼──────────┐
          │      reviewer         │
          │        node           │
          └────────┬──────────────┘
                   │ always (non-fatal)
                   │
          ┌────────▼──────────┐
          │   result_builder  │
          │       node        │
          └────────┬──────────┘
                   │
              ┌────▼─────┐
              │   END    │
              └──────────┘
```

## 路由规则

| 边 | 条件 |
|---|---|
| START → planner_node | `mode == "full_pipeline" and goal exists` |
| START → executor_node | `mode == "execute_only"` or `"plan_and_execute"` |
| planner_node → executor_node | `plan_error is None` (成功) |
| planner_node → error_handler | `plan_error is not None` |
| executor_node → reviewer_node | `execution_error is None` 且 `mode != "plan_and_execute"` |
| executor_node → result_builder | `mode == "plan_and_execute"` 且成功 |
| executor_node → error_handler | `execution_error is not None` |
| reviewer_node → result_builder | 始终 (reviewer 失败不阻塞流水线) |
| error_handler → failed_phase | `retry_count <= max_retries` (重试) |
| error_handler → result_builder | `retry_count > max_retries` (放弃) |
| result_builder → END | 始终 |

## 执行模式

| mode | 流经节点 | 说明 |
|------|---------|------|
| `execute_only` | executor → reviewer → result_builder | 默认模式，执行已有测试步骤 |
| `full_pipeline` | planner → executor → reviewer → result_builder | 完整流程，先规划再执行 |
| `plan_and_execute` | planner → executor → result_builder | 跳过 reviewer |

## 文件结构

```
app/agents/
├── supervisor_state.py    # SupervisorState TypedDict — 图状态定义
├── supervisor_graph.py    # build_pipeline_graph() — 图构建器和路由函数
├── nodes.py               # 5 个节点函数 (planner/executor/reviewer/error_handler/result_builder)
├── planner_agent.py       # Planner 子智能体 — 生成测试计划
├── executor_agent.py      # Executor 子智能体 — 执行测试步骤
└── reviewer_agent.py      # Reviewer 子智能体 — 生成审查报告
```

## 状态字段 (SupervisorState)

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | str | 执行模式: execute_only / full_pipeline / plan_and_execute |
| `goal` | Optional[str] | 自然语言测试目标 (planner 使用) |
| `target_url` | Optional[str] | 目标 URL (planner 使用) |
| `test_steps` | Optional[List[Dict]] | 待执行的测试步骤 |
| `step_results` | Optional[List[Dict]] | executor 执行结果 |
| `plan` | Optional[Dict] | planner 生成的测试计划 |
| `review` | Optional[Dict] | reviewer 生成的审查报告 |
| `plan_error` | Optional[str] | planner 错误信息 |
| `execution_error` | Optional[str] | executor 错误信息 |
| `retry_count` | int | 已重试次数 |
| `max_retries` | int | 最大重试次数 (默认 1) |
| `failed_phase` | Optional[str] | 失败的节点名，用于重试路由 |
| `current_phase` | Optional[str] | 当前阶段 |
| `final_result` | Optional[Dict] | 最终结果 (存入数据库) |

## 错误处理策略

| 阶段 | 错误类型 | 处理方式 |
|------|---------|---------|
| Planning | LLM 失败/解析错误 | 重试 1 次，失败则生成错误结果 |
| Execution | Playwright 超时 | 重试 1 次，失败则标记所有步骤失败 |
| Execution | 无 Page 对象 | 立即失败 (配置错误) |
| Review | LLM 失败/解析错误 | **非致命**，设置 `review_error`，流水线继续 |
| 任何阶段 | `retry_count > max_retries` | 路由到 result_builder 生成错误结果 |

## 集成方式

Celery 任务 (`test_execution.py`) 负责 Playwright 浏览器生命周期管理，通过 `RunnableConfig` 将 Page 对象传入图：

```python
graph = build_pipeline_graph()
result = await graph.ainvoke(
    initial_state,
    config={"configurable": {"page": page, "run_id": run_id}}
)
```
