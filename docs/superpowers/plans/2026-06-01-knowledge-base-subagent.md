# Knowledge Base Subagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a knowledge-base subagent that classifies queries and dispatches to RAG/Web/DB sources in parallel, replacing the separate rag-knowledge and search subagents.

**Architecture:** A `create_agent` with a single `query_knowledge_base` tool. The tool uses LLM structured output to classify which sources to query, dispatches via `asyncio.gather`, and synthesizes results. Registered as a `CompiledSubAgent` named "knowledge-base".

**Tech Stack:** LangChain (`create_agent`, `@tool`, structured output), `asyncio.gather` for parallel dispatch, `TavilySearchResults` for web, `PGVector` for RAG, SQLAlchemy for DB, Pydantic for classification schema.

---

### Task 1: Create classification schema and helper types

**Files:**
- Create: `backend/app/agents/chat_assistant/knowledge_base_tools.py`

- [ ] **Step 1: Create the file with Pydantic models and source classification types**

```python
"""
Knowledge Base Tools — Router tool for multi-source knowledge queries.

Classifies queries via LLM structured output, dispatches to RAG/Web/DB
sources in parallel, and synthesizes results into a coherent answer.
"""

import asyncio
import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SourceClassification(BaseModel):
    """A single routing decision: which source to query with what sub-question."""
    source: Literal["rag", "web", "db"] = Field(
        description="The knowledge source to query"
    )
    sub_query: str = Field(
        description="A targeted sub-question optimized for this source"
    )


class ClassificationResult(BaseModel):
    """Result of classifying a user query into source-specific sub-questions."""
    classifications: list[SourceClassification] = Field(
        description="List of sources to query with their targeted sub-questions"
    )
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/knowledge_base_tools.py
git commit -m "feat(kb-agent): add classification schema for knowledge base router"
```

---

### Task 2: Implement source handlers (RAG, Web, DB)

**Files:**
- Modify: `backend/app/agents/chat_assistant/knowledge_base_tools.py`

- [ ] **Step 1: Add the three private source handler functions after the Pydantic models**

Append to `knowledge_base_tools.py`:

```python
async def _query_rag(sub_query: str) -> tuple[str, str]:
    """Query the PGVector knowledge base via existing rag_tools."""
    try:
        from app.agents.chat_assistant.rag_tools import retrieve_context

        result_text, _docs = retrieve_context.invoke({"query": sub_query, "k": 4})
        if not result_text or "No relevant documents" in result_text:
            return ("rag", "No relevant documents found in the knowledge base.")
        return ("rag", result_text)
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        return ("rag", f"Error querying knowledge base: {e}")


async def _query_web(sub_query: str) -> tuple[str, str]:
    """Query web search via Tavily."""
    try:
        try:
            from langchain_tavily import TavilySearchResults
        except ImportError:
            from langchain_community.tools.tavily_search import TavilySearchResults

        from app.core.config import settings

        if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY.strip() == "":
            return ("web", "Web search unavailable: TAVILY_API_KEY not configured.")

        search = TavilySearchResults(
            max_results=5,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )
        results = await search.ainvoke({"query": sub_query})

        if not results:
            return ("web", f"No web results found for '{sub_query}'.")

        if isinstance(results, str):
            return ("web", results)

        if isinstance(results, list):
            formatted = []
            for i, r in enumerate(results, 1):
                if isinstance(r, dict):
                    title = r.get("title", "Untitled")
                    url = r.get("url", "")
                    content = r.get("content", "")
                    formatted.append(f"{i}. **{title}**")
                    if url:
                        formatted.append(f"   {url}")
                    if content:
                        formatted.append(f"   {content[:300]}")
                elif isinstance(r, str):
                    formatted.append(f"{i}. {r}")
            return ("web", "\n".join(formatted))

        return ("web", str(results))
    except Exception as e:
        logger.error("Web query failed: %s", e)
        return ("web", f"Error searching the web: {e}")


async def _query_db(sub_query: str) -> tuple[str, str]:
    """Query the database by generating SQL from natural language."""
    try:
        from app.core.agent_config import get_llm
        from app.agents.sql_agent.sql_tools import (
            _is_read_only,
            _ensure_limit,
        )
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(temperature=0.0, max_tokens=1024)

        sql_gen_prompt = [
            SystemMessage(content=(
                "You are a SQL expert for an E2E testing platform PostgreSQL database.\n"
                "Available tables: test_definitions, test_steps, test_runs, test_cases, "
                "schedules, test_suites, llm_usage, users.\n\n"
                "Generate a single SELECT query to answer the question.\n"
                "Rules:\n"
                "- Only SELECT queries (no INSERT/UPDATE/DELETE/DROP)\n"
                "- Always include LIMIT (max 100)\n"
                "- Never use SELECT *\n"
                "- Output ONLY the SQL query, nothing else\n"
            )),
            HumanMessage(content=sub_query),
        ]

        sql_response = await llm.ainvoke(sql_gen_prompt)
        query = sql_response.content.strip()

        ok, msg = _is_read_only(query)
        if not ok:
            return ("db", f"Generated query rejected: {msg}")

        query = _ensure_limit(query)

        from app.core.database import sync_session_maker
        from sqlalchemy import text

        def _exec():
            db = sync_session_maker()
            try:
                db.execute(text("SET LOCAL statement_timeout = '30s';"))
                result = db.execute(text(query))
                rows = result.fetchall()
                if not rows:
                    return "Query returned no results."
                col_names = list(result.keys())
                header = " | ".join(col_names)
                separator = "-+-".join("-" * len(c) for c in col_names)
                row_strs = [" | ".join(str(v) for v in row) for row in rows]
                return f"{header}\n{separator}\n" + "\n".join(row_strs)
            except Exception as e:
                return f"Error: {e}"
            finally:
                db.rollback()
                db.close()

        result_text = await asyncio.to_thread(_exec)
        return ("db", result_text)
    except Exception as e:
        logger.error("DB query failed: %s", e)
        return ("db", f"Error querying database: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/knowledge_base_tools.py
git commit -m "feat(kb-agent): add RAG, Web, and DB source handlers"
```

---

### Task 3: Implement classifier, synthesizer, and main router tool

**Files:**
- Modify: `backend/app/agents/chat_assistant/knowledge_base_tools.py`

- [ ] **Step 1: Add the classify function, synthesize function, and the main `query_knowledge_base` tool**

Append to `knowledge_base_tools.py`:

```python
_SOURCE_HANDLERS = {
    "rag": _query_rag,
    "web": _query_web,
    "db": _query_db,
}


async def _classify_sources(query: str) -> list[SourceClassification]:
    """Use LLM structured output to classify which sources to query."""
    from app.core.agent_config import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(temperature=0.0, max_tokens=512)
    structured_llm = llm.with_structured_output(ClassificationResult)

    result = await structured_llm.ainvoke([
        SystemMessage(content=(
            "Analyze this query and determine which knowledge sources to consult.\n"
            "For each relevant source, generate a targeted sub-question.\n\n"
            "Available sources:\n"
            "- **rag**: Previously indexed documents, internal wikis, saved knowledge. "
            "Use when the user asks about content that has been explicitly indexed.\n"
            "- **web**: Current information, news, facts, recent events, general knowledge. "
            "Use when the user needs up-to-date or publicly available information.\n"
            "- **db**: Test results, metrics, platform data from the application database. "
            "Use when the user asks about test runs, analytics, schedules, or platform data.\n\n"
            "Return ONLY sources that are relevant. A simple question may need just one source; "
            "a broad question may need multiple.\n"
            "When in doubt, prefer 'web' for general questions and 'db' for platform data questions."
        )),
        HumanMessage(content=query),
    ])

    return result.classifications


async def _synthesize(query: str, results: list[tuple[str, str]]) -> str:
    """Combine results from multiple sources into a coherent answer."""
    if not results:
        return "No results found from any knowledge source."

    if len(results) == 1:
        source, text = results[0]
        return f"**[{source.upper()}]** {text}"

    from app.core.agent_config import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    formatted = "\n\n".join(
        f"**[{source.upper()}]**\n{text}"
        for source, text in results
    )

    llm = get_llm(temperature=0.3, max_tokens=2048)
    response = await llm.ainvoke([
        SystemMessage(content=(
            f'Synthesize these search results to answer: "{query}"\n\n'
            "- Combine information from multiple sources without redundancy\n"
            "- Highlight the most relevant and actionable information\n"
            "- Attribute which source each piece of info came from\n"
            "- Keep the response concise and well-organized\n"
            "- Respond in the same language as the original query"
        )),
        HumanMessage(content=formatted),
    ])

    return response.content


@tool
async def query_knowledge_base(query: str) -> str:
    """Search across multiple knowledge sources (indexed documents, web, database).

    Automatically classifies the query, searches relevant sources in parallel,
    and synthesizes results into a coherent answer with source attribution.

    Use this for any information-seeking question — about indexed documents,
    current events, test data, platform metrics, or general knowledge.

    Args:
        query: The question or search query to answer.
    """
    if not query or not query.strip():
        return "Error: Query cannot be empty."

    classifications = await _classify_sources(query)

    if not classifications:
        return "Unable to determine relevant knowledge sources for this query."

    logger.info(
        "KB router classified query '%s' -> %s",
        query[:50],
        [(c.source, c.sub_query[:40]) for c in classifications],
    )

    tasks = []
    for c in classifications:
        handler = _SOURCE_HANDLERS.get(c.source)
        if handler:
            tasks.append(handler(c.sub_query))

    results = await asyncio.gather(*tasks)

    return await _synthesize(query, list(results))
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/knowledge_base_tools.py
git commit -m "feat(kb-agent): add classifier, synthesizer, and main router tool"
```

---

### Task 4: Create the knowledge base subagent

**Files:**
- Create: `backend/app/agents/chat_assistant/subagents/knowledge_base_agent.py`

- [ ] **Step 1: Create the subagent file**

```python
"""
Knowledge Base Subagent — Multi-source router for knowledge queries.

Classifies queries, routes to RAG/Web/DB sources in parallel,
and synthesizes results into a coherent answer with source attribution.
Replaces the separate rag-knowledge and search subagents.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.knowledge_base_tools import query_knowledge_base


def create_knowledge_base_graph(llm):
    """Create the compiled graph for the knowledge base subagent."""
    return create_agent(
        model=llm,
        tools=[query_knowledge_base],
        system_prompt=(
            "You are a knowledge base specialist. You answer questions by searching "
            "across multiple knowledge sources: indexed documents, the web, and the "
            "application database.\n\n"
            "**How you work:**\n"
            "1. Use the query_knowledge_base tool to search across sources\n"
            "2. The tool automatically classifies your query, searches relevant sources "
            "in parallel, and synthesizes the results\n"
            "3. Present the synthesized answer to the user with clear source attribution\n\n"
            "**Guidelines:**\n"
            "- For simple factual questions, one tool call is sufficient\n"
            "- For complex research questions, you may make 2-3 calls with different angles\n"
            "- Always present results clearly, noting which sources provided which information\n"
            "- If results are insufficient, suggest what additional sources could help\n"
            "- Respond in the same language as the user's message\n"
            "- Document indexing is handled separately — do not attempt to index documents\n"
        ),
    )


def get_knowledge_base_subagent(llm):
    """Get the compiled knowledge base subagent."""
    return CompiledSubAgent(
        name="knowledge-base",
        description=(
            "Search across multiple knowledge sources (indexed documents, web, database) "
            "to answer questions. Use this when the user asks any information-seeking question "
            "— about documents, current events, test data, metrics, or general knowledge. "
            "Automatically routes to the best sources and synthesizes results."
        ),
        runnable=create_knowledge_base_graph(llm),
    )
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/subagents/knowledge_base_agent.py
git commit -m "feat(kb-agent): add knowledge base subagent definition"
```

---

### Task 5: Update subagents `__init__.py`

**Files:**
- Modify: `backend/app/agents/chat_assistant/subagents/__init__.py`

- [ ] **Step 1: Replace rag and search exports with knowledge_base**

Update the file to remove `get_rag_subagent` and `get_search_subagent`, add `get_knowledge_base_subagent`:

```python
"""
Subagents for the Chat Agent.

Each subagent is a specialized agent compiled with specific tools
for a particular domain.
"""

from .test_query_agent import get_test_query_subagent
from .user_admin_agent import get_user_admin_subagent
from .test_reviewer_agent import get_test_reviewer_subagent
from .analytics_agent import get_analytics_subagent
from .email_agent import get_email_subagent
from .data_analysis_agent import get_data_analysis_subagent
from .knowledge_base_agent import get_knowledge_base_subagent
from .sql_agent import get_sql_query_subagent
from .content_builder_agent import get_content_builder_subagent

__all__ = [
    "get_test_query_subagent",
    "get_user_admin_subagent",
    "get_test_reviewer_subagent",
    "get_analytics_subagent",
    "get_email_subagent",
    "get_data_analysis_subagent",
    "get_knowledge_base_subagent",
    "get_sql_query_subagent",
    "get_content_builder_subagent",
]
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/subagents/__init__.py
git commit -m "refactor(kb-agent): replace rag and search exports with knowledge_base"
```

---

### Task 6: Update chat_agent.py registration

**Files:**
- Modify: `backend/app/agents/chat_assistant/chat_agent.py`

- [ ] **Step 1: Update imports — replace rag/search with knowledge_base**

In `chat_agent.py`, change the import block (lines 23-34) from:

```python
from app.agents.chat_assistant.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
    get_search_subagent,
    get_email_subagent,
    get_data_analysis_subagent,
    get_rag_subagent,
    get_sql_query_subagent,
    get_content_builder_subagent,
)
```

to:

```python
from app.agents.chat_assistant.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
    get_knowledge_base_subagent,
    get_email_subagent,
    get_data_analysis_subagent,
    get_sql_query_subagent,
    get_content_builder_subagent,
)
```

- [ ] **Step 2: Update subagents list — replace rag/search with knowledge_base**

In `chat_agent.py`, change the `subagents` list inside `create_deep_agent` (around lines 137-148) from:

```python
            subagents=[
                get_test_query_subagent(llm),
                get_user_admin_subagent(llm),
                get_test_reviewer_subagent(llm),
                get_analytics_subagent(llm),
                get_search_subagent(llm),
                get_email_subagent(llm),
                get_data_analysis_subagent(llm),
                get_rag_subagent(llm),
                get_sql_query_subagent(llm),
                get_content_builder_subagent(llm),
            ],
```

to:

```python
            subagents=[
                get_test_query_subagent(llm),
                get_user_admin_subagent(llm),
                get_test_reviewer_subagent(llm),
                get_analytics_subagent(llm),
                get_knowledge_base_subagent(llm),
                get_email_subagent(llm),
                get_data_analysis_subagent(llm),
                get_sql_query_subagent(llm),
                get_content_builder_subagent(llm),
            ],
```

- [ ] **Step 3: Update `_get_subagent_description`**

Replace the `"search"` and `"rag-knowledge"` entries with a single `"knowledge-base"` entry:

```python
    def _get_subagent_description(self, subagent_name: str) -> str:
        """Get human-readable description for subagent."""
        descriptions = {
            "test-query": "Querying test cases and suites",
            "user-admin": "Managing user accounts and permissions",
            "test-reviewer": "Analyzing test results and outcomes",
            "analytics": "Processing analytics and metrics",
            "knowledge-base": "Searching across knowledge sources",
            "email": "Sending emails and querying email history",
            "data-analysis": "Analyzing data, generating charts and visualizations",
            "sql-query": "Querying the database with SQL",
            "content-builder": "Researching topics and writing content",
            "planner": "Planning task execution",
            "executor": "Executing planned tasks",
            "reviewer": "Reviewing and validating results",
        }
        return descriptions.get(subagent_name, "Processing request")
```

- [ ] **Step 4: Commit**

```bash
git add platform/backend/app/agents/chat_assistant/chat_agent.py
git commit -m "refactor(kb-agent): register knowledge-base subagent, remove rag and search"
```

---

### Task 7: Write tests

**Files:**
- Create: `backend/app/tests/test_knowledge_base_tools.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for Knowledge Base tools — classification, synthesis, and router."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.agents.chat_assistant.knowledge_base_tools import (
    SourceClassification,
    ClassificationResult,
    _synthesize,
    query_knowledge_base,
)


class TestSourceClassification:
    def test_valid_rag(self):
        c = SourceClassification(source="rag", sub_query="find auth docs")
        assert c.source == "rag"

    def test_valid_web(self):
        c = SourceClassification(source="web", sub_query="latest news")
        assert c.source == "web"

    def test_valid_db(self):
        c = SourceClassification(source="db", sub_query="test pass rate")
        assert c.source == "db"

    def test_invalid_source_rejected(self):
        with pytest.raises(Exception):
            SourceClassification(source="invalid", sub_query="test")


class TestClassificationResult:
    def test_single(self):
        r = ClassificationResult(
            classifications=[SourceClassification(source="web", sub_query="test")]
        )
        assert len(r.classifications) == 1

    def test_multiple(self):
        r = ClassificationResult(classifications=[
            SourceClassification(source="rag", sub_query="docs"),
            SourceClassification(source="web", sub_query="info"),
            SourceClassification(source="db", sub_query="data"),
        ])
        assert len(r.classifications) == 3

    def test_empty(self):
        r = ClassificationResult(classifications=[])
        assert len(r.classifications) == 0


class TestSynthesize:
    @pytest.mark.asyncio
    async def test_empty_results(self):
        result = await _synthesize("query", [])
        assert "No results" in result

    @pytest.mark.asyncio
    async def test_single_result_no_llm(self):
        result = await _synthesize("query", [("rag", "content here")])
        assert "[RAG]" in result
        assert "content here" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools.get_llm")
    async def test_multiple_results_uses_llm(self, mock_get_llm):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Combined answer"))
        mock_get_llm.return_value = mock_llm
        result = await _synthesize("query", [("rag", "a"), ("web", "b")])
        assert "Combined answer" in result


class TestQueryKnowledgeBase:
    def test_tool_name(self):
        assert query_knowledge_base.name == "query_knowledge_base"

    def test_tool_description(self):
        assert "knowledge" in query_knowledge_base.description.lower()

    @pytest.mark.asyncio
    async def test_empty_query(self):
        result = await query_knowledge_base.ainvoke({"query": ""})
        assert "Error" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._synthesize")
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_no_classifications(self, mock_classify, mock_synth):
        mock_classify.return_value = []
        result = await query_knowledge_base.ainvoke({"query": "test"})
        assert "Unable to determine" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._synthesize")
    @patch("app.agents.chat_assistant.knowledge_base_tools._query_web")
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_routes_and_synthesizes(self, mock_classify, mock_web, mock_synth):
        mock_classify.return_value = [
            SourceClassification(source="web", sub_query="search web"),
        ]
        mock_web.return_value = ("web", "results")
        mock_synth.return_value = "Final answer"
        result = await query_knowledge_base.ainvoke({"query": "test question"})
        assert result == "Final answer"


class TestKnowledgeBaseSubagent:
    def test_returns_compiled(self):
        from deepagents import CompiledSubAgent
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent
        subagent = get_knowledge_base_subagent(MagicMock())
        assert isinstance(subagent, CompiledSubAgent)
        assert subagent.name == "knowledge-base"

    def test_description(self):
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent
        subagent = get_knowledge_base_subagent(MagicMock())
        assert "knowledge" in subagent.description.lower()

    def test_has_runnable(self):
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent
        subagent = get_knowledge_base_subagent(MagicMock())
        assert subagent.runnable is not None
```

- [ ] **Step 2: Run tests**

```bash
cd platform/backend && python -m pytest app/tests/test_knowledge_base_tools.py -v
```

- [ ] **Step 3: Commit**

```bash
git add platform/backend/app/tests/test_knowledge_base_tools.py
git commit -m "test(kb-agent): add tests for classification, synthesis, and router"
```

---

### Task 8: Verify integration

- [ ] **Step 1: Verify no remaining references to removed subagents**

```bash
cd platform/backend && grep -rn "get_rag_subagent\|get_search_subagent" app/agents/chat_assistant/chat_agent.py app/agents/chat_assistant/subagents/__init__.py
```

Expected: No output.

- [ ] **Step 2: Verify module imports cleanly**

```bash
cd platform/backend && python -c "from app.agents.chat_assistant.subagents import get_knowledge_base_subagent; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run full test suite**

```bash
cd platform/backend && python -m pytest app/tests/ -v --tb=short
```

Expected: All tests pass.
