"""
Test endpoint to inspect stream chunk structure.
"""
from fastapi import APIRouter
from app.agents.deepagent.chat_agent import get_chat_agent

router = APIRouter()

@router.get("/test-stream")
async def test_stream():
    """Test endpoint to inspect stream chunks."""
    chat_agent = get_chat_agent()

    chunks = []
    async for chunk in chat_agent.agent.stream(
        {"messages": [{"role": "user", "content": "Hello"}]},
        config={"configurable": {"thread_id": "test-thread"}},
        stream_mode=["updates", "messages"],
        subgraphs=True,
        version="v2",
    ):
        chunks.append({
            "type": str(chunk.get("type")),
            "keys": list(chunk.keys()),
            "ns": chunk.get("ns"),
            "sample": str(chunk.get("data"))[:200] if chunk.get("data") else None
        })
        if len(chunks) >= 10:  # Limit to first 10 chunks
            break

    return {"chunks": chunks}
