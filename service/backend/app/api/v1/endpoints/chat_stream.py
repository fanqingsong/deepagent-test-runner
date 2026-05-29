"""
Chat streaming SSE endpoint.

Streams structured events from ChatAgent.chat_stream() including
subagent status, tool calls, token deltas, and execution progress.
"""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agents.deepagent.chat_agent import get_chat_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stream")
async def chat_stream_endpoint(request: Request):
    """
    SSE endpoint for streaming chat with thinking/execution process.

    Accepts POST with JSON body:
    - messages: message list (last message is the user input)
    - config.configurable.thread_id: conversation thread ID
    - enable_search: boolean (default false)
    - enable_deep_thinking: boolean (default false)

    Emits SSE events with typed event names:
    - event: subagent_started / subagent_completed / subagent_progress
    - event: tool_call / tool_result
    - event: token_delta
    - event: stream_complete / error
    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"error": "Missing authorization"}

    user_id = 1  # TODO: extract from JWT

    body = await request.body()
    if isinstance(body, bytes):
        body = body.decode()

    data = json.loads(body) if body else {}
    messages = data.get("messages", [])
    config_data = data.get("config", {})
    enable_search = data.get("enable_search", False)
    enable_deep_thinking = data.get("enable_deep_thinking", False)

    thread_id = config_data.get("configurable", {}).get("thread_id", "default-thread")

    # Extract the user message from the messages array
    user_message = ""
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            user_message = last_msg.get("content", "")
        elif hasattr(last_msg, "content"):
            user_message = last_msg.content

    chat_agent = get_chat_agent()

    async def event_generator():
        try:
            async for event in chat_agent.chat_stream(
                message=user_message,
                thread_id=thread_id,
                user_id=user_id,
                enable_search=enable_search,
                enable_deep_thinking=enable_deep_thinking,
            ):
                event_type = event.get("type", "unknown")
                event_data = json.dumps(event, default=str, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {event_data}\n\n"

        except Exception as e:
            logger.exception("Stream error")
            error_data = json.dumps({"type": "error", "content": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
