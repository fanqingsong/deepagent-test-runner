"""
LangGraph Server 导出模块
将 Deep Agents 导出给 LangGraph server 使用
"""

import asyncio
import concurrent.futures
import logging
from datetime import datetime
from typing import Any, Dict

from app.agents.chat_assistant.chat_agent import ChatAgent

logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
root_logger.info("[TRACKING] graph.py module loaded!")
print("[TRACKING] graph.py module loaded! (print)")

# 全局 agent 实例
_agent: ChatAgent | None = None


def _get_chat_agent() -> ChatAgent:
    global _agent
    if _agent is None:
        _agent = ChatAgent()
    return _agent


def _run_async_in_thread(coro):
    """Run an async coroutine in a separate thread with its own event loop."""
    def _runner():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_runner)
        return future.result()


async def _track_session_async(thread_id: str, user_id: int):
    """异步跟踪会话到数据库。"""
    try:
        from app.services.chat_session_service import chat_session_service
        from app.core.database import async_session_maker
        from app.core.llm_context import agent_type_ctx, thread_id_ctx, user_id_ctx

        # 设置上下文变量以便其他地方可以访问
        thread_id_ctx.set(thread_id)
        user_id_ctx.set(user_id)

        async with async_session_maker() as db:
            await chat_session_service.upsert_session(db, thread_id, user_id)

        logger.info(f"Tracked chat session: thread_id={thread_id}, user_id={user_id}")
    except Exception as e:
        logger.warning(f"Failed to track chat session: {e}")


def _track_session_from_config(config: Dict[str, Any]):
    """从 LangGraph 配置中提取信息并跟踪会话。"""
    try:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        user_id = configurable.get("user_id")

        if thread_id and user_id:
            # Run async tracking in the background (fire and forget)
            asyncio.create_task(_track_session_async(thread_id, user_id))
            logger.info(f"Initiated session tracking for thread_id={thread_id}, user_id={user_id}")
    except Exception as e:
        logger.warning(f"Failed to extract config for tracking: {e}")


def _init_and_get_agent_with_tracking():
    """初始化并返回带跟踪功能的 agent。"""
    chat_agent = _get_chat_agent()
    if not chat_agent._ready:
        _run_async_in_thread(chat_agent._ensure_store())

    # 返回 agent 并添加跟踪逻辑
    agent = chat_agent.agent

    # 包装 agent 的 stream 方法来跟踪会话
    # LangGraph server 调用 stream() 而不是 invoke()
    original_stream = agent.stream

    async def tracked_stream(
        inputs,
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """包装 stream 方法，在执行前跟踪会话。"""
        logger.info(f"[TRACKING] tracked_stream called with config: {config}")

        if config is None:
            config = {}

        # 从 config 中提取 thread_id 和 user_id
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        user_id = configurable.get("user_id")

        logger.info(f"[TRACKING] Extracted thread_id={thread_id}, user_id={user_id}")

        # 如果没有 thread_id，生成一个新的
        if not thread_id:
            import uuid
            thread_id = str(uuid.uuid4())
            configurable["thread_id"] = thread_id
            config["configurable"] = configurable
            logger.info(f"[TRACKING] Generated new thread_id={thread_id}")

        # 跟踪会话 - 使用线程池执行器来运行异步代码
        if user_id:
            try:
                _run_async_in_thread(_track_session_async(thread_id, user_id))
                logger.info(f"[TRACKING] Queued session tracking for thread_id={thread_id}, user_id={user_id}")
            except Exception as e:
                logger.warning(f"[TRACKING] Failed to queue session tracking: {e}")
                logger.warning(f"[TRACKING] Exception: {e}", exc_info=True)
        else:
            logger.warning(f"[TRACKING] No user_id in config, skipping session tracking")

        # 调用原始 stream 方法
        async for event in original_stream(inputs, config, **kwargs):
            yield event

    agent.stream = tracked_stream
    logger.info("[TRACKING] Applied tracked_stream wrapper to agent")
    return agent


def _init_and_get_agent():
    """同步初始化并返回 compiled agent（含 PostgreSQL checkpointer）。"""
    chat_agent = _get_chat_agent()
    if not chat_agent._ready:
        _run_async_in_thread(chat_agent._ensure_store())
    return chat_agent.agent


# 导出 agent 实例给 LangGraph server
def agent():
    """LangGraph server 入口点 - 会话跟踪版本"""
    print("[TRACKING] agent() function called!")
    try:
        result = _init_and_get_agent_with_tracking()
        print("[TRACKING] agent() returned successfully with tracking wrapper")
        return result
    except Exception as e:
        print(f"[TRACKING] Failed to initialize agent with tracking: {e}")
        logger.warning(f"Failed to initialize agent with tracking, using fallback: {e}")
        return _init_and_get_agent()


__all__ = ["agent"]
