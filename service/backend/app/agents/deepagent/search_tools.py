"""
Search Tools — Web search functionality using Tavily.

Provides tools for searching the web with graceful error handling
and result summarization.
"""

import logging
from typing import Optional

from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)


def _check_tavily_available() -> tuple[bool, str]:
    """Check if Tavily API key is configured.

    Returns:
        Tuple of (is_available, error_message)
    """
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY.strip() == "":
        return False, "Tavily API key is not configured. Please add TAVILY_API_KEY to your environment."
    return True, ""


@tool
async def web_search(
    query: str,
    max_results: int = 5,
) -> str:
    """Search the web for current information using Tavily.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default 5, max 10)

    Returns:
        Formatted search results with source links and summaries
    """
    try:
        from langchain_tavily import TavilySearchResults
    except ImportError:
        # Fallback to langchain_community
        from langchain_community.tools.tavily_search import TavilySearchResults

    # Validate max_results
    if max_results < 1:
        max_results = 1
    elif max_results > 10:
        max_results = 10

    # Check if Tavily is available
    available, error_msg = _check_tavily_available()
    if not available:
        return f"Search is currently unavailable: {error_msg}"

    # Validate query
    if not query or query.strip() == "":
        return "Error: Search query cannot be empty."

    try:
        # Initialize Tavily search
        search = TavilySearchResults(
            max_results=max_results,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )

        # Execute search
        logger.info(f"Executing Tavily search: query='{query}', max_results={max_results}")
        results = await search.ainvoke({"query": query})

        if not results:
            return f"No results found for '{query}'."

        # Handle string result
        if isinstance(results, str):
            return f"**Search results for '{query}'**\n\n{results}"

        # Handle list result
        if isinstance(results, list):
            if not results:
                return f"No results found for '{query}'."

            formatted_results = [f"**Search results for '{query}'**\n"]

            for i, result in enumerate(results, 1):
                # Handle dict items
                if isinstance(result, dict):
                    title = result.get("title", "Untitled")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    score = result.get("score", 0)

                    formatted_results.append(f"\n{i}. **{title}**")
                    if url:
                        formatted_results.append(f"   URL: {url}")
                    if content:
                        # Truncate content if too long
                        content_preview = content[:300] + "..." if len(content) > 300 else content
                        formatted_results.append(f"   {content_preview}")
                    if score:
                        formatted_results.append(f"   Relevance: {score:.2f}")
                # Handle string items
                elif isinstance(result, str):
                    formatted_results.append(f"\n{i}. {result}")

            return "\n".join(formatted_results)

        # Fallback for other types
        return f"**Search results for '{query}'**\n\n{str(results)}"

    except Exception as e:
        logger.error(f"Error executing Tavily search: {e}")
        return f"Error executing search: {str(e)}. Please try again later."


@tool
async def search_with_summary(
    query: str,
    max_results: int = 5,
) -> str:
    """Search the web and provide a summarized answer using Tavily.

    This tool uses Tavily's built-in answer generation to provide
    a direct answer to your question along with source references.

    Args:
        query: The search query or question
        max_results: Maximum number of results to use for summary (default 5, max 10)

    Returns:
        A summarized answer with source links
    """
    try:
        from langchain_tavily import TavilyAnswer
    except ImportError:
        # Fallback to langchain_community
        from langchain_community.tools.tavily_search import TavilyAnswer

    # Validate max_results
    if max_results < 1:
        max_results = 1
    elif max_results > 10:
        max_results = 10

    # Check if Tavily is available
    available, error_msg = _check_tavily_available()
    if not available:
        return f"Search is currently unavailable: {error_msg}"

    # Validate query
    if not query or query.strip() == "":
        return "Error: Search query cannot be empty."

    try:
        # Initialize Tavily answer
        search = TavilyAnswer(
            max_results=max_results,
            search_depth="basic",
        )

        # Execute search with answer generation
        logger.info(f"Executing Tavily search with summary: query='{query}', max_results={max_results}")
        result = await search.ainvoke({"query": query})

        if not result:
            return f"No results found for '{query}'."

        # Handle string result (TavilyAnswer may return a string)
        if isinstance(result, str):
            return f"**Answer for '{query}'**\n\n{result}"

        # Handle list result
        if isinstance(result, list):
            if not result:
                return f"No results found for '{query}'."

            # Join list items
            return f"**Answer for '{query}'**\n\n" + "\n".join(str(item) for item in result)

        # Handle dict result
        if isinstance(result, dict):
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            formatted = [f"**Answer for '{query}'**\n"]
            if answer:
                formatted.append(f"{answer}\n")

            if sources and isinstance(sources, list):
                formatted.append("\n**Sources:**")
                for i, source in enumerate(sources, 1):
                    if isinstance(source, dict):
                        title = source.get("title", "Untitled")
                        url = source.get("url", "")
                        formatted.append(f"{i}. {title}")
                        if url:
                            formatted.append(f"   {url}")
                    else:
                        formatted.append(f"{i}. {source}")

            return "\n".join(formatted)

        # Fallback for other types
        return f"**Answer for '{query}'**\n\n{str(result)}"

    except Exception as e:
        logger.error(f"Error executing Tavily search with summary: {e}")
        return f"Error executing search: {str(e)}. Please try again later."
