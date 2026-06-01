"""
RAG Tools — Document indexing, retrieval, and knowledge base management.

Uses PGVector (PostgreSQL + pgvector extension) for persistent vector storage.
Documents are embedded and stored in PostgreSQL, surviving container restarts.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import bs4
import requests
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_vector_store: Optional[PGVector] = None
_embeddings: Optional[OpenAIEmbeddings] = None
_indexed_sources: dict[str, dict] = {}


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=os.getenv("LLM_EMBEDDING_MODEL", "BAAI/bge-m3"),
            base_url=os.getenv("LLM_EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
            api_key=os.getenv("LLM_EMBEDDING_API_KEY"),
        )
    return _embeddings


def _get_connection_string() -> str:
    """Build psycopg connection string from async DATABASE_URL."""
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://cc_test_user:password@postgres:5432/cc_test_db")
    return url.replace("+asyncpg", "")


def _get_vector_store() -> PGVector:
    global _vector_store
    if _vector_store is None:
        _vector_store = PGVector(
            embedding=_get_embeddings(),
            collection_name="rag_knowledge",
            connection=_get_connection_string(),
            use_jsonb=True,
        )
    return _vector_store


@tool
def index_web_page(url: str, chunk_size: int = 1000) -> str:
    """Index a web page by fetching its content, splitting into chunks, and storing in the vector store.

    Args:
        url: The URL of the web page to index.
        chunk_size: Size of each text chunk in characters (default 1000).
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        if not text.strip():
            return json.dumps({"success": False, "error": "No text content found at URL"})

        doc = Document(page_content=text, metadata={"source": url})
        return _index_documents([doc], url, chunk_size)

    except requests.RequestException as e:
        return json.dumps({"success": False, "error": f"Failed to fetch URL: {e}"})
    except Exception as e:
        logger.error("Error indexing web page %s: %s", url, e)
        return json.dumps({"success": False, "error": str(e)})


@tool
def index_text_content(text: str, source_name: str, chunk_size: int = 1000) -> str:
    """Index raw text content by splitting into chunks and storing in the vector store.

    Args:
        text: The text content to index.
        source_name: A name to identify this content source.
        chunk_size: Size of each text chunk in characters (default 1000).
    """
    if not text.strip():
        return json.dumps({"success": False, "error": "No text content provided"})

    doc = Document(page_content=text, metadata={"source": source_name})
    return _index_documents([doc], source_name, chunk_size)


def _index_documents(docs: list[Document], source_name: str, chunk_size: int) -> str:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size * 0.2),
        add_start_index=True,
    )
    all_splits = splitter.split_documents(docs)

    if not all_splits:
        return json.dumps({"success": False, "error": "Document splitting produced no chunks"})

    store = _get_vector_store()
    store.add_documents(documents=all_splits)

    existing = _indexed_sources.get(source_name, {})
    _indexed_sources[source_name] = {
        "chunk_count": existing.get("chunk_count", 0) + len(all_splits),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }

    return json.dumps({
        "success": True,
        "source": source_name,
        "chunks_indexed": len(all_splits),
        "total_chunks": _indexed_sources[source_name]["chunk_count"],
    })


@tool(response_format="content_and_artifact")
def retrieve_context(query: str, k: int = 4) -> tuple[str, list[Document]]:
    """Retrieve relevant context from the knowledge base to help answer a query.

    Args:
        query: The search query to find relevant context.
        k: Number of results to return (default 4).
    """
    store = _get_vector_store()
    retrieved_docs = store.similarity_search(query, k=k)

    if not retrieved_docs:
        return "No relevant documents found in the knowledge base.", []

    serialized = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}"
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


@tool
def list_indexed_sources() -> str:
    """List all sources currently indexed in the knowledge base."""
    if not _indexed_sources:
        return json.dumps({"sources": [], "message": "No sources indexed yet"})

    sources = [
        {
            "name": name,
            "chunk_count": info["chunk_count"],
            "indexed_at": info["indexed_at"],
        }
        for name, info in _indexed_sources.items()
    ]
    return json.dumps({"sources": sources, "total_sources": len(sources)})
