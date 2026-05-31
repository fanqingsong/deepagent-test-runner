# Deep Research Subagent Design

## Overview

Add a deep research subagent to the chat assistant that performs multi-step web research with planning, parallel researcher delegation, and synthesized report generation with citations.

## Architecture

The deep research subagent is a **nested deep agent** - registered as a `CompiledSubAgent` of the main chat assistant, but internally a full `create_deep_agent` with its own researcher sub-agents.

```
Main Chat Assistant (create_deep_agent)
  ├── test-query subagent
  ├── search subagent            (existing quick search)
  ├── deep-research subagent     (NEW - nested create_deep_agent)
  │     └── researcher-agent     (internal sub-subagent)
  ├── email subagent
  └── ... other subagents
```

## New Files

| File | Purpose |
|------|---------|
| `backend/app/agents/chat_assistant/deep_research_tools.py` | Search + webpage fetch tools |
| `backend/app/agents/chat_assistant/subagents/deep_research_agent.py` | Nested deep agent definition |

## Modified Files

| File | Change |
|------|--------|
| `backend/app/agents/chat_assistant/chat_agent.py` | Register deep-research subagent in subagents list |
| `backend/requirements.txt` | Add `markdownify` dependency |

## Components

### 1. Deep Research Tools (`deep_research_tools.py`)

Two tools for the researcher sub-agents:

- **`tavily_search(query, max_results, topic)`**: Searches via Tavily API to discover URLs, then fetches full webpage content for each result. Returns markdown-formatted content with titles, URLs, and page text.
- **`fetch_webpage_content(url, timeout)`**: Helper that fetches a URL via httpx and converts HTML to markdown using markdownify.

The key difference from existing `search_tools.py` is that this tool fetches **full webpage content** (not just summaries), enabling deep analysis by the researcher.

### 2. Deep Research Agent (`deep_research_agent.py`)

Three components:

1. **Orchestrator**: The outer `create_deep_agent` with:
   - System prompt containing research workflow instructions, delegation strategy, report writing guidelines
   - Access to `tavily_search` and `write_todos`/`write_file` tools
   - Max 3 concurrent researcher sub-agents
   - Max 3 delegation rounds

2. **Researcher sub-agent**: A `CompiledSubAgent` with:
   - Name: `researcher-agent`
   - Tools: `tavily_search`
   - System prompt with search strategy, tool call budgets (2-5 calls), source attribution format

3. **Entry function**: `get_deep_research_subagent(llm)` returns `CompiledSubAgent` for registration in the main chat agent.

### 3. Prompt Templates

**Orchestrator Prompt** covers:
- Research workflow: Plan -> Save request -> Delegate -> Synthesize -> Write report -> Verify
- Delegation strategy: Default 1 sub-agent; parallelize only for explicit comparisons
- Report writing guidelines: Structure by type (comparison, list, overview)
- Citation format: `[1]`, `[2]` inline with numbered Sources section

**Researcher Prompt** covers:
- Date-aware context
- Search strategy: broad first, then narrow
- Tool call budgets: 2-3 for simple, up to 5 for complex
- Stop conditions: comprehensive answer, 3+ sources, or diminishing returns
- Response format: headings, inline citations, Sources section

## Dependencies

| Package | Status | Purpose |
|---------|--------|---------|
| `tavily-python` / `langchain_tavily` | Available | Web search API |
| `httpx` | Available | HTTP client for fetching webpages |
| `markdownify` | **New** | HTML to markdown conversion |

## Configuration

- `TAVILY_API_KEY`: Already required by existing search tools
- `LLM_BASE_URL` / `LLM_MODEL`: Uses same GLM model as other agents
- Max concurrent researchers: 3
- Max delegation rounds: 3

## User Experience

When a user asks for deep research:

1. Main chat assistant recognizes the request requires research
2. Delegates to `deep-research` subagent via `task()` tool
3. Subagent creates todo list, delegates to researcher(s)
4. Researchers search, fetch content, analyze, return findings with citations
5. Orchestrator synthesizes into a structured report
6. Report flows back through the chat interface as the assistant's response

The deep research subagent is read-only - it only searches and reads, never modifies project state.

## Out of Scope

- File download or document processing
- Image analysis from search results
- Caching search results between sessions
- Custom search provider configuration
