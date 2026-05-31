# Deep Research Subagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deep research subagent to the chat assistant that performs multi-step web research with planning, parallel researcher delegation, and synthesized report generation with citations.

**Architecture:** A nested deep agent registered as a `CompiledSubAgent` of the main chat assistant. Internally uses `create_deep_agent` with its own `researcher-agent` sub-subagent. The researcher gets a `tavily_search` tool that discovers URLs via Tavily and fetches full webpage content for analysis.

**Tech Stack:** LangChain, Deep Agents (`create_deep_agent`, `CompiledSubAgent`), Tavily, httpx, markdownify

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/agents/chat_assistant/deep_research_tools.py` | Create | `tavily_search` tool with full content fetching |
| `backend/app/agents/chat_assistant/subagents/deep_research_agent.py` | Create | Nested deep agent with researcher sub-subagent |
| `backend/app/agents/chat_assistant/subagents/__init__.py` | Modify | Export `get_deep_research_subagent` |
| `backend/app/agents/chat_assistant/chat_agent.py` | Modify | Register deep-research subagent in imports + subagents list |
| `backend/requirements.txt` | Modify | Add `markdownify` dependency |

---

### Task 1: Add markdownify dependency

**Files:**
- Modify: `backend/requirements.txt:27` (after the `httpx` line)

- [ ] **Step 1: Add markdownify to requirements.txt**

Add `markdownify>=0.13.0` to `backend/requirements.txt` after the existing `httpx` line (line 27):

```
httpx>=0.27.1,<1.0.0
markdownify>=0.13.0
```

- [ ] **Step 2: Rebuild the backend container to install the new dependency**

```bash
cd /home/fqs/workspace/self/deepagent-test-runner/platform
docker compose build backend
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add markdownify dependency for deep research content extraction"
```

---

### Task 2: Create deep research tools

**Files:**
- Create: `backend/app/agents/chat_assistant/deep_research_tools.py`

This file provides the `tavily_search` tool used by researcher sub-agents. Unlike the existing `search_tools.py` (which returns summaries), this tool fetches **full webpage content** so researchers can do deep analysis.

- [ ] **Step 1: Create `deep_research_tools.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/chat_assistant/deep_research_tools.py
git commit -m "feat: add deep research tools with full-content tavily search"
```

---

### Task 3: Create deep research agent

**Files:**
- Create: `backend/app/agents/chat_assistant/subagents/deep_research_agent.py`

This is the core: a nested `create_deep_agent` with its own researcher sub-agent. The orchestrator plans, delegates to researchers, and synthesizes findings into a cited report.

- [ ] **Step 1: Create `deep_research_agent.py`**

```python
"""
Deep Research Subagent — Multi-step web research with planning and synthesis.

A nested deep agent that plans research, delegates to researcher sub-agents,
and synthesizes findings into a comprehensive cited report.
"""

from datetime import datetime

from deepagents import CompiledSubAgent, create_deep_agent

from app.agents.chat_assistant.deep_research_tools import tavily_search

RESEARCH_WORKFLOW_INSTRUCTIONS = """# Research Workflow

Follow this workflow for all research requests:

1. **Plan**: Create a todo list with write_todos to break down the research into focused tasks
2. **Save the request**: Use write_file() to save the user's research question to `/research_request.md`
3. **Research**: Delegate research tasks to sub-agents using the task() tool - ALWAYS use sub-agents for research, never conduct research yourself
4. **Synthesize**: Review all sub-agent findings and consolidate citations (each unique URL gets one number across all findings)
5. **Write Report**: Write a comprehensive final report to `/final_report.md` (see Report Writing Guidelines below)
6. **Verify**: Read `/research_request.md` and confirm you've addressed all aspects with proper citations and structure

## Research Planning Guidelines
- Batch similar research tasks into a single TODO to minimize overhead
- For simple fact-finding questions, use 1 sub-agent
- For comparisons or multi-faceted topics, delegate to multiple parallel sub-agents
- Each sub-agent should research one specific aspect and return findings

## Report Writing Guidelines

When writing the final report to `/final_report.md`, follow these structure patterns:

**For comparisons:**
1. Introduction
2. Overview of topic A
3. Overview of topic B
4. Detailed comparison
5. Conclusion

**For lists/rankings:**
Simply list items with details - no introduction needed:
1. Item 1 with explanation
2. Item 2 with explanation

**For summaries/overviews:**
1. Overview of topic
2. Key concepts
3. Conclusion

**General guidelines:**
- Use clear section headings (## for sections, ### for subsections)
- Write in paragraph form by default - be text-heavy, not just bullet points
- Do NOT use self-referential language ("I found...", "I researched...")
- Write as a professional report without meta-commentary
- Each section should be comprehensive and detailed
- Use bullet points only when listing is more appropriate than prose

**Citation format:**
- Cite sources inline using [1], [2], [3] format
- Assign each unique URL a single citation number across ALL sub-agent findings
- End report with ### Sources section listing each numbered source
- Number sources sequentially without gaps (1,2,3,4...)
- Format: [1] Source Title: URL (each on separate line)
"""

RESEARCHER_INSTRUCTIONS = """You are a research assistant conducting research on the user's input topic. For context, today's date is {date}.

Your job is to use tools to gather information about the user's input topic.
You can use the tavily_search tool to find resources that can help answer the research question.
You can call it in series or in parallel, your research is conducted in a tool-calling loop.

Think like a human researcher with limited time. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Start with broader searches** - Use broad, comprehensive queries first
3. **After each search, pause and assess** - Do I have enough to answer? What's still missing?
4. **Execute narrower searches as you gather information** - Fill in the gaps
5. **Stop when you can answer confidently** - Don't keep searching for perfection

**Tool Call Budgets** (Prevent excessive searching):
- **Simple queries**: Use 2-3 search tool calls maximum
- **Complex queries**: Use up to 5 search tool calls maximum
- **Always stop**: After 5 search tool calls if you cannot find the right sources

**Stop Immediately When**:
- You can answer the user's question comprehensively
- You have 3+ relevant examples/sources for the question
- Your last 2 searches returned similar information

When providing your findings back to the orchestrator:

1. **Structure your response**: Organize findings with clear headings and detailed explanations
2. **Cite sources inline**: Use [1], [2], [3] format when referencing information from your searches
3. **Include Sources section**: End with ### Sources listing each numbered source with title and URL

Example:
## Key Findings

Context engineering is a critical technique for AI agents [1]. Studies show that proper context management can improve performance by 40% [2].

### Sources
[1] Context Engineering Guide: https://example.com/context-guide
[2] AI Performance Study: https://example.com/study
"""

SUBAGENT_DELEGATION_INSTRUCTIONS = """# Sub-Agent Research Coordination

Your role is to coordinate research by delegating tasks from your TODO list to specialized research sub-agents.

## Delegation Strategy

**DEFAULT: Start with 1 sub-agent** for most queries:
- "What is quantum computing?" -> 1 sub-agent (general overview)
- "List the top 10 coffee shops in San Francisco" -> 1 sub-agent
- "Research context engineering for AI agents" -> 1 sub-agent (covers all aspects)

**ONLY parallelize when the query EXPLICITLY requires comparison or has clearly independent aspects:**

**Explicit comparisons** -> 1 sub-agent per element:
- "Compare OpenAI vs Anthropic vs DeepMind AI safety approaches" -> 3 parallel sub-agents
- "Compare Python vs JavaScript for web development" -> 2 parallel sub-agents

**Clearly separated aspects** -> 1 sub-agent per aspect (use sparingly):
- "Research renewable energy adoption in Europe, Asia, and North America" -> 3 parallel sub-agents
- Only use this pattern when aspects cannot be covered efficiently by a single comprehensive search

## Key Principles
- **Bias towards single sub-agent**: One comprehensive research task is more token-efficient than multiple narrow ones
- **Avoid premature decomposition**: Don't break "research X" into "research X overview", "research X techniques", "research X applications" - just use 1 sub-agent for all of X
- **Parallelize only for clear comparisons**: Use multiple sub-agents when comparing distinct entities or geographically separated data

## Parallel Execution Limits
- Use at most {max_concurrent_research_units} parallel sub-agents per iteration
- Make multiple task() calls in a single response to enable parallel execution
- Each sub-agent returns findings independently

## Research Limits
- Stop after {max_researcher_iterations} delegation rounds if you haven't found adequate sources
- Stop when you have sufficient information to answer comprehensively
- Bias towards focused research over exhaustive exploration"""

MAX_CONCURRENT_RESEARCH_UNITS = 3
MAX_RESEARCHER_ITERATIONS = 3


def _get_orchestrator_instructions() -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    return (
        RESEARCH_WORKFLOW_INSTRUCTIONS
        + "\n\n"
        + "=" * 80
        + "\n\n"
        + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
            max_concurrent_research_units=MAX_CONCURRENT_RESEARCH_UNITS,
            max_researcher_iterations=MAX_RESEARCHER_ITERATIONS,
        )
    )


def _get_researcher_instructions() -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    return RESEARCHER_INSTRUCTIONS.format(date=current_date)


def get_deep_research_subagent(llm):
    """Create the deep research subagent (nested deep agent)."""
    researcher_sub_agent = {
        "name": "researcher-agent",
        "description": "Delegate research to the sub-agent. Give one topic at a time.",
        "system_prompt": _get_researcher_instructions(),
        "tools": [tavily_search],
    }

    agent = create_deep_agent(
        model=llm,
        tools=[tavily_search],
        system_prompt=_get_orchestrator_instructions(),
        subagents=[researcher_sub_agent],
    )

    return CompiledSubAgent(
        name="deep-research",
        description=(
            "Conduct deep multi-step web research on a topic. Use this for complex research "
            "questions that require gathering information from multiple sources, comparing topics, "
            "or producing a comprehensive cited report. For quick lookups or simple questions, "
            "prefer the 'search' subagent instead."
        ),
        runnable=agent,
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/chat_assistant/subagents/deep_research_agent.py
git commit -m "feat: add deep research agent with nested researcher sub-agent"
```

---

### Task 4: Register the deep research subagent

**Files:**
- Modify: `backend/app/agents/chat_assistant/subagents/__init__.py:16-30`
- Modify: `backend/app/agents/chat_assistant/chat_agent.py:23-34` (imports) and `chat_agent.py:137-148` (subagents list)

- [ ] **Step 1: Add export to `subagents/__init__.py`**

Add the import on line 17 (after the `content_builder_agent` import) and add to `__all__` on line 29:

```python
# Add after line 17:
from .deep_research_agent import get_deep_research_subagent

# Add to __all__ list (after "get_content_builder_subagent"):
    "get_deep_research_subagent",
```

The full file becomes:

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
from .search_agent import get_search_subagent
from .email_agent import get_email_subagent
from .data_analysis_agent import get_data_analysis_subagent
from .rag_agent import get_rag_subagent
from .sql_agent import get_sql_query_subagent
from .content_builder_agent import get_content_builder_subagent
from .deep_research_agent import get_deep_research_subagent

__all__ = [
    "get_test_query_subagent",
    "get_user_admin_subagent",
    "get_test_reviewer_subagent",
    "get_analytics_subagent",
    "get_search_subagent",
    "get_email_subagent",
    "get_data_analysis_subagent",
    "get_rag_subagent",
    "get_sql_query_subagent",
    "get_content_builder_subagent",
    "get_deep_research_subagent",
]
```

- [ ] **Step 2: Add import to `chat_agent.py`**

In `chat_agent.py`, add `get_deep_research_subagent` to the existing import block from `subagents` (around line 23-34):

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
    get_deep_research_subagent,
)
```

- [ ] **Step 3: Add to subagents list in `chat_agent.py`**

Add `get_deep_research_subagent(llm),` to the `subagents=[...]` list (around line 137-148):

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
    get_deep_research_subagent(llm),
],
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/chat_assistant/subagents/__init__.py backend/app/agents/chat_assistant/chat_agent.py
git commit -m "feat: register deep research subagent in chat agent"
```

---

### Task 5: Rebuild and verify

- [ ] **Step 1: Rebuild backend container**

```bash
cd /home/fqs/workspace/self/deepagent-test-runner/platform
docker compose build backend
docker compose up -d backend
```

- [ ] **Step 2: Verify backend starts without errors**

```bash
docker compose logs backend --tail 30
```

Expected: No import errors related to `deep_research_agent` or `deep_research_tools`. Look for `Application startup complete` in logs.

- [ ] **Step 3: Verify the subagent is loaded**

```bash
docker compose logs backend 2>&1 | grep -i "deep.research"
```

Expected: No errors. If the agent initialization logs subagent names, `deep-research` should appear.

- [ ] **Step 4: Commit any fixups if needed**

---

## Self-Review

**Spec coverage:**
- [x] Nested deep agent architecture -> Task 3
- [x] Tavily search with full content fetching -> Task 2
- [x] Researcher sub-agent with tool call budgets -> Task 3 (RESEARCHER_INSTRUCTIONS prompt)
- [x] Orchestrator with planning, delegation, synthesis -> Task 3 (RESEARCH_WORKFLOW_INSTRUCTIONS prompt)
- [x] Citation format [1], [2] with Sources section -> Task 3 (prompts)
- [x] markdownify dependency -> Task 1
- [x] Registration in main agent -> Task 4
- [x] Read-only (no state modification tools) -> Tasks 2-3 (only search tools, no write tools exposed to researcher)

**Placeholder scan:** No TBDs, TODOs, or vague steps. All code is complete.

**Type consistency:** `get_deep_research_subagent(llm)` returns `CompiledSubAgent` consistent with all other subagent functions. Import in `__init__.py` matches the function name in `deep_research_agent.py`.
