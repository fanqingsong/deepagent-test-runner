"""
Deep Research Tools — Full-content web search for deep research agents.

Uses Tavily for URL discovery, then fetches full webpage content
converted to markdown for in-depth analysis by researcher agents.
"""

import logging
from typing import Annotated, Literal

import httpx
from langchain.tools import InjectedToolArg, tool
from markdownify import markdownify

from app.core.config import settings

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


def _get_tavily_api_key() -> str | None:
    """Get Tavily API key from settings."""
    if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip():
        return settings.TAVILY_API_KEY.strip()
    return None


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch webpage and convert HTML to markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
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

    result_texts = []
    for result in results:
        url = result.get("url", "")
        title = result.get("title", "Untitled")
        content = fetch_webpage_content(url) if url else "No URL available."
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n---")

    return f"Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )
