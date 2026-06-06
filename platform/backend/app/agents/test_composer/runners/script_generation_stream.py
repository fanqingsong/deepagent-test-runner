"""
Streaming script generation runner — yields SSE events as the subagent executes.

Uses LangChain's astream_events(v2) to observe tool calls, LLM tokens,
and chain lifecycle in real-time, then maps them to typed SSE events.
"""

import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from app.core.llm_context import llm_usage_context

logger = logging.getLogger(__name__)

# Step definitions: tool name → human-readable step label
_TOOL_STEP_MAP = {
    "fetch_page_context_tool": "Fetching page context",
    "validate_script": "Validating script",
    "execute_script_tool": "Executing in sandbox",
    "save_generated_script": "Saving result",
}


def _sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


async def run_script_generation_stream(
    test_definition_id: int,
    url: str,
    goal: str,
    description: str = None,
) -> AsyncGenerator[str, None]:
    """Run script generation and yield SSE events in real-time."""
    from ..subagents import get_script_generator_subagent
    from app.core.agent_config import get_llm

    llm = get_llm(temperature=0.3, max_tokens=4096)
    subagent = get_script_generator_subagent(llm)

    desc_section = f"\nDescription: {description}" if description else ""
    prompt = f"""Generate a Playwright test script for this test case:

Test Definition ID: {test_definition_id}
Test Goal: {goal}
Target URL: {url}{desc_section}

Follow the Workflow:
1. Fetch page context
2. Generate the script
3. Validate it
4. Execute it
5. If it fails, fix and retry (up to 3 attempts)
6. Save the final result"""

    current_step = "Initializing"
    tool_calls_log: list[dict] = []

    yield _sse("step_started", {"step": current_step})

    try:
        async with llm_usage_context("script_generator", test_run_id=f"gen_{test_definition_id}"):
            stream = subagent["runnable"].astream_events(
                {"messages": [HumanMessage(content=prompt)]},
                version="v2",
                config={"recursion_limit": 50},
            )

            async for event in stream:
                kind = event.get("event", "")
                name = event.get("name", "")
                data = event.get("data", {})

                # --- Tool call started ---
                if kind == "on_tool_start" and name in _TOOL_STEP_MAP:
                    step_label = _TOOL_STEP_MAP[name]
                    if step_label != current_step:
                        yield _sse("step_completed", {"step": current_step, "status": "done"})
                        current_step = step_label
                        yield _sse("step_started", {"step": current_step})

                    input_args = data.get("input", {})
                    tool_calls_log.append({"name": name, "status": "running"})
                    yield _sse("tool_call", {
                        "tool": name,
                        "args": {k: _truncate(str(v)) for k, v in input_args.items()},
                    })

                # --- Tool call finished ---
                elif kind == "on_tool_end" and name in _TOOL_STEP_MAP:
                    output = data.get("output", {})
                    output_str = str(output)
                    is_error = '"error"' in output_str and '"status": "error"' in output_str

                    # Update tool log
                    for tc in reversed(tool_calls_log):
                        if tc["name"] == name and tc["status"] == "running":
                            tc["status"] = "error" if is_error else "done"
                            break

                    yield _sse("tool_result", {
                        "tool": name,
                        "result_preview": _truncate(output_str),
                        "is_error": is_error,
                    })

                    # If execute failed, next LLM call is a retry
                    if name == "execute_script_tool" and is_error:
                        yield _sse("step_completed", {"step": current_step, "status": "error"})
                        current_step = "Retrying (fixing script)"
                        yield _sse("step_started", {"step": current_step})

                # --- LLM streaming token ---
                elif kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                        if text.strip():
                            # Detect step: if no tool called yet, we're generating
                            if current_step == "Initializing":
                                yield _sse("step_completed", {"step": current_step, "status": "done"})
                                current_step = "Generating script"
                                yield _sse("step_started", {"step": current_step})

                            yield _sse("llm_token", {"text": text})

    except Exception as e:
        logger.error("Streaming script generation failed: %s", e)
        yield _sse("step_completed", {"step": current_step, "status": "error"})
        yield _sse("error", {"message": str(e)})
        # Try to mark as failed in DB
        try:
            from app.models.test_definition import TestDefinition
            from sqlalchemy import select as sa_select
            from ..tools.db_tools import _run_with_db

            async def _mark_failed(session):
                r = await session.execute(
                    sa_select(TestDefinition).where(TestDefinition.id == test_definition_id)
                )
                td = r.scalar_one_or_none()
                if td and td.script_status == "generating":
                    td.script_status = "failed"
                    td.script_metadata = {"error": str(e)}

            await _run_with_db(_mark_failed)
        except Exception:
            logger.error("Failed to mark generation as failed in DB")
        return

    # Read back the final result from DB (saved by save_generated_script tool)
    yield _sse("step_completed", {"step": current_step, "status": "done"})

    from ..tools.db_tools import _run_with_db
    from app.models.test_definition import TestDefinition
    from sqlalchemy import select as sa_select

    async def _read_final(session):
        r = await session.execute(
            sa_select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        td = r.scalar_one_or_none()
        if td:
            return {
                "playwright_script": td.playwright_script,
                "script_status": td.script_status,
                "script_metadata": td.script_metadata or {},
                "execution_mode": td.execution_mode,
            }
        return {
            "playwright_script": None,
            "script_status": "failed",
            "script_metadata": {"error": "Failed to read back result"},
            "execution_mode": "script",
        }

    final = await _run_with_db(_read_final)
    yield _sse("done", final)
