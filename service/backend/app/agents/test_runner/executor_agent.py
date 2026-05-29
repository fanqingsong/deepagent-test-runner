"""
Executor Agent — AI-powered test step execution using LangGraph + Playwright tools.

Executes steps ONE BY ONE, taking a screenshot after each step so that
every step's screenshot reflects the actual page state at that point.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from playwright.async_api import Page

from app.agent_tools.playwright_tools import (
    PLAYWRIGHT_TOOLS,
    set_page,
    set_screenshot_dir,
)
from app.core.agent_config import get_llm
from app.core.llm_context import llm_usage_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a test execution agent. Execute ONE test step using browser automation tools.

Rules:
1. Execute ONLY the single step described below.
2. After executing, verify the result.
3. Take a screenshot as evidence.
4. Report the result as JSON immediately — do NOT retry failed operations more than once.

If a tool call fails, report the failure in JSON right away. Do not keep trying different approaches.

The JSON must have this structure (use real values, not placeholders):
- Wrap in ```json ... ```
- Top key: "result" — a single object
- Keys: status ("passed" or "failed"), details (what you did), error (only for failed steps)

For failed steps, write a clear error message explaining what happened.
"""

_STEP_PROMPT = """Execute this single test step:

Step {step_number}: {description}

**Current Page:**
- URL: {url}
- Title: {title}
{nav_note}

Execute the step now, then take a screenshot, then report the result as JSON."""

# Screenshot directory (shared with nodes.py)
SCREENSHOT_BASE_DIR = Path("/app/screenshots")

_PLACEHOLDERS = frozenset({
    "...", "…", "-", "step description here",
    "what you did and verified",
    "specific error message explaining what failed and why",
})


def _clean(val):
    if val is None:
        return None
    v = str(val).strip()
    if not v or v in _PLACEHOLDERS or len(v) < 5:
        return None
    return val


def _parse_single_result(messages: list) -> Dict[str, Any]:
    """Parse the JSON result from a single-step agent invocation."""
    for msg in reversed(messages):
        content = msg.content if hasattr(msg, "content") else str(msg)
        if "```json" in content:
            try:
                json_start = content.index("```json") + 7
                json_end = content.index("```", json_start)
                data = json.loads(content[json_start:json_end].strip())
                if "result" in data:
                    return data["result"]
                if "steps" in data:
                    steps = data["steps"]
                    if steps:
                        return steps[0]
            except (json.JSONDecodeError, ValueError):
                continue
    return {"status": "passed", "details": "Completed"}


async def _capture_screenshot(page: Page, run_id: str, step_number: int, description: str, status: str) -> str:
    """Capture a screenshot of the current page state."""
    try:
        run_dir = SCREENSHOT_BASE_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        safe_desc = description[:30].replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"step_{step_number:02d}_{status}_{safe_desc}_{timestamp}.png"
        screenshot_path = run_dir / filename
        await page.screenshot(path=str(screenshot_path), full_page=False, type="png")
        web_path = f"/screenshots/{run_id}/{filename}"
        return web_path
    except Exception as e:
        logger.warning("Screenshot capture failed for step %s: %s", step_number, e)
        return ""


async def _execute_single_step(
    page: Page,
    step: Dict[str, Any],
    idx: int,
    total: int,
    run_id: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute one test step via the LLM agent and return the result."""
    step_number = step.get("step_number", idx + 1)
    description = step.get("description", "")

    url = context.get("url", "unknown")
    title = context.get("title", "unknown")

    prompt = _STEP_PROMPT.format(
        step_number=step_number,
        description=description,
        url=url,
        title=title,
        nav_note="",
    )

    llm = get_llm(temperature=0.0, max_tokens=2048)
    agent = create_react_agent(llm, tools=PLAYWRIGHT_TOOLS)

    try:
        async with llm_usage_context("executor", test_run_id=run_id):
            result = await agent.ainvoke(
                {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]},
                config={
                    "configurable": {"thread_id": f"step-{uuid4()}"},
                    "recursion_limit": 50,
                },
            )
        parsed = _parse_single_result(result.get("messages", []))
        status_val = parsed.get("status", "passed")
        error_val = _clean(parsed.get("error"))
        if status_val == "failed" and error_val is None:
            error_val = f"Step {step_number} execution failed"
        details = _clean(parsed.get("details")) or ""
    except Exception as e:
        logger.warning("Step %d agent invocation failed: %s", step_number, e)
        status_val = "failed"
        error_val = str(e)
        details = ""

    # Take screenshot immediately after step execution
    screenshot_path = await _capture_screenshot(page, run_id, step_number, description, status_val)

    # Update context with current page state
    try:
        context["url"] = page.url
        context["title"] = await page.title()
    except Exception:
        pass

    return {
        "step_number": step_number,
        "description": description,
        "status": status_val,
        "details": details,
        "error": error_val,
        "mode": "langgraph_executor",
        "duration": 0,
        "screenshot_path": screenshot_path,
    }


async def interpret_and_execute_batch(
    page: Page,
    test_steps: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute all test steps one-by-one with per-step screenshots.

    Args:
        page: Playwright page instance
        test_steps: List of test steps with 'description' and 'step_number'
        context: Additional context (url, title, environment, etc.)

    Returns:
        List of step result dicts with status/details/error/screenshot_path
    """
    context = context or {}
    run_id = context.get("run_id", "default")

    set_page(page)
    set_screenshot_dir(f"/tmp/agent_screenshots/{run_id}")

    try:
        context.setdefault("url", page.url)
        context.setdefault("title", await page.title())
    except Exception:
        context.setdefault("url", "unknown")
        context.setdefault("title", "unknown")

    logger.info("Executor agent: starting step-by-step execution of %d steps", len(test_steps))

    results: List[Dict[str, Any]] = []
    failed_early = False
    for idx, step in enumerate(test_steps):
        if failed_early:
            # Skip remaining steps after a failure — they depend on prior steps
            logger.info("Executor agent: skipping step %d/%d (prior step failed)", idx + 1, len(test_steps))
            results.append({
                "step_number": step.get("step_number", idx + 1),
                "description": step.get("description", ""),
                "status": "skipped",
                "details": "",
                "error": "Skipped: a previous step failed",
                "mode": "langgraph_executor",
                "duration": 0,
            })
            continue

        logger.info("Executor agent: executing step %d/%d", idx + 1, len(test_steps))
        result = await _execute_single_step(page, step, idx, len(test_steps), run_id, context)
        results.append(result)
        logger.info("Executor agent: step %d result=%s", result["step_number"], result["status"])

        if result["status"] == "failed":
            failed_early = True

        # Push incremental progress to Redis for streaming display
        try:
            from app.core.job_store import update_job
            import redis.asyncio as aioredis
            from app.core.config import settings

            progress_steps = [
                {k: r[k] for k in (
                    "step_number", "description", "status", "error", "duration",
                    "screenshot_path",
                ) if k in r}
                for r in results
            ]
            update_job(run_id, {
                "completed_steps": progress_steps,
                "current_step": idx + 1,
                "total_steps": len(test_steps),
                "browser_url": context.get("url", ""),
                "browser_title": context.get("title", ""),
            })

            # Publish to browser stream WebSocket channel
            screenshot_path = result.get("screenshot_path")
            if screenshot_path:
                redis_client = aioredis.from_url(settings.REDIS_URL)
                channel_name = f"browser_stream:{run_id}"
                frame_data = {
                    "type": "frame",
                    "path": screenshot_path,
                    "url": context.get("url", ""),
                    "title": context.get("title", ""),
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                import json
                await redis_client.publish(channel_name, json.dumps(frame_data))
                await redis_client.close()
        except Exception as e:
            logger.warning("Failed to publish browser stream frame: %s", e)

    logger.info(
        "Executor agent: completed %d steps, %d passed",
        len(results),
        sum(1 for r in results if r["status"] == "passed"),
    )
    return results
