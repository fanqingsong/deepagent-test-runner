"""
LangGraph Server 导出模块
将 Deep Agents 导出给 LangGraph server 使用
"""

from app.agents.chat_agent import ChatAgent
from app.core.agent_config import get_llm

# 创建全局 agent 实例
_agent = None

def get_chat_agent():
    """获取或创建聊天 agent 单例"""
    global _agent
    if _agent is None:
        _agent = ChatAgent()
    return _agent

# 导出 agent 实例给 LangGraph server
def agent():
    """LangGraph server 入口点"""
    chat_agent = get_chat_agent()
    return chat_agent.agent

__all__ = ["agent"]
