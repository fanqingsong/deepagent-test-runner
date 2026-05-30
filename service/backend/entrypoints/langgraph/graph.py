"""
LangGraph Server 导出模块
将 Deep Agents 导出给 LangGraph server 使用
"""

import concurrent.futures
import logging

from app.agents.deepagent.chat_agent import ChatAgent

logger = logging.getLogger(__name__)

# 全局 agent 实例
_agent: ChatAgent | None = None


def _get_chat_agent() -> ChatAgent:
    global _agent
    if _agent is None:
        _agent = ChatAgent()
    return _agent


def _run_async_in_thread(coro):
    """Run an async coroutine in a separate thread to avoid event loop conflicts."""
    import asyncio

    def _runner():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_runner)
        return future.result()


def _init_and_get_agent():
    """同步初始化并返回 compiled agent（含 PostgreSQL checkpointer）."""
    chat_agent = _get_chat_agent()
    if not chat_agent._ready:
        _run_async_in_thread(chat_agent._ensure_store())
    return chat_agent.agent


# 导出 agent 实例给 LangGraph server
def agent():
    """LangGraph server 入口点"""
    return _init_and_get_agent()


__all__ = ["agent"]
