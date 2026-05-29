"""
聊天流式端点 - 支持 LangGraph useStream 协议

提供 Server-Sent Events (SSE) 端点，兼容 @langchain/react 的 useStream hook。
"""
import asyncio
import json
import logging
from typing import AsyncIterator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_config
from starlette.middleware.cors import CORSMiddleware

from app.core.agent_config import get_llm
from app.core.security import get_current_user_ws
from app.agents.deepagent.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
    get_search_subagent,
)
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatStreamAgent:
    """专用于流式响应的聊天 Agent"""

    def __init__(self):
        self.checkpointer = MemorySaver()
        llm = get_llm(temperature=0.7, max_tokens=8192)

        self.agent = create_deep_agent(
            model=llm,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt(),
            memory=["/memories/AGENTS.md"],
            backend=CompositeBackend(
                default=StateBackend(),
                routes={
                    "/memories/": StoreBackend(
                        namespace=lambda rt: ("user", str(get_config().get("metadata", {}).get("user_id", "default")))
                    ),
                },
            ),
            subagents=[
                get_test_query_subagent(llm),
                get_user_admin_subagent(llm),
                get_test_reviewer_subagent(llm),
                get_analytics_subagent(llm),
                get_search_subagent(llm),
            ],
            debug=True,
        )
        logger.info("Stream chat agent initialized")

    def _get_system_prompt(self) -> str:
        return """You are an AI assistant for the E2E testing platform. You coordinate specialized subagents to help users with various tasks.

**Your Role:**
You are the main coordinator that routes user requests to appropriate specialized subagents using the `task` tool.

**How to Work:**
1. Analyze the user's request and delegate to the appropriate subagent
2. When multiple subagents are needed, coordinate them sequentially
3. Synthesize the subagent results into a helpful, human-readable response

**Memory & Context:**
Use your memory filesystem (/memories/) to persist important information across conversations. When the user shares their name, preferences, or project details, write them to /memories/AGENTS.md so you can recall them later.

**Response Guidelines:**
- Don't just repeat the subagent output - explain it in context
- For actions requiring permissions, ensure the subagent explains what will happen first
- When a user lacks permission, explain the requirement clearly
- Be concise but thorough"""


# 全局 agent实例
_stream_agent = None


def get_stream_agent():
    """获取流式聊天 agent单例"""
    global _stream_agent
    if _stream_agent is None:
        _stream_agent = ChatStreamAgent()
    return _stream_agent


@router.post("/stream")
async def chat_stream_endpoint(request: Request):
    """
    SSE 端点，兼容 @langchain/react useStream 协议

    useStream 会发送 POST 请求到这个端点，包含：
    - thread_id: 线程ID (在config中)
    - messages: 消息列表
    - config: 配置信息
    """
    # 提取认证信息
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"error": "Missing authorization"}

    token = auth_header.split(" ")[1]

    # 简化的用户ID提取（实际应该验证JWT）
    user_id = 1  # 暂时硬编码

    # 读取请求体 - 必须在返回StreamingResponse之前
    body = await request.body()
    if isinstance(body, bytes):
        body = body.decode()

    data = json.loads(body) if body else {}
    messages = data.get("messages", [])
    config_data = data.get("config", {})

    # 获取thread_id
    thread_id = config_data.get("configurable", {}).get("thread_id", "default-thread")

    # 创建 agent 输入
    agent_input = {"messages": messages}

    config = {
        "configurable": {
            "thread_id": thread_id,
            **config_data.get("configurable", {})
        },
        "metadata": {"user_id": user_id},
    }

    agent = get_stream_agent()

    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 流式处理
            for chunk in agent.agent.stream(
                agent_input,
                config=config,
                stream_mode=["updates", "messages"],
                subgraphs=True,
                version="v2",
            ):
                # 转换为 SSE 格式
                event_data = json.dumps(chunk)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.exception("Stream error")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
