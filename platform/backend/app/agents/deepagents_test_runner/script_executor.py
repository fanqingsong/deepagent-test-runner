"""
Script Executor — run generated Python Playwright scripts in a sandboxed environment.

Executes the `async def run_test(page: Page) -> dict` function from a generated
script string, passing in a live Playwright page and capturing results.
"""

import asyncio
import logging
from typing import Any, Dict

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERNS = [
    "import os", "import subprocess", "import sys", "import shutil",
    "import socket", "import http", "exec(", "eval(",
    "compile(", "os.system", "os.popen", "subprocess.", "os.remove", "os.unlink",
]

_SAFE_BUILTINS = {
    "__import__": __import__,
    "print": print, "len": len, "str": str, "int": int, "float": float,
    "bool": bool, "list": list, "dict": dict, "tuple": tuple, "set": set,
    "range": range, "enumerate": enumerate, "zip": zip, "map": map,
    "filter": filter, "isinstance": isinstance, "type": type,
    "None": None, "True": True, "False": False,
    "abs": abs, "min": min, "max": max, "sum": sum,
    "sorted": sorted, "reversed": reversed, "any": any, "all": all,
    "hasattr": hasattr, "getattr": getattr,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "RuntimeError": RuntimeError,
    "Exception": Exception, "AssertionError": AssertionError,
}


def _check_safety(script: str) -> str | None:
    """Check script for dangerous patterns."""
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in script:
            return f"Script contains blocked pattern: {pattern}"

    # Check for unsafe __import__ usage
    if "__import__" in script:
        # Allow __import__ for module imports (from playwright.async_api import ...)
        # Block direct dangerous __import__ calls
        unsafe_imports = ["__import__('os')", "__import__('subprocess')", "__import__('sys')",
                         '__import__("os")', '__import__("subprocess")', '__import__("sys")']
        for unsafe in unsafe_imports:
            if unsafe in script:
                return f"Script contains unsafe import: {unsafe}"

    return None


async def execute_script(
    script: str,
    page: Page,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Execute a generated Playwright script in a sandboxed namespace.

    Args:
        script: Python source with `async def run_test(page: Page) -> dict`.
        page: Active Playwright page instance.
        timeout: Max execution time in seconds.

    Returns:
        Dict with: status, step_results, error
    """
    safety_error = _check_safety(script)
    if safety_error:
        return {"status": "error", "step_results": [], "error": safety_error}

    namespace: Dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}

    try:
        exec(script, namespace)
    except Exception as e:
        return {"status": "error", "step_results": [], "error": f"Script compilation failed: {e}"}

    run_test_fn = namespace.get("run_test")
    if not run_test_fn or not callable(run_test_fn):
        return {"status": "error", "step_results": [], "error": "Script missing 'async def run_test(page)'"}

    try:
        result = await asyncio.wait_for(run_test_fn(page), timeout=timeout)
    except asyncio.TimeoutError:
        return {"status": "error", "step_results": [], "error": f"Script timed out ({timeout}s)"}
    except Exception as e:
        return {"status": "failed", "step_results": [], "error": f"Script execution error: {e}"}

    if not isinstance(result, dict):
        return {"status": "error", "step_results": [], "error": f"Script returned {type(result).__name__}, expected dict"}

    return {
        "status": result.get("status", "passed"),
        "step_results": result.get("step_results", []),
        "error": result.get("error"),
    }
