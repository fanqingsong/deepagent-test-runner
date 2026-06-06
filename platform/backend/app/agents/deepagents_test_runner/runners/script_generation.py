"""
Script Generation Runners — entry functions bridging API endpoints to the subagent.

- run_script_generation(): full workflow for API endpoint (generate + save to DB)
- generate_playwright_script(): LLM-only generation (used by subagent tools)
"""

import logging
import re
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage

from app.core.llm_context import llm_usage_context

logger = logging.getLogger(__name__)

_GENERATE_PROMPT = """Generate a Playwright test script for this test case:

**Test Goal:** {goal}
**Target URL:** {url}
{description_section}
**Page Structure (extracted DOM elements):**
{page_context}

Generate the complete `async def run_test(page: Page) -> dict` function now.
After generating, use the validate_script tool to verify the script is correct."""


def _extract_script(llm_output: str) -> Optional[str]:
    """Extract Python code from LLM output."""
    match = re.search(r"```python\s*\n(.*?)```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    if "async def run_test" in llm_output:
        start = llm_output.index("async def run_test")
        return llm_output[start:].strip()
    return None


def _extract_last_message(result: Dict[str, Any]) -> str:
    """Extract text from the last AIMessage in an agent response."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return str(messages[-1]) if messages else ""


async def generate_playwright_script(
    goal: str,
    url: str,
    page_context: str,
    description: Optional[str] = None,
    run_id: str = "script-gen",
) -> Dict[str, Any]:
    """Generate a Playwright test script via the Test Runner DeepAgent.

    Returns dict with "script" (str) and "error" (Optional[str]).
    """
    from ..subagents import get_script_generator_subagent
    from app.core.agent_config import get_llm

    description_section = f"\n**Description:** {description}\n" if description else ""

    prompt = _GENERATE_PROMPT.format(
        goal=goal, url=url,
        description_section=description_section,
        page_context=page_context,
    )

    try:
        llm = get_llm(temperature=0.3, max_tokens=4096)
        subagent = get_script_generator_subagent(llm)

        async with llm_usage_context("script_generator", test_run_id=run_id):
            result = await subagent.runnable.ainvoke(
                {"messages": [HumanMessage(content=prompt)]},
            )
    except Exception as e:
        logger.error("Script generation agent call failed: %s", e)
        return {"script": None, "error": str(e)}

    final_text = _extract_last_message(result)
    script = _extract_script(final_text)

    if not script:
        return {"script": None, "error": "Failed to extract script from agent output"}

    logger.info("Script generator: produced script (%d chars)", len(script))
    return {"script": script, "error": None}


async def run_script_generation(
    test_definition_id: int,
    url: str,
    goal: str,
    description: str = None,
) -> Dict[str, Any]:
    """Run the full script generation workflow via script-generator subagent."""
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

    try:
        async with llm_usage_context("script_generator", test_run_id=f"gen_{test_definition_id}"):
            await subagent.runnable.ainvoke(
                {"messages": [HumanMessage(content=prompt)]},
            )
    except Exception as e:
        logger.error("run_script_generation subagent call failed: %s", e)

    # Read back the result saved by the subagent via save_generated_script tool
    from app.core.worker_db import run_with_session
    from app.models.test_definition import TestDefinition
    from sqlalchemy import select as sa_select

    async def _read(db):
        r = await db.execute(
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

    return await run_with_session(_read)
