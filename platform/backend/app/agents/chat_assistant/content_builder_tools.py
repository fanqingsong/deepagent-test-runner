"""
Content Builder Tools — Research and content writing tools.

Provides web research via Tavily and LLM-powered content generation
for blog posts and social media.
"""

import logging
from typing import Literal

from langchain_core.tools import tool

from app.core.agent_config import get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)


def _check_tavily_available() -> tuple[bool, str]:
    """Check if Tavily API key is configured."""
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY.strip() == "":
        return False, "Tavily API key is not configured. Please add TAVILY_API_KEY to your environment."
    return True, ""


@tool
async def research_topic(query: str, max_results: int = 5) -> str:
    """Research a topic using web search. Returns structured research notes with sources.

    Use this FIRST before writing any content. Make 2-3 targeted searches
    to gather comprehensive information.

    Args:
        query: The research query (be specific and detailed)
        max_results: Number of search results (default 5, max 10)

    Returns:
        Formatted research notes with key findings and source URLs
    """
    try:
        from langchain_tavily import TavilySearchResults
    except ImportError:
        from langchain_community.tools.tavily_search import TavilySearchResults

    available, error_msg = _check_tavily_available()
    if not available:
        return f"Research unavailable: {error_msg}"

    if not query or not query.strip():
        return "Error: Research query cannot be empty."

    max_results = max(1, min(10, max_results))

    try:
        search = TavilySearchResults(
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )
        logger.info(f"Researching topic: query='{query}', max_results={max_results}")
        results = await search.ainvoke({"query": query})

        if not results:
            return f"No research results found for '{query}'."

        if isinstance(results, str):
            return f"## Research: {query}\n\n{results}"

        if isinstance(results, list):
            notes = [f"## Research Notes: {query}\n"]
            notes.append("### Key Findings\n")

            for i, result in enumerate(results, 1):
                if isinstance(result, dict):
                    title = result.get("title", "Untitled")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    notes.append(f"\n**{i}. {title}**\n")
                    if content:
                        notes.append(f"{content[:500]}\n")
                    if url:
                        notes.append(f"Source: {url}\n")
                elif isinstance(result, str):
                    notes.append(f"\n{i}. {result}\n")

            return "\n".join(notes)

        return str(results)

    except Exception as e:
        logger.error(f"Research error: {e}")
        return f"Research failed: {e}"


@tool
async def write_blog_post(
    topic: str,
    research_notes: str,
    tone: str = "professional",
    target_audience: str = "developers",
) -> str:
    """Write a structured blog post based on research notes.

    Args:
        topic: The blog post topic/title
        research_notes: Research findings to base the post on (from research_topic tool)
        tone: Writing tone — professional, casual, technical, or conversational
        target_audience: Who the post is for — developers, executives, general, etc.

    Returns:
        Complete blog post in markdown format
    """
    llm = get_llm(temperature=0.7, max_tokens=4096)

    prompt = f"""Write a well-structured blog post in markdown about: {topic}

**Target audience:** {target_audience}
**Tone:** {tone}

**Research notes to incorporate:**
{research_notes}

**Structure requirements:**
1. Compelling title (H1)
2. Hook — open with a question, statistic, or bold statement (2-3 sentences)
3. Context — explain why this topic matters now
4. Main content — 3-5 sections with H2 headers, each covering one key insight
5. Practical application — actionable takeaways
6. Conclusion — summarize 3 key points, end with a call-to-action

**Writing guidelines:**
- Use active voice
- One idea per paragraph
- Concrete examples and numbers over abstractions
- Keep sentences under 25 words when possible
- Include bullet points for lists of 3+ items
- Write in the same language as the research notes or topic

Output ONLY the blog post markdown, no extra commentary."""

    from langchain_core.messages import HumanMessage
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    return result.content


@tool
async def write_social_post(
    topic: str,
    research_notes: str,
    platform: Literal["linkedin", "twitter"] = "linkedin",
    tone: str = "professional",
) -> str:
    """Write a social media post based on research notes.

    Args:
        topic: The post topic
        research_notes: Research findings to base the post on (from research_topic tool)
        platform: Target platform — "linkedin" or "twitter"
        tone: Writing tone — professional, casual, or thought-provoking

    Returns:
        Formatted social media post with hashtags
    """
    llm = get_llm(temperature=0.7, max_tokens=2048)

    if platform == "linkedin":
        format_guide = """**LinkedIn format:**
- 1300 character limit
- First line is the hook (must grab attention)
- Use line breaks for readability
- 2-3 short paragraphs for main insight
- End with a question or call-to-action
- 3-5 relevant hashtags at the end"""
    else:
        format_guide = """**Twitter/X format:**
- 280 character limit per tweet
- Thread format if longer: start with "1/🧵 [hook]"
- Each tweet: one idea
- Max 2 hashtags per tweet
- End thread with conclusion + CTA"""

    prompt = f"""Write a {platform} post about: {topic}

**Tone:** {tone}

**Research to incorporate:**
{research_notes}

{format_guide}

**Writing guidelines:**
- Lead with the most compelling insight
- Use "I" and share perspectives where appropriate
- Be concise and scannable
- Include a clear hook in the first line
- Write in the same language as the research notes or topic

Output ONLY the social media post, no extra commentary."""

    from langchain_core.messages import HumanMessage
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    return result.content
