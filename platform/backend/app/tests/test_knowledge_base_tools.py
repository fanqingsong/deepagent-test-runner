"""Tests for Knowledge Base tools and subagent."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from unittest import mock

from app.agents.chat_assistant.knowledge_base_tools import (
    SourceClassification,
    ClassificationResult,
    _synthesize,
    _SOURCE_HANDLERS,
    query_knowledge_base,
    _query_rag,
    _query_web,
    _query_db,
)


# ---------------------------------------------------------------------------
# SourceClassification model
# ---------------------------------------------------------------------------

class TestSourceClassification:
    """Tests for the SourceClassification model."""

    def test_valid_rag_source(self):
        """Test that 'rag' is a valid source."""
        classification = SourceClassification(source="rag", sub_query="test query")
        assert classification.source == "rag"
        assert classification.sub_query == "test query"

    def test_valid_web_source(self):
        """Test that 'web' is a valid source."""
        classification = SourceClassification(source="web", sub_query="search query")
        assert classification.source == "web"
        assert classification.sub_query == "search query"

    def test_valid_db_source(self):
        """Test that 'db' is a valid source."""
        classification = SourceClassification(source="db", sub_query="sql query")
        assert classification.source == "db"
        assert classification.sub_query == "sql query"

    def test_invalid_source_rejected(self):
        """Test that invalid sources are rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            SourceClassification(source="invalid", sub_query="test")

    def test_source_required(self):
        """Test that source field is required."""
        with pytest.raises(Exception):
            SourceClassification(sub_query="test")

    def test_sub_query_required(self):
        """Test that sub_query field is required."""
        with pytest.raises(Exception):
            SourceClassification(source="rag")


# ---------------------------------------------------------------------------
# ClassificationResult model
# ---------------------------------------------------------------------------

class TestClassificationResult:
    """Tests for the ClassificationResult model."""

    def test_single_classification(self):
        """Test ClassificationResult with a single classification."""
        classification = SourceClassification(source="rag", sub_query="test")
        result = ClassificationResult(classifications=[classification])
        assert len(result.classifications) == 1
        assert result.classifications[0].source == "rag"

    def test_multiple_classifications(self):
        """Test ClassificationResult with multiple classifications."""
        classifications = [
            SourceClassification(source="rag", sub_query="doc query"),
            SourceClassification(source="web", sub_query="web query"),
            SourceClassification(source="db", sub_query="db query"),
        ]
        result = ClassificationResult(classifications=classifications)
        assert len(result.classifications) == 3
        assert result.classifications[0].source == "rag"
        assert result.classifications[1].source == "web"
        assert result.classifications[2].source == "db"

    def test_empty_classifications(self):
        """Test ClassificationResult with empty classifications list."""
        result = ClassificationResult(classifications=[])
        assert len(result.classifications) == 0
        assert result.classifications == []

    def test_classifications_field_required(self):
        """Test that classifications field is required."""
        with pytest.raises(Exception):
            ClassificationResult()


# ---------------------------------------------------------------------------
# _synthesize function
# ---------------------------------------------------------------------------

class TestSynthesize:
    """Tests for the _synthesize function."""

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test _synthesize with empty results list."""
        result = await _synthesize("test query", [])
        assert result == "Unable to retrieve information from any knowledge source."

    @pytest.mark.asyncio
    async def test_single_result_no_llm_call(self):
        """Test _synthesize with single result (no LLM call)."""
        results = [("rag", "result text")]
        result = await _synthesize("test query", results)
        assert result == "[rag]\n\nresult text"

    @pytest.mark.asyncio
    async def test_single_result_web_source(self):
        """Test _synthesize with single web result."""
        results = [("web", "web search results")]
        result = await _synthesize("test query", results)
        assert result == "[web]\n\nweb search results"

    @pytest.mark.asyncio
    async def test_single_result_db_source(self):
        """Test _synthesize with single db result."""
        results = [("db", "database query results")]
        result = await _synthesize("test query", results)
        assert result == "[db]\n\ndatabase query results"

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools.get_llm")
    async def test_multiple_results_llm_synthesis(self, mock_get_llm):
        """Test _synthesize with multiple results (uses LLM)."""
        # Mock LLM response
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content.strip.return_value = "Synthesized answer"
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        results = [
            ("rag", "rag result"),
            ("web", "web result"),
        ]
        result = await _synthesize("test query", results)

        # Verify LLM was called with correct parameters
        mock_get_llm.assert_called_once_with(temperature=0.3, max_tokens=2048)
        mock_llm.ainvoke.assert_called_once()
        assert "Synthesized from 2 sources" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools.get_llm")
    async def test_multiple_results_llm_error_fallback(self, mock_get_llm):
        """Test _synthesize fallback when LLM call fails."""
        # Mock LLM to raise exception
        mock_get_llm.side_effect = Exception("LLM error")

        results = [
            ("rag", "rag result"),
            ("web", "web result"),
        ]
        result = await _synthesize("test query", results)

        # Should fallback to concatenated results
        assert "[rag]" in result
        assert "rag result" in result
        assert "[web]" in result
        assert "web result" in result


# ---------------------------------------------------------------------------
# query_knowledge_base tool
# ---------------------------------------------------------------------------

class TestQueryKnowledgeBase:
    """Tests for the query_knowledge_base tool."""

    def test_tool_has_correct_name(self):
        """Test that the tool has the correct name."""
        assert query_knowledge_base.name == "query_knowledge_base"

    def test_tool_has_description(self):
        """Test that the tool has a description."""
        assert query_knowledge_base.description
        assert "knowledge" in query_knowledge_base.description.lower()

    @pytest.mark.asyncio
    async def test_empty_query_error(self):
        """Test that empty query returns error."""
        result = await query_knowledge_base.ainvoke({"query": ""})
        assert "Error" in result
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_whitespace_query_error(self):
        """Test that whitespace-only query returns error."""
        result = await query_knowledge_base.ainvoke({"query": "   "})
        assert "Error" in result
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_no_classifications_error(self, mock_classify):
        """Test that no classifications returns error."""
        mock_classify.return_value = []

        result = await query_knowledge_base.ainvoke({"query": "test query"})
        assert "Unable to determine appropriate knowledge sources" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._SOURCE_HANDLERS", {"rag": AsyncMock(return_value=("rag", "rag result"))})
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_routes_to_rag_correctly(self, mock_classify):
        """Test that queries are routed to RAG correctly."""
        # Setup classification to return RAG
        mock_classify.return_value = [
            SourceClassification(source="rag", sub_query="test query")
        ]

        result = await query_knowledge_base.ainvoke({"query": "test query"})

        # Verify result contains RAG response
        assert "[rag]" in result
        assert "rag result" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._SOURCE_HANDLERS", {"web": AsyncMock(return_value=("web", "web result"))})
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_routes_to_web_correctly(self, mock_classify):
        """Test that queries are routed to Web correctly."""
        # Setup classification to return Web
        mock_classify.return_value = [
            SourceClassification(source="web", sub_query="search query")
        ]

        result = await query_knowledge_base.ainvoke({"query": "search query"})

        # Verify result contains Web response
        assert "[web]" in result
        assert "web result" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._SOURCE_HANDLERS", {"db": AsyncMock(return_value=("db", "db result"))})
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_routes_to_db_correctly(self, mock_classify):
        """Test that queries are routed to DB correctly."""
        # Setup classification to return DB
        mock_classify.return_value = [
            SourceClassification(source="db", sub_query="database query")
        ]

        result = await query_knowledge_base.ainvoke({"query": "database query"})

        # Verify result contains DB response
        assert "[db]" in result
        assert "db result" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools.get_llm")
    @patch("app.agents.chat_assistant.knowledge_base_tools._query_rag", return_value=("rag", "rag result"))
    @patch("app.agents.chat_assistant.knowledge_base_tools._query_web", return_value=("web", "web result"))
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    async def test_multiple_sources_synthesized(self, mock_classify, mock_query_web, mock_query_rag, mock_get_llm):
        """Test that multiple sources are queried and synthesized."""
        # Setup classification to return multiple sources
        mock_classify.return_value = [
            SourceClassification(source="rag", sub_query="doc query"),
            SourceClassification(source="web", sub_query="web query"),
        ]

        # Mock LLM for synthesis
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content.strip.return_value = "Synthesized answer"
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # Create a custom dict to temporarily replace _SOURCE_HANDLERS
        import app.agents.chat_assistant.knowledge_base_tools as kb_module
        original_handlers = kb_module._SOURCE_HANDLERS
        kb_module._SOURCE_HANDLERS = {
            "rag": mock_query_rag,
            "web": mock_query_web,
            "db": kb_module._query_db
        }

        try:
            result = await query_knowledge_base.ainvoke({"query": "complex query"})
        finally:
            kb_module._SOURCE_HANDLERS = original_handlers

        # Verify synthesis occurred
        assert "Synthesized from 2 sources" in result

    @pytest.mark.asyncio
    @patch("app.agents.chat_assistant.knowledge_base_tools._classify_sources")
    @patch("app.agents.chat_assistant.knowledge_base_tools._query_rag")
    async def test_handler_exception_caught(self, mock_query_rag, mock_classify):
        """Test that handler exceptions are caught and formatted."""
        # Setup classification
        mock_classify.return_value = [
            SourceClassification(source="rag", sub_query="test query")
        ]
        # Mock handler to raise exception
        mock_query_rag.side_effect = Exception("Handler error")

        result = await query_knowledge_base.ainvoke({"query": "test query"})

        # Should format error in result
        assert "Error" in result or "Handler error" in result

    def test_source_handlers_dict(self):
        """Test that _SOURCE_HANDLERS has correct mappings."""
        assert "rag" in _SOURCE_HANDLERS
        assert "web" in _SOURCE_HANDLERS
        assert "db" in _SOURCE_HANDLERS
        assert _SOURCE_HANDLERS["rag"] == _query_rag
        assert _SOURCE_HANDLERS["web"] == _query_web
        assert _SOURCE_HANDLERS["db"] == _query_db


# ---------------------------------------------------------------------------
# Subagent registration
# ---------------------------------------------------------------------------

class TestKnowledgeBaseSubagent:
    """Tests for the Knowledge Base subagent registration."""

    def test_get_knowledge_base_subagent_returns_dict(self):
        """Test that get_knowledge_base_subagent returns a dict with required keys."""
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent

        mock_llm = MagicMock()
        subagent = get_knowledge_base_subagent(mock_llm)
        assert isinstance(subagent, dict)
        assert "name" in subagent
        assert "description" in subagent
        assert "runnable" in subagent

    def test_subagent_has_correct_name(self):
        """Test that subagent has the correct name."""
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent

        mock_llm = MagicMock()
        subagent = get_knowledge_base_subagent(mock_llm)
        assert subagent["name"] == "knowledge-base"

    def test_subagent_has_description(self):
        """Test that subagent has a description."""
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent

        mock_llm = MagicMock()
        subagent = get_knowledge_base_subagent(mock_llm)
        assert subagent["description"]
        assert len(subagent["description"]) > 0

    def test_subagent_description_mentions_knowledge(self):
        """Test that subagent description mentions knowledge sources."""
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent

        mock_llm = MagicMock()
        subagent = get_knowledge_base_subagent(mock_llm)
        desc_lower = subagent["description"].lower()
        assert "knowledge" in desc_lower or "source" in desc_lower

    def test_subagent_has_runnable(self):
        """Test that subagent has a runnable graph."""
        from app.agents.chat_assistant.subagents.knowledge_base_agent import get_knowledge_base_subagent

        mock_llm = MagicMock()
        subagent = get_knowledge_base_subagent(mock_llm)
        assert subagent["runnable"] is not None
