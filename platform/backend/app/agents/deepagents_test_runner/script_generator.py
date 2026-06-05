"""
Script Generator — generate Python Playwright scripts from test goal + page context.

Uses LLM to produce executable Playwright test scripts. Supports iterative
fixing by feeding back execution errors.
"""

import logging
import re
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agent_config import get_llm
from app.core.llm_context import llm_usage_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a Playwright test script generator. Generate a Python async function that uses Playwright to test a web page.

Rules:
1. Output ONLY the Python code inside ```python ... ``` block. No explanations outside.
2. The function signature must be: async def run_test(page: Page) -> dict
3. Use Playwright async API (await page.goto, await page.click, etc.)
4. Use CSS selectors to find elements (prefer id selectors like #login-btn)
5. Use playwright.expect for assertions: from playwright.async_api import expect
6. Return a result dict with: {"status": "passed"} or {"status": "failed", "error": "..."}
7. Add try/except around each step to capture failures with meaningful error messages
8. Use page.wait_for_selector(selector, state="visible", timeout=15000) before interacting with elements (15s timeout)
9. Add page.wait_for_load_state('networkidle') after navigation if needed
10. Do NOT import os, subprocess, or any file system modules
11. Do NOT use page.evaluate for anything other than reading data
12. IMPORTANT: Always use timeout=15000 (15 seconds) for all wait_for_selector calls to handle slow networks
"""

_GENERATE_PROMPT = """Generate a Playwright test script for this test case:

**Test Goal:** {goal}
**Target URL:** {url}

**Page Structure (extracted DOM elements):**
{page_context}

Generate the complete `async def run_test(page: Page) -> dict` function now."""

_FIX_PROMPT = """The previously generated Playwright script failed. Fix it.

**Test Goal:** {goal}
**Target URL:** {url}

**Previous Script:**
```python
{previous_script}
```

**Execution Error:**
{error}

Generate the fixed `async def run_test(page: Page) -> dict` function now."""


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


def _validate_script(script: str) -> bool:
    """Basic validation of generated script."""
    if not script:
        return False
    if "async def run_test" not in script:
        return False
    # Block dangerous imports - but allow __import__ for Playwright's internal use
    dangerous = ["import os", "import subprocess", "import sys"]
    for pattern in dangerous:
        if pattern in script:
            return False
    # Allow __import__ only in safe contexts (playwright internal)
    if "__import__" in script:
        # Check if it's being used unsafely
        unsafe_usage = ['__import__(\'os\')', '__import__(\'subprocess\')', '__import__(\'sys\')']
        for unsafe in unsafe_usage:
            if unsafe in script:
                return False
    return True


async def generate_playwright_script(
    goal: str,
    url: str,
    page_context: str,
    previous_error: Optional[str] = None,
    previous_script: Optional[str] = None,
    run_id: str = "script-gen",
) -> Dict[str, Any]:
    """Generate or fix a Playwright test script via LLM.

    Returns dict with "script" (str) and "error" (Optional[str]).
    """
    if previous_error and previous_script:
        prompt = _FIX_PROMPT.format(
            goal=goal, url=url,
            previous_script=previous_script,
            error=previous_error,
        )
    else:
        prompt = _GENERATE_PROMPT.format(
            goal=goal, url=url,
            page_context=page_context,
        )

    llm = get_llm(temperature=0.0, max_tokens=4096)

    try:
        async with llm_usage_context("script_generator", test_run_id=run_id):
            response = await llm.ainvoke(
                [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)]
            )
    except Exception as e:
        logger.error("Script generation LLM call failed: %s", e)
        return {"script": None, "error": str(e)}

    content = response.content if hasattr(response, "content") else str(response)
    script = _extract_script(content)

    if not script:
        return {"script": None, "error": "Failed to extract script from LLM output"}
    if not _validate_script(script):
        return {"script": None, "error": "Generated script failed validation"}

    logger.info("Script generator: produced script (%d chars)", len(script))
    return {"script": script, "error": None}
