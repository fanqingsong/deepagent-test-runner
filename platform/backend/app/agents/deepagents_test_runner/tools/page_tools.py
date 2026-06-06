"""
Page tools for Test Runner agent.

Tool for fetching page DOM context for script generation.
"""

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def fetch_page_context_tool(url: str) -> str:
    """Navigate to URL and extract page DOM structure for script generation.

    Launches a headless browser, navigates to the URL, and returns
    structured page context including forms, inputs, buttons, and links.

    Args:
        url: The target URL to analyze.
    """
    from playwright.async_api import async_playwright
    from ..lib.page_fetcher import fetch_page_context

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                result = await fetch_page_context(page, url)
                return json.dumps(result)
            finally:
                await browser.close()
    except Exception as e:
        logger.error("fetch_page_context_tool failed: %s", e)
        return json.dumps({"title": "", "url": url, "error": str(e), "context_text": ""})
