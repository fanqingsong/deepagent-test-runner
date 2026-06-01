"""
Knowledge Base Subagent — Multi-source router for knowledge queries.

Classifies queries, routes to RAG/Web/DB sources in parallel,
and synthesizes results into a coherent answer with source attribution.
Replaces the separate rag-knowledge and search subagents.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.knowledge_base_tools import query_knowledge_base
from app.agents.chat_assistant.rag_tools import index_web_page, index_text_content, list_indexed_sources


def create_knowledge_base_graph(llm):
    """Create the compiled graph for the knowledge base subagent."""
    return create_agent(
        model=llm,
        tools=[query_knowledge_base, index_web_page, index_text_content, list_indexed_sources],
        system_prompt=(
            "You are a knowledge base specialist. You manage the knowledge base by indexing "
            "documents and answering questions from multiple sources.\n\n"
            "**Document Indexing:**\n"
            "When the user wants to add content to the knowledge base:\n"
            "- Use index_web_page(url) to index a web page\n"
            "- Use index_text_content(text, source_name) to index raw text\n"
            "- Use list_indexed_sources() to show what's already indexed\n\n"
            "**Question Answering:**\n"
            "Use the query_knowledge_base tool to search across sources.\n"
            "It automatically classifies queries, searches RAG/Web/DB in parallel, "
            "and synthesizes results with source attribution.\n\n"
            "**Guidelines:**\n"
            "- Always confirm what was indexed (chunk count, source name)\n"
            "- For simple factual questions, one query call is sufficient\n"
            "- For complex research questions, make 2-3 calls with different angles\n"
            "- Respond in the same language as the user's message\n"
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
