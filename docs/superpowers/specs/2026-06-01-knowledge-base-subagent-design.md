# Knowledge Base Subagent Design

## Overview

Add a `knowledge-base` subagent to the chat assistant that replaces the existing `rag-knowledge` and `search` subagents with a unified router. The router classifies queries via LLM structured output, dispatches to relevant knowledge sources (RAG, Web, DB) in parallel, and synthesizes results into a coherent answer with source attribution.

## Architecture

```
User query → classify (LLM structured output)
                ├── RAG source    → PGVector similarity search
                ├── Web source    → Tavily web search
                └── DB source     → SQL query (SELECT-only)
                → synthesize (LLM combines results)
```

The subagent uses `create_agent` with a single `query_knowledge_base` tool — consistent with all other subagents in the project. The router logic lives inside this tool rather than a separate StateGraph.

```
Main Chat Assistant (create_deep_agent)
  ├── test-query subagent
  ├── knowledge-base subagent    (NEW — replaces rag-knowledge + search)
  ├── sql-query subagent         (kept for explicit SQL tasks)
  ├── email subagent
  └── ... other subagents
```

## New Files

| File | Purpose |
|------|---------|
| `backend/app/agents/chat_assistant/knowledge_base_tools.py` | Router tool: classify → parallel dispatch → synthesize |
| `backend/app/agents/chat_assistant/subagents/knowledge_base_agent.py` | CompiledSubAgent registration |

## Modified Files

| File | Change |
|------|--------|
| `backend/app/agents/chat_assistant/chat_agent.py` | Replace `get_rag_subagent` + `get_search_subagent` imports/registrations with `get_knowledge_base_subagent`; update `_get_subagent_description` |
| `backend/app/agents/chat_assistant/subagents/__init__.py` | Remove `get_rag_subagent` and `get_search_subagent` exports, add `get_knowledge_base_subagent` |

## Components

### 1. Classification

Uses LLM structured output with a Pydantic model to classify the query:

- `source`: `Literal["rag", "web", "db"]`
- `sub_query`: targeted sub-question optimized for that source

The classifier receives a system prompt describing each source's strengths:

- **RAG**: indexed documents, internal wikis, previously saved knowledge
- **Web**: current information, news, facts, recent events
- **DB**: test results, metrics, platform data from PostgreSQL tables

Only relevant sources are returned. A simple factual question may route to one source; a broad research question may route to all three.

### 2. Parallel Dispatch

```python
tasks = []
for c in classifications:
    if c.source == "rag": tasks.append(_query_rag(c.sub_query))
    elif c.source == "web": tasks.append(_query_web(c.sub_query))
    elif c.source == "db": tasks.append(_query_db(c.sub_query))
results = await asyncio.gather(*tasks)
```

**Source handlers** (private async functions, not exposed as tools):

- `_query_rag(sub_query)` → imports and calls `retrieve_context` from `rag_tools.py`
- `_query_web(sub_query)` → uses `TavilySearchResults` from existing `search_tools.py` logic
- `_query_db(sub_query)` → generates SQL from natural language, executes SELECT-only query

### 3. DB Source Handler Safety

- Reuses SQL execution pattern from `sql_tools.py`
- Enforces SELECT-only: rejects queries starting with `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`
- LLM generates SQL from the sub-query, executes it, returns formatted text

### 4. Synthesis

- Single source result: pass through with light formatting (no extra LLM call)
- Multiple source results: LLM synthesizes into coherent answer with source attribution
- Each result prefixed with `[RAG]`, `[Web]`, or `[DB]` for attribution

### 5. Subagent Definition

`knowledge_base_agent.py` follows the standard pattern:

- `create_knowledge_base_graph(llm)` → `create_agent(model=llm, tools=[query_knowledge_base], system_prompt=...)`
- `get_knowledge_base_subagent(llm)` → `CompiledSubAgent(name="knowledge-base", description=..., runnable=...)`

System prompt covers:
- When to use the tool (any information-seeking question)
- Document indexing is handled separately (not by this subagent)
- Respond in the same language as the user

### 6. Error Handling

- Source handler failures are caught per-source; error string returned instead of result
- Synthesis proceeds with successful results only
- If all sources fail, returns a clear error message

## Dependencies

No new dependencies. Reuses existing packages:

- `langchain_tavily` / `tavily-python` — web search
- `langchain_openai` + `PGVector` — RAG retrieval
- `asyncio` — parallel dispatch
- `pydantic` — structured output for classification

## Out of Scope

- Document indexing (handled separately)
- File download or document processing
- Caching search results between sessions
- Replacing the standalone `sql-query` subagent
- Custom search provider configuration
