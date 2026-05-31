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
