"""
Knowledge Base Tools — Multi-source query routing and synthesis.

Integrates three knowledge sources:
- RAG (Vector Store): Document retrieval from indexed knowledge base
- Web (Tavily): Real-time web search for current information
- DB (SQL): Direct database queries for structured data

Provides a unified query_knowledge_base tool that classifies queries,
routes to appropriate sources, and synthesizes results with attribution.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.agent_config import get_llm
from app.core.config import settings
from app.core.database import sync_session_maker

logger = logging.getLogger(__name__)

# Thread pool for running sync database calls
_db_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="db_query")


# =============================================================================
# Part 1: Classification Schema
# =============================================================================

class SourceClassification(BaseModel):
    """Classification for a single sub-query to a specific source."""

    source: Literal["rag", "web", "db"] = Field(
        description="The knowledge source to query: 'rag' for documents, 'web' for search, 'db' for database"
    )
    sub_query: str = Field(
        description="A specific sub-query optimized for this source"
    )


class ClassificationResult(BaseModel):
    """Classification result containing all source classifications."""

    classifications: list[SourceClassification] = Field(
        description="List of source classifications for the query"
    )


# =============================================================================
# Part 2: Source Handlers
# =============================================================================

async def _query_rag(sub_query: str) -> tuple[str, str]:
    """Query the RAG vector store for relevant documents.

    Args:
        sub_query: The search query for the vector store

    Returns:
        Tuple of (source_name, result_text)
    """
    try:
        from app.agents.chat_assistant.rag_tools import retrieve_context

        result, docs = retrieve_context.invoke({"query": sub_query, "k": 4})

        if not docs:
            return "rag", "No relevant documents found in the knowledge base."

        return "rag", result

    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        return "rag", f"Error retrieving from knowledge base: {str(e)}"


async def _query_web(sub_query: str) -> tuple[str, str]:
    """Query the web using Tavily search for current information.

    Args:
        sub_query: The search query for web search

    Returns:
        Tuple of (source_name, result_text)
    """
    # Check if Tavily API key is configured
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY.strip() == "":
        return "web", "Web search is not available. TAVILY_API_KEY is not configured."

    try:
        # Try importing from langchain_tavily first
        try:
            from langchain_tavily import TavilySearchResults
        except ImportError:
            # Fallback to langchain_community
            from langchain_community.tools.tavily_search import TavilySearchResults

        # Initialize Tavily search
        search = TavilySearchResults(
            max_results=5,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )

        # Execute search
        results = await search.ainvoke({"query": sub_query})

        if not results:
            return "web", f"No web search results found for '{sub_query}'."

        # Handle list result
        if isinstance(results, list):
            formatted_lines = [f"**Web search results for '{sub_query}'**\n"]

            for i, result in enumerate(results[:5], 1):
                if isinstance(result, dict):
                    title = result.get("title", "Untitled")
                    url = result.get("url", "")
                    content = result.get("content", "")

                    formatted_lines.append(f"\n{i}. **{title}**")
                    if url:
                        formatted_lines.append(f"   URL: {url}")
                    if content:
                        # Truncate long content
                        content_preview = content[:300] + "..." if len(content) > 300 else content
                        formatted_lines.append(f"   {content_preview}")
                elif isinstance(result, str):
                    formatted_lines.append(f"\n{i}. {result}")

            return "web", "\n".join(formatted_lines)

        # Handle string result
        if isinstance(results, str):
            return "web", f"**Web search results for '{sub_query}'**\n\n{results}"

        # Fallback
        return "web", f"**Web search results for '{sub_query}'**\n\n{str(results)}"

    except Exception as e:
        logger.error(f"Error querying web: {e}")
        return "web", f"Error executing web search: {str(e)}"


async def _query_db(sub_query: str) -> tuple[str, str]:
    """Query the database using LLM-generated SQL.

    Args:
        sub_query: Natural language query to convert to SQL

    Returns:
        Tuple of (source_name, result_text)
    """
    try:
        from app.agents.chat_assistant.sql_tools import _ensure_limit, _is_read_only

        # Generate SQL using LLM
        sql_gen_prompt = f"""Convert the following natural language query into a PostgreSQL SQL query.

Query: {sub_query}

Rules:
- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE, DROP, etc.)
- Always include a LIMIT clause (max 100 rows)
- Use proper table and column names based on the database schema
- Use proper PostgreSQL syntax

Available tables include: users, test_definitions, test_runs, test_cases, test_suites, schedules, llm_usage, and others.

Return ONLY the SQL query, no explanation."""

        llm = get_llm(temperature=0.0, max_tokens=512)
        sql_response = llm.invoke(sql_gen_prompt)
        sql_query = sql_response.content.strip()

        # Validate the query is read-only
        is_valid, error_msg = _is_read_only(sql_query)
        if not is_valid:
            return "db", f"Error: Generated SQL is not read-only: {error_msg}"

        # Ensure LIMIT clause
        sql_query = _ensure_limit(sql_query)

        # Execute query in thread pool (sync SQLAlchemy)
        loop = asyncio.get_event_loop()
        result_text = await loop.run_in_executor(
            _db_executor,
            _execute_sync_query,
            sql_query
        )

        return "db", result_text

    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return "db", f"Error executing database query: {str(e)}"


def _execute_sync_query(sql_query: str) -> str:
    """Execute a SQL query synchronously.

    This function runs in a thread pool executor to avoid blocking the async loop.

    Args:
        sql_query: The SQL query to execute

    Returns:
        Formatted result text
    """
    from app.agents.chat_assistant.sql_tools import MAX_RESULT_ROWS

    db = sync_session_maker()
    try:
        result = db.execute(text(sql_query))
        rows = result.fetchall()

        if not rows:
            return "Query returned no results."

        col_names = list(result.keys())
        header = " | ".join(col_names)
        separator = "-+-".join("-" * len(c) for c in col_names)
        row_strs = [" | ".join(str(v) for v in row) for row in rows]

        # Truncate if too many results
        if len(row_strs) > MAX_RESULT_ROWS:
            row_strs = row_strs[:MAX_RESULT_ROWS]
            row_strs.append(f"... ({len(rows)} total rows, showing first {MAX_RESULT_ROWS})")

        return f"{header}\n{separator}\n" + "\n".join(row_strs)

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.rollback()
        db.close()


# =============================================================================
# Part 3: Classifier, Synthesizer, Router Tool
# =============================================================================

_SOURCE_HANDLERS = {
    "rag": _query_rag,
    "web": _query_web,
    "db": _query_db,
}


async def _classify_sources(query: str) -> list[SourceClassification]:
    """Classify which knowledge sources to use for the query.

    Args:
        query: The user's query

    Returns:
        List of source classifications
    """
    classification_prompt = f"""Analyze the following query and determine which knowledge sources should be used to answer it.

Query: {query}

Available sources:
- RAG (rag): Use for questions about internal documents, knowledge base, indexed content, project-specific information, or historical context
- Web (web): Use for questions about current events, recent information, external topics, or anything requiring up-to-date data
- DB (db): Use for questions about database records, test results, user data, metrics, or structured data stored in the system

Rules:
- You can recommend multiple sources if the query could benefit from each
- Each classification should include a specific sub-query optimized for that source
- If unsure, prefer RAG for internal knowledge and Web for external knowledge

Classify the query and return the list of sources to query."""

    try:
        llm = get_llm(temperature=0.0, max_tokens=512)
        classifier = llm.with_structured_output(ClassificationResult)
        result: ClassificationResult = await classifier.ainvoke(classification_prompt)
        return result.classifications

    except Exception as e:
        logger.error(f"Error classifying sources: {e}")
        # Fallback to RAG only
        return [SourceClassification(source="rag", sub_query=query)]


async def _synthesize(query: str, results: list[tuple[str, str]]) -> str:
    """Synthesize results from multiple sources into a coherent answer.

    Args:
        query: The original user query
        results: List of (source_name, result_text) tuples

    Returns:
        Synthesized answer with source attribution
    """
    if not results:
        return "Unable to retrieve information from any knowledge source."

    # Single result - return directly without LLM call
    if len(results) == 1:
        source_name, result_text = results[0]
        return f"[{source_name}]\n\n{result_text}"

    # Multiple results - use LLM to synthesize
    sources_text = "\n\n".join(
        f"## Source: {source_name}\n{content}"
        for source_name, content in results
    )

    synthesis_prompt = f"""Synthesize the following information from multiple sources to answer the user's query.

User Query: {query}

## Source Information

{sources_text}

Instructions:
- Create a coherent answer that integrates information from all relevant sources
- Maintain source attribution - cite which source provided each piece of information
- Resolve any contradictions between sources (prefer RAG for internal info, Web for current info)
- If sources provide complementary information, combine them effectively
- Keep the answer clear and organized
- If a source has no useful information, don't force it into the answer"""

    try:
        llm = get_llm(temperature=0.3, max_tokens=2048)
        response = await llm.ainvoke(synthesis_prompt)

        synthesized = response.content.strip()
        return f"[Synthesized from {len(results)} sources]\n\n{synthesized}"

    except Exception as e:
        logger.error(f"Error synthesizing results: {e}")
        # Fallback: concatenate results
        return "\n\n---\n\n".join(
            f"[{source_name}]\n\n{content}"
            for source_name, content in results
        )


@tool
async def query_knowledge_base(query: str) -> str:
    """Query multiple knowledge sources and synthesize a comprehensive answer.

    This tool automatically classifies your query, routes it to appropriate sources
    (RAG knowledge base, web search, or database), and synthesizes results with
    proper source attribution.

    Args:
        query: Your question or query in natural language

    Returns:
        A comprehensive answer with source attribution

    Examples:
        query_knowledge_base("What are the recent test execution results?")
        query_knowledge_base("How do I configure the test scheduler?")
        query_knowledge_base("What's the current status of all active users?")
    """
    # Validate input
    if not query or query.strip() == "":
        return "Error: Query cannot be empty."

    try:
        # Step 1: Classify sources
        classifications = await _classify_sources(query)

        if not classifications:
            return "Unable to determine appropriate knowledge sources for this query."

        # Step 2: Query each source in parallel
        tasks = []
        for classification in classifications:
            handler = _SOURCE_HANDLERS.get(classification.source)
            if handler:
                tasks.append(handler(classification.sub_query))

        if not tasks:
            return "No valid knowledge sources available for this query."

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error from source {classifications[i].source}: {result}")
                formatted_results.append((
                    classifications[i].source.upper(),
                    f"Error: {str(result)}"
                ))
            else:
                formatted_results.append(result)

        # Step 3: Synthesize results
        answer = await _synthesize(query, formatted_results)

        return answer

    except Exception as e:
        logger.error(f"Error in query_knowledge_base: {e}")
        return f"Error processing query: {str(e)}"
