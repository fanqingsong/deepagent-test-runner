"""
Playwright CLI tools for LangGraph agents.

Provides LangChain @tool functions for browser automation via Playwright.
These replace the Claude Agent SDK's Bash/Read/Write tools that were previously
used for Playwright automation.

Each tool operates on a shared Playwright Page instance passed via a thread-local
context, set by the executor agent before invoking the LLM.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Dangerous JS patterns that should be blocked in browser_evaluate
_DANGEROUS_JS_PATTERNS = [
    "document.write",
    "eval(",
    "Function(",
    "new Function",
    "import(",
    "require(",
    "XMLHttpRequest",
]

# Thread-local page reference — set by executor_agent before each invocation
_current_page = None
_screenshot_dir = "/tmp/agent_screenshots"


def set_page(page):
    """Set the current Playwright page for tools to use."""
    global _current_page
    _current_page = page


def set_screenshot_dir(path: str):
    """Set directory for saving screenshots."""
    global _screenshot_dir
    _screenshot_dir = path
    Path(_screenshot_dir).mkdir(parents=True, exist_ok=True)


def _get_page():
    if _current_page is None:
        raise RuntimeError("No Playwright page available. Call set_page() first.")
    return _current_page


@tool
async def browser_navigate(url: str) -> str:
    """Navigate the browser to a URL. Returns the final URL after navigation."""
    page = _get_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        if "Timeout" in str(e):
            try:
                response = await page.goto(url, wait_until="load", timeout=15000)
            except Exception:
                try:
                    response = await page.goto(url, wait_until="commit", timeout=10000)
                except Exception as e2:
                    return json.dumps({"error": f"Navigation failed: {str(e2)}", "url": page.url})
        else:
            return json.dumps({"error": f"Navigation failed: {str(e)}", "url": page.url})
    final_url = page.url
    status = response.status if response else "unknown"
    return json.dumps({"url": final_url, "status": status})


@tool
async def browser_click(selector: str) -> str:
    """Click on an element identified by CSS selector."""
    page = _get_page()
    try:
        await page.click(selector, timeout=15000)
        return f"Clicked element: {selector}"
    except Exception as e:
        return f"Click failed on '{selector}': {str(e)}"


@tool
async def browser_fill(selector: str, value: str) -> str:
    """Fill a form field identified by CSS selector with a value."""
    page = _get_page()
    try:
        await page.fill(selector, value, timeout=15000)
        return f"Filled {selector} with value: {value[:50]}"
    except Exception as e:
        return f"Fill failed on '{selector}': {str(e)}"


@tool
async def browser_screenshot(name: str) -> str:
    """Take a screenshot and save it. Returns the file path."""
    page = _get_page()
    Path(_screenshot_dir).mkdir(parents=True, exist_ok=True)
    filepath = str(Path(_screenshot_dir) / f"{name}.png")
    await page.screenshot(path=filepath)
    return filepath


@tool
async def browser_get_text(selector: str) -> str:
    """Get the text content of an element identified by CSS selector."""
    page = _get_page()
    try:
        text = await page.text_content(selector, timeout=15000)
        return text or ""
    except Exception as e:
        return f"Get text failed on '{selector}': {str(e)}"


@tool
async def browser_get_page_content() -> str:
    """Get the full HTML content of the current page."""
    page = _get_page()
    content = await page.content()
    return content[:5000]


@tool
async def browser_wait_for(selector: str, timeout: int = 10000) -> str:
    """Wait for an element to appear on the page. Timeout in milliseconds."""
    page = _get_page()
    try:
        await page.wait_for_selector(selector, timeout=timeout or 10000)
        return f"Element appeared: {selector}"
    except Exception as e:
        return f"Wait for '{selector}' failed: {str(e)}"


@tool
async def browser_press_key(key: str) -> str:
    """Press a keyboard key (e.g., 'Enter', 'Tab', 'Escape')."""
    page = _get_page()
    await page.keyboard.press(key)
    return f"Pressed key: {key}"


@tool
async def browser_select_option(selector: str, value: str) -> str:
    """Select an option in a <select> dropdown by value."""
    page = _get_page()
    try:
        await page.select_option(selector, value, timeout=15000)
        return f"Selected {value} in {selector}"
    except Exception as e:
        return f"Select failed on '{selector}': {str(e)}"


@tool
async def browser_evaluate(expression: str) -> str:
    """Execute a JavaScript expression in the browser and return the result.

    Prefer using browser_get_text, browser_click, browser_fill for common
    operations instead of writing raw JavaScript.
    """
    expr_lower = expression.lower()
    for pattern in _DANGEROUS_JS_PATTERNS:
        if pattern.lower() in expr_lower:
            logger.warning("Blocked JS expression containing dangerous pattern: %s", pattern)
            return json.dumps({"error": f"Expression contains blocked pattern: {pattern}"})
    page = _get_page()
    try:
        result = await page.evaluate(expression)
        return json.dumps(result) if not isinstance(result, str) else result
    except Exception as e:
        return json.dumps({"error": f"JS execution failed: {str(e)}. Try using browser_get_text or browser_click instead."})


@tool
async def execute_playwright_script(script: str) -> str:
    """Execute a Node.js Playwright script and return stdout.

    The script receives 'chromium' from playwright. Example:
      const browser = await chromium.launch({headless:true});
      const page = await browser.newPage();
      await page.goto('https://example.com');
      console.log(await page.title());
      await browser.close();
    """
    script_lower = script.lower()
    for pattern in _DANGEROUS_JS_PATTERNS:
        if pattern.lower() in script_lower:
            logger.warning("Blocked Playwright script containing dangerous pattern: %s", pattern)
            return json.dumps({"error": f"Script contains blocked pattern: {pattern}"})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(f"const {{ chromium }} = require('playwright');\n(async () => {{\n{script}\n}})();")
        script_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode()
        error = stderr.decode()
        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {error}"
        return output or "Script executed successfully"
    except asyncio.TimeoutError:
        return "Error: Script execution timed out (60s)"
    finally:
        Path(script_path).unlink(missing_ok=True)


# Collect all tools for easy import
PLAYWRIGHT_TOOLS = [
    browser_navigate,
    browser_click,
    browser_fill,
    browser_screenshot,
    browser_get_text,
    browser_get_page_content,
    browser_wait_for,
    browser_press_key,
    browser_select_option,
    browser_evaluate,
    execute_playwright_script,
]
