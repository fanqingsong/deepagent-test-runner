"""
Deep Research Tools — Full-content web search for deep research agents.

Uses Tavily for URL discovery, then fetches full webpage content
converted to markdown for in-depth analysis by researcher agents.
"""

import asyncio
import logging
from typing import Annotated, Literal
from urllib.parse import urlparse

import httpx
from langchain.tools import InjectedToolArg, tool
from markdownify import markdownify

from app.core.config import settings

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"
ALLOWED_SCHEMES = {"http", "https"}


def _get_tavily_api_key() -> str | None:
    """Get Tavily API key from settings."""
    if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip():
        return settings.TAVILY_API_KEY.strip()
    return None


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to fetch (SSRF protection)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"):
            return False
        return True
    except Exception:
        return False


async def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch webpage and convert HTML to markdown."""
    if not _is_safe_url(url):
        return f"Error: Unsafe URL blocked: {url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            text = markdownify(response.text)
            if len(text) > 8000:
                text = text[:8000] + "\n\n[Content truncated]"
            return text
    except Exception as e:
        return f"Error fetching {url}: {e!s}"


@tool(parse_docstring=True)
async def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 2,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns
    full webpage content as markdown for analysis.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default 2)
        topic: Topic filter - 'general', 'news', or 'finance' (default 'general')

    Returns:
        Formatted search results with full webpage content
    """
    api_key = _get_tavily_api_key()
    if not api_key:
        return "Search unavailable: TAVILY_API_KEY not configured."

    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    if max_results < 1:
        max_results = 1
    elif max_results > 10:
        max_results = 10

    logger.info(f"Executing deep research search: query='{query}', max_results={max_results}, topic='{topic}'")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TAVILY_API_URL,
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "topic": topic,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return f"Search error: {e!s}"

    results = data.get("results", [])
    if not results:
        return f"No results found for '{query}'."

    logger.info(f"Deep research search completed: found {len(results)} results for '{query}'")

    async def _safe_fetch(url: str) -> str:
        if not url:
            return "No URL available."
        return await fetch_webpage_content(url)

    contents = await asyncio.gather(*[_safe_fetch(r.get("url", "")) for r in results])

    result_texts = []
    for result, content in zip(results, contents):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n---")

    return f"Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )
