"""
Deep Agents Test Runner — Script generation and execution.

- **Script Generation**: Playwright script generation and execution
- **Page Fetcher**: DOM extraction for LLM context
"""

from .runners import run_script_generation, generate_playwright_script
from .lib import execute_script, fetch_page_context

__all__ = [
    "run_script_generation",
    "generate_playwright_script",
    "execute_script",
    "fetch_page_context",
]
