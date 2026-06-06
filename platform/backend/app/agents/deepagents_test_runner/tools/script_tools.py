"""
Script tools for Test Runner agent.

Tools for validating and executing Playwright scripts.
"""

import json
import logging

from langchain_core.tools import tool

from ..lib.script_executor import check_script_safety

logger = logging.getLogger(__name__)


@tool
def validate_script(script: str) -> str:
    """Validate a Playwright test script for safety and structural correctness.

    Checks for required function signature, dangerous imports, and unsafe patterns.

    Args:
        script: The Python Playwright script source code to validate.

    Returns:
        JSON string with "valid" (bool) and "errors" (list of strings).
    """
    errors: list[str] = []

    if not script:
        return json.dumps({"valid": False, "errors": ["Script is empty"]})

    if "async def run_test" not in script:
        errors.append("Script must contain 'async def run_test(page: Page) -> dict'")

    errors.extend(check_script_safety(script))

    return json.dumps({"valid": len(errors) == 0, "errors": errors})


@tool
async def execute_script_tool(script: str, url: str) -> str:
    """Execute a Playwright script in sandbox against a URL.

    Validates the script for safety, then runs it in a restricted
    sandbox environment against the target page.

    Args:
        script: The Python Playwright script source code.
        url: Target URL to navigate to before execution.
    """
    from playwright.async_api import async_playwright
    from ..lib.script_executor import execute_script

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                result = await execute_script(script, page, timeout=60)
                return json.dumps(result)
            finally:
                await browser.close()
    except Exception as e:
        logger.error("execute_script_tool failed: %s", e)
        return json.dumps({"status": "error", "step_results": [], "error": str(e)})
