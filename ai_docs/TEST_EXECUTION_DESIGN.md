# 测试用例执行设计文档

## 文档概述

**项目:** Claude Code Test Runner - AI-Powered Test Planning System  
**版本:** 2.0  
**日期:** 2026-05-16  
**作者:** AI Architecture Team  
**状态:** 生产就绪

---

## 目录

1. [系统架构](#系统架构)
2. [执行流程](#执行流程)
3. [AI驱动的测试执行](#ai驱动的测试执行)
4. [自适应决策机制](#自适应决策机制)
5. [错误恢复策略](#错误恢复策略)
6. [性能优化](#性能优化)
7. [监控与日志](#监控与日志)

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        测试执行架构                              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   前端 UI    │ ───> │   API 层     │ ───> │  任务队列    │
│  TestForm    │      │  FastAPI     │      │   Redis     │
└──────────────┘      └──────────────┘      └──────────────┘
                              │
                              ↓
┌───────────────────────────────────────────────────────────────┐
│                      后端执行服务                              │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │        Autonomous Test Planner (AI规划器)            │    │
│  │  • 自然语言目标解析                                   │    │
│  │  • 测试计划生成 (3-8步骤)                            │    │
│  │  • 风险评估与置信度评分                               │    │
│  └──────────────────────────────────────────────────────┘    │
│                           │                                    │
│                           ↓                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │      Claude Agent SDK 执行引擎                        │    │
│  │  • 自适应测试执行                                     │    │
│  │  • 实时决策制定                                       │    │
│  │  • 错误恢复与重试                                     │    │
│  └──────────────────────────────────────────────────────┘    │
│                           │                                    │
│                           ↓                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Playwright 浏览器自动化                        │    │
│  │  • 页面导航与交互                                     │    │
│  │  • 元素定位与操作                                     │    │
│  │  • 截图与证据收集                                     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据持久化层                              │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL: test_runs, test_cases, test_steps              │
│  Redis: 任务状态, 执行进度, 实时决策缓存                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 执行流程

### 1. 传统执行流程 vs AI驱动执行

#### 传统执行流程
```python
# 传统方式: 固定步骤执行
def execute_test_traditional(test_steps):
    results = []
    for step in test_steps:
        try:
            result = execute_step(step)
            results.append(result)
        except Exception as e:
            # 简单失败, 无适应性
            results.append({"status": "failed", "error": str(e)})
            break  # 停止执行
    return results
```

#### AI驱动执行流程
```python
# AI方式: 自适应执行
async def execute_test_ai_driven(test_goal, ai_plan):
    results = []
    current_plan = ai_plan.copy()
    execution_context = {"attempts": 0, "decisions": []}
    
    for step in current_plan["steps"]:
        # 执行步骤
        result = await execute_step_with_adaptive_recovery(
            step, 
            execution_context
        )
        
        # AI决策: 是否继续、重试、跳过或中止
        if not result["success"]:
            decision = await make_execution_decision(
                current_step=step,
                page_state=get_page_state(),
                execution_history=results,
                ai_context=execution_context
            )
            
            # 根据AI决策调整执行策略
            if decision["action"] == "retry":
                result = await retry_with_modifications(
                    step, 
                    decision["modifications"]
                )
            elif decision["action"] == "skip":
                continue  # 跳过当前步骤
            elif decision["action"] == "abort":
                break  # 中止执行
        
        results.append(result)
        execution_context["decisions"].append(decision)
    
    return results
```

### 2. 详细执行步骤

#### 阶段1: 初始化与准备
```python
async def initialize_test_execution(test_definition_id):
    """初始化测试执行环境"""
    
    # 1. 从数据库加载测试定义
    test_def = await load_test_definition(test_definition_id)
    
    # 2. 检查是否有AI生成的计划
    if test_def.ai_generated_plan:
        execution_plan = test_def.ai_generated_plan
        mode = "ai_adaptive"
    else:
        # 兼容传统步骤
        execution_plan = convert_steps_to_plan(test_def.test_steps)
        mode = "traditional"
    
    # 3. 创建测试运行记录
    test_run = await create_test_run(
        test_definition_id=test_definition_id,
        execution_mode=mode,
        total_steps=len(execution_plan["steps"])
    )
    
    # 4. 初始化浏览器环境
    browser_context = await initialize_browser(
        url=test_def.url,
        environment=test_def.environment
    )
    
    return {
        "test_run_id": test_run.id,
        "execution_plan": execution_plan,
        "browser_context": browser_context,
        "mode": mode
    }
```

#### 阶段2: AI驱动的步骤执行
```python
async def execute_step_with_ai(step, browser_context, execution_history):
    """使用AI增强的步骤执行"""
    
    # 1. 预处理: 根据页面状态调整参数
    page_analysis = await analyze_current_page(browser_context)
    modified_step = preprocess_step(step, page_analysis)
    
    # 2. 执行核心操作
    try:
        result = await execute_core_action(
            browser_context, 
            modified_step
        )
        
        # 3. 智能验证
        verification_result = await intelligent_verify(
            expected=step.verification,
            actual=page_analysis,
            confidence=step.confidence
        )
        
        if not verification_result.passed:
            # AI决策: 是否应该通过
            decision = await should_pass_with_warnings(
                step, 
                verification_result,
                execution_history
            )
            verification_result.passed = decision.approve
        
        result["verification"] = verification_result
        result["success"] = verification_result.passed
        
    except Exception as error:
        # 错误恢复决策
        result = await handle_execution_error(
            step, 
            error, 
            browser_context,
            execution_history
        )
    
    # 4. 记录执行数据
    result["screenshot"] = await capture_screenshot(browser_context)
    result["page_state"] = page_analysis
    result["execution_time"] = time.time() - start_time
    
    return result
```

#### 阶段3: 自适应决策制定
```python
async def make_execution_decision(current_step, page_state, execution_history):
    """AI驱动的实时决策制定"""
    
    # 1. 分析失败原因
    failure_analysis = await analyze_failure(
        current_step, 
        page_state, 
        execution_history
    )
    
    # 2. 评估继续执行的可能性
    continuation_probability = await assess_continuation(
        current_step,
        failure_analysis,
        execution_history
    )
    
    # 3. 制定决策
    if continuation_probability > 0.7:
        # 高置信度: 可以重试
        return {
            "action": "retry",
            "reason": "Recoverable error detected",
            "modifications": await generate_recovery_strategy(
                current_step, 
                failure_analysis
            )
        }
    elif continuation_probability > 0.3:
        # 中等置信度: 跳过当前步骤
        return {
            "action": "skip", 
            "reason": "Step not critical for overall goal",
            "modifications": {}
        }
    else:
        # 低置信度: 中止执行
        return {
            "action": "abort",
            "reason": "Critical failure preventing continuation",
            "modifications": {}
        }
```

---

## AI驱动的测试执行

### 1. Claude Agent SDK 集成

```python
class ClaudeAIExecutor:
    """Claude Agent SDK 驱动的测试执行器"""
    
    def __init__(self, api_key, base_url):
        self.client = Anthropic(api_key=api_key, base_url=base_url)
        self.agent = None
        
    async def initialize_agent(self, test_goal, execution_plan):
        """初始化AI代理"""
        
        system_prompt = f"""You are an adaptive test execution AI.

**Test Goal:**
{test_goal}

**Execution Plan:**
{self._format_plan(execution_plan)}

**Your Capabilities:**
- Execute browser automation via Playwright
- Make intelligent decisions when steps fail
- Adapt to dynamic page conditions
- Recover from errors automatically
- Decide when to continue, retry, skip, or abort

**Error Recovery Strategies:**
- Wait longer for dynamic content
- Try alternative selectors
- Navigate to parent elements first
- Clear cookies and retry
- Abort if critical path is blocked

You have full autonomy to make execution decisions."""
        
        self.agent = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=[
                {
                    "type": "browser_automation",
                    "name": "execute_browser_action",
                    "description": "Execute browser actions via Playwright"
                },
                {
                    "type": "decision_support",
                    "name": "make_execution_decision",
                    "description": "Make intelligent execution decisions"
                }
            ]
        )
        
    async def execute_step_adaptive(self, step, page_context):
        """自适应执行单个步骤"""
        
        prompt = f"""Execute the following test step:

**Step:** {step['description']}
**Type:** {step['type']}
**Confidence:** {step['confidence']}
**Verification:** {step['verification']}

**Current Page Context:**
{page_context}

**Fallback Strategies:**
{step['fallback_strategies']}

Execute this step and report back with:
1. Success status
2. Actual results vs expected
3. Any adaptations made
4. Suggested next actions"""

        response = await self.agent.tools.execute_browser_action(
            prompt=prompt,
            step_data=step,
            page_context=page_context
        )
        
        return response
```

### 2. 执行模式对比

#### 传统模式 (Traditional Mode)
```python
# 传统模式: 严格执行预定义步骤
async def traditional_execution(test_steps):
    for step in test_steps:
        result = await execute_step(step)
        if not result.success:
            return {"status": "failed", "failed_at": step.step_number}
    return {"status": "passed"}
```

#### AI自适应模式 (AI Adaptive Mode)
```python
# AI自适应模式: 智能调整执行策略
async def ai_adaptive_execution(test_goal, ai_plan):
    execution_log = []
    adaptive_decisions = []
    
    for step in ai_plan["steps"]:
        # 执行步骤
        result = await execute_step_with_ai(step)
        
        # 记录执行
        execution_log.append(result)
        
        # 如果失败, 进行AI决策
        if not result.success:
            decision = await make_ai_decision(
                step=step,
                result=result,
                execution_history=execution_log,
                test_goal=test_goal
            )
            
            adaptive_decisions.append(decision)
            
            # 根据决策行动
            if decision.action == "retry":
                step = apply_modifications(step, decision.modifications)
                result = await execute_step_with_ai(step)
            elif decision.action == "skip":
                continue
            elif decision.action == "abort":
                break
        
        execution_log.append(result)
    
    return {
        "status": determine_final_status(execution_log),
        "execution_log": execution_log,
        "adaptive_decisions": adaptive_decisions,
        "execution_variance": calculate_variance(ai_plan, execution_log)
    }
```

---

## 自适应决策机制

### 1. 决策制定框架

```python
class AdaptiveDecisionEngine:
    """自适应决策引擎"""
    
    async def make_decision(self, context):
        """制定执行决策"""
        
        # 1. 收集上下文信息
        failure_context = await self.analyze_failure(context)
        
        # 2. 评估严重程度
        severity = await self.assess_severity(
            failure_context,
            context.test_goal,
            context.execution_history
        )
        
        # 3. 生成决策选项
        options = await self.generate_decision_options(
            severity,
            failure_context,
            context
        )
        
        # 4. 选择最优决策
        decision = await self.select_best_decision(
            options,
            context.test_goal
        )
        
        return decision
    
    async def analyze_failure(self, context):
        """分析失败原因"""
        return {
            "error_type": classify_error(context.error),
            "affected_element": identify_element(context.page_state),
            "timing": context.execution_time,
            "page_state": context.page_state,
            "network_status": await check_network_health(),
            "similar_failures": await find_similar_failures(context)
        }
    
    async def assess_severity(self, failure_context, test_goal, history):
        """评估失败严重程度"""
        
        severity_score = 0.0
        
        # 因素1: 对测试目标的影响
        goal_impact = await assess_goal_impact(failure_context, test_goal)
        severity_score += goal_impact * 0.4
        
        # 因素2: 历史成功率
        historical_success = calculate_historical_success(history)
        severity_score += (1 - historical_success) * 0.3
        
        # 因素3: 错误类型严重性
        error_severity = get_error_severity(failure_context.error_type)
        severity_score += error_severity * 0.3
        
        return min(severity_score, 1.0)  # 归一化到 [0,1]
```

### 2. 决策策略

```python
DECISION_STRATEGIES = {
    "continue": {
        "condition": lambda ctx: ctx.confidence > 0.8 and ctx.recovery_attempts < 2,
        "action": "proceed_to_next_step",
        "reason": "High confidence step succeeded"
    },
    
    "retry": {
        "condition": lambda ctx: (
            ctx.recovery_attempts < ctx.max_retries and
            ctx.error_recovery_probability > 0.6
        ),
        "action": "retry_with_modifications",
        "modifications": [
            "increase_timeout",
            "alternative_selector",
            "wait_for_element",
            "clear_cache"
        ],
        "reason": "Recoverable error with fallback options"
    },
    
    "skip": {
        "condition": lambda ctx: (
            ctx.step_criticality < 0.5 and
            ctx.error_type in ["non_critical", "cosmetic"]
        ),
        "action": "skip_step_continue_execution",
        "reason": "Non-critical step, overall goal still achievable"
    },
    
    "abort": {
        "condition": lambda ctx: (
            ctx.critical_path_blocked or
            ctx.recovery_attempts >= ctx.max_retries or
            ctx.continuation_probability < 0.2
        ),
        "action": "stop_execution",
        "reason": "Critical failure preventing goal achievement"
    }
}
```

---

## 错误恢复策略

### 1. 分层恢复机制

```python
class ErrorRecoveryManager:
    """分层错误恢复管理器"""
    
    async def recover_from_error(self, error, context):
        """执行分层恢复"""
        
        # 第1层: 快速恢复 (秒级)
        quick_recovery = await self.try_quick_recovery(error, context)
        if quick_recovery.success:
            return quick_recovery
        
        # 第2层: 中等恢复 (秒级到分钟级)
        medium_recovery = await self.try_medium_recovery(error, context)
        if medium_recovery.success:
            return medium_recovery
        
        # 第3层: 深度恢复 (分钟级)
        deep_recovery = await self.try_deep_recovery(error, context)
        return deep_recovery
    
    async def try_quick_recovery(self, error, context):
        """快速恢复策略"""
        
        quick_strategies = [
            # 策略1: 增加超时时间
            {
                "name": "increase_timeout",
                "condition": lambda e: "timeout" in str(e).lower(),
                "action": lambda: retry_with_timeout(context.step, timeout * 2)
            },
            
            # 策略2: 等待元素可见
            {
                "name": "wait_for_element",
                "condition": lambda e: "not visible" in str(e).lower(),
                "action": lambda: wait_for_element_visibility(context.element, timeout=5000)
            },
            
            # 策略3: 重试点击
            {
                "name": "retry_click",
                "condition": lambda e: "click" in str(e).lower(),
                "action": lambda: retry_click(context.element, delay=1000)
            }
        ]
        
        for strategy in quick_strategies:
            if strategy["condition"](error):
                try:
                    result = await strategy["action"]()
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=strategy["name"],
                            duration=time.time() - start_time
                        )
                except Exception as e:
                    continue
        
        return RecoveryResult(success=False, strategy="none")
    
    async def try_medium_recovery(self, error, context):
        """中等恢复策略"""
        
        medium_strategies = [
            # 策略1: 替代选择器
            {
                "name": "alternative_selector",
                "action": lambda: try_alternative_selectors(
                    context.element,
                    generate_css_variants(context.selector)
                )
            },
            
            # 策略2: 页面刷新
            {
                "name": "page_refresh",
                "action": lambda: refresh_page_and_retry(
                    context.step,
                    preserve_state=True
                )
            },
            
            # 策略3: 导航到父元素
            {
                "name": "parent_navigation",
                "action": lambda: navigate_via_parent_elements(
                    context.element,
                    context.step.action
                )
            }
        ]
        
        # 实现类似的恢复逻辑...
        return await self._try_recovery_strategies(medium_strategies, error, context)
    
    async def try_deep_recovery(self, error, context):
        """深度恢复策略"""
        
        deep_strategies = [
            # 策略1: 清除缓存和Cookie
            {
                "name": "clear_browser_data",
                "action": lambda: clear_browser_data_and_retry(
                    context.step,
                    clear_cache=True,
                    clear_cookies=True
                )
            },
            
            # 策略2: 重新导航
            {
                "name": "renavigate",
                "action": lambda: full_navigation_retry(
                    context.url,
                    context.step
                )
            },
            
            # 策略3: 替代执行方法
            {
                "name": "alternative_execution",
                "action": lambda: use_alternative_execution_method(
                    context.step,
                    context.page_state
                )
            }
        ]
        
        return await self._try_recovery_strategies(deep_strategies, error, context)
```

### 2. 恢复策略数据库

```python
RECOVERY_STRATEGIES = {
    "timeout_errors": {
        "strategies": [
            {"name": "increase_timeout", "multiplier": 2},
            {"name": "wait_for_idle", "timeout": 30000},
            {"name": "slow_motion", "delay_multiplier": 3}
        ],
        "success_rate": 0.85,
        "avg_duration": 5000  # 毫秒
    },
    
    "element_not_found": {
        "strategies": [
            {"name": "alternative_selectors", "variants": ["css", "xpath", "text"]},
            {"name": "wait_for_animation", "timeout": 2000},
            {"name": "scroll_into_view", "behavior": "smooth"}
        ],
        "success_rate": 0.78,
        "avg_duration": 3000
    },
    
    "stale_element": {
        "strategies": [
            {"name": "refresh_element", "method": "DOM_query"},
            {"name": "page_refresh", "preserve_state": True},
            {"name": "relocate_element", "strategy": "search_from_parent"}
        ],
        "success_rate": 0.92,
        "avg_duration": 2000
    },
    
    "network_error": {
        "strategies": [
            {"name": "retry_request", "max_attempts": 3},
            {"name": "check_connection", "action": "verify_network"},
            {"name": "alternative_endpoint", "fallback": True}
        ],
        "success_rate": 0.67,
        "avg_duration": 8000
    }
}
```

---

## 性能优化

### 1. 并行执行优化

```python
class ParallelExecutionOptimizer:
    """并行执行优化器"""
    
    async def optimize_execution_plan(self, execution_plan):
        """优化执行计划以支持并行执行"""
        
        # 1. 构建依赖图
        dependency_graph = self._build_dependency_graph(execution_plan)
        
        # 2. 识别可并行执行的步骤组
        parallel_groups = self._identify_parallel_groups(dependency_graph)
        
        # 3. 生成优化后的执行计划
        optimized_plan = {
            "parallel_groups": parallel_groups,
            "estimated_duration": self._estimate_parallel_duration(parallel_groups),
            "resource_requirements": self._calculate_resources(parallel_groups)
        }
        
        return optimized_plan
    
    async def execute_parallel(self, optimized_plan):
        """并行执行优化后的计划"""
        
        results = []
        
        for group in optimized_plan["parallel_groups"]:
            if len(group) == 1:
                # 串行执行
                result = await self._execute_single(group[0])
                results.append(result)
            else:
                # 并行执行
                group_results = await asyncio.gather(
                    *[self._execute_single(step) for step in group],
                    return_exceptions=True
                )
                results.extend(group_results)
        
        return results
```

### 2. 缓存与预加载

```python
class ExecutionCacheManager:
    """执行缓存管理器"""
    
    def __init__(self):
        self.page_state_cache = LRUCache(maxsize=100)
        self.selector_cache = {}
        self.execution_pattern_cache = {}
    
    async def cache_page_state(self, url, page_state):
        """缓存页面状态"""
        self.page_state_cache[url] = {
            "state": page_state,
            "timestamp": time.time(),
            "ttl": 300  # 5分钟过期
        }
    
    async def get_cached_state(self, url):
        """获取缓存的页面状态"""
        if url in self.page_state_cache:
            cached = self.page_state_cache[url]
            if time.time() - cached["timestamp"] < cached["ttl"]:
                return cached["state"]
        return None
    
    async def optimize_selector(self, selector):
        """优化选择器"""
        if selector in self.selector_cache:
            return self.selector_cache[selector]
        
        # 生成更高效的选择器
        optimized = await self._generate_optimized_selector(selector)
        self.selector_cache[selector] = optimized
        return optimized
```

---

## 监控与日志

### 1. 执行监控

```python
class ExecutionMonitor:
    """执行监控器"""
    
    async def monitor_execution(self, test_run_id):
        """监控测试执行"""
        
        while True:
            # 获取当前执行状态
            status = await self.get_execution_status(test_run_id)
            
            # 检查异常情况
            if status["duration"] > status["estimated_duration"] * 1.5:
                await self.alert_slow_execution(test_run_id, status)
            
            if status["failure_rate"] > 0.5:
                await self.alert_high_failure_rate(test_run_id, status)
            
            if status["memory_usage"] > 0.8:
                await self.alert_memory_pressure(test_run_id, status)
            
            # 更新实时指标
            await self.update_metrics(test_run_id, status)
            
            if status["completed"]:
                break
            
            await asyncio.sleep(5)
```

### 2. 详细日志记录

```python
class ExecutionLogger:
    """执行日志记录器"""
    
    async def log_step_execution(self, step, result, context):
        """记录步骤执行详情"""
        
        log_entry = {
            "timestamp": time.time(),
            "step_number": step["step_number"],
            "description": step["description"],
            "expected": step["verification"],
            "actual": result.get("actual_result"),
            "success": result["success"],
            "duration": result["duration"],
            "screenshot": result.get("screenshot_path"),
            "page_state": result.get("page_state"),
            "adaptive_decisions": result.get("adaptive_decisions", []),
            "error": result.get("error"),
            "metadata": {
                "confidence": step.get("confidence"),
                "retry_count": result.get("retry_count", 0),
                "recovery_strategies": result.get("recovery_strategies", [])
            }
        }
        
        # 保存到数据库
        await self.save_to_database(log_entry)
        
        # 保存到文件系统
        await self.save_to_filesystem(log_entry)
        
        # 实时日志流
        await self.stream_to_dashboard(log_entry)
```

---

## 执行示例

### 完整执行流程示例

```python
# 示例: AI驱动的登录测试执行

async def execute_ai_test_example():
    """AI驱动测试执行完整示例"""
    
    # 1. 用户输入自然语言目标
    test_goal = """
    Test user login functionality with valid credentials.
    Verify that users can successfully log in with valid 
    credentials and cannot log in with invalid credentials.
    Also check that the 'Remember Me' feature works correctly.
    """
    
    # 2. AI生成测试计划
    ai_plan = await generate_ai_plan(
        goal=test_goal,
        url="http://example.com/login",
        context={"browser": "chrome"}
    )
    
    # AI生成的计划示例:
    # {
    #   "plan_id": "abc123",
    #   "steps": [
    #     {
    #       "step_number": 1,
    #       "description": "Navigate to login page",
    #       "type": "navigation",
    #       "confidence": 0.99,
    #       "verification": "URL is /login and login form is visible",
    #       "fallback_strategies": ["wait_for_page_load", "refresh_page"]
    #     },
    #     {
    #       "step_number": 2,
    #       "description": "Enter valid username and password",
    #       "type": "input",
    #       "confidence": 0.95,
    #       "verification": "Input fields contain entered values",
    #       "fallback_strategies": ["clear_fields_first", "slow_typing"]
    #     },
    #     # ... 更多步骤
    #   ],
    #   "estimated_duration": 120,
    #   "risk_factors": ["dynamic_content", "captcha"],
    #   "success_criteria": ["user_logged_in", "dashboard_visible"]
    # }
    
    # 3. 初始化AI执行引擎
    executor = ClaudeAIExecutor(
        api_key="your-api-key",
        base_url="https://api.anthropic.com"
    )
    
    await executor.initialize_agent(test_goal, ai_plan)
    
    # 4. 执行测试 (自适应执行)
    execution_results = []
    
    for step in ai_plan["steps"]:
        print(f"Executing step {step['step_number']}: {step['description']}")
        
        # 执行步骤 (包含自动错误恢复)
        result = await executor.execute_step_adaptive(
            step=step,
            page_context=await get_current_page_state()
        )
        
        print(f"Result: {result['success']}")
        print(f"Confidence: {result['confidence']}")
        
        if result['adaptive_decisions']:
            print(f"AI Decisions: {result['adaptive_decisions']}")
        
        execution_results.append(result)
        
        # 如果关键步骤失败, AI决定是否继续
        if not result['success'] and step.get('critical', False):
            decision = await executor.make_continuation_decision(
                current_step=step,
                result=result,
                execution_history=execution_results
            )
            
            print(f"AI Decision: {decision['action']} - {decision['reason']}")
            
            if decision['action'] == 'abort':
                print("Critical failure, aborting execution")
                break
    
    # 5. 生成执行报告
    execution_report = {
        "test_goal": test_goal,
        "total_steps": len(ai_plan["steps"]),
        "passed_steps": sum(1 for r in execution_results if r["success"]),
        "failed_steps": sum(1 for r in execution_results if not r["success"]),
        "adaptive_decisions_made": sum(
            1 for r in execution_results if r.get("adaptive_decisions")
        ),
        "execution_variance": calculate_variance(ai_plan, execution_results),
        "final_status": determine_final_status(execution_results),
        "duration": sum(r["duration"] for r in execution_results),
        "ai_confidence": calculate_overall_confidence(execution_results)
    }
    
    print("\n=== EXECUTION REPORT ===")
    print(f"Status: {execution_report['final_status']}")
    print(f"Passed: {execution_report['passed_steps']}/{execution_report['total_steps']}")
    print(f"AI Decisions: {execution_report['adaptive_decisions_made']}")
    print(f"Overall Confidence: {execution_report['ai_confidence']:.2%}")
    
    return execution_report
```

---

## 总结

### 关键特性

1. **AI驱动的智能执行**
   - 自然语言测试目标理解
   - 自适应决策制定
   - 实时错误恢复

2. **多层次错误处理**
   - 快速恢复 (秒级)
   - 中等恢复 (秒级到分钟级)
   - 深度恢复 (分钟级)

3. **性能优化**
   - 并行执行支持
   - 智能缓存机制
   - 资源优化管理

4. **全面监控**
   - 实时执行状态
   - 详细日志记录
   - 性能指标跟踪

### 技术优势

- **灵活性**: 从固定步骤到智能适应
- **可靠性**: 多层错误恢复机制
- **效率性**: AI优化的执行路径
- **可观测性**: 完整的执行追踪

这个设计文档提供了完整的AI驱动测试执行架构,支持从传统的固定步骤执行到智能自适应执行的无缝升级。
