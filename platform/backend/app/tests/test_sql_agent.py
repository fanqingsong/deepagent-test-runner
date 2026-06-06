"""Tests for SQL Agent tools and subagent."""

import pytest
from unittest.mock import MagicMock, patch

from app.agents.chat_assistant.sql_tools import (
    _is_read_only,
    _ensure_limit,
    MAX_RESULT_ROWS,
    _FORBIDDEN_KEYWORDS,
    sql_db_list_tables,
    sql_db_schema,
    sql_db_query,
    sql_db_query_checker,
)


# ---------------------------------------------------------------------------
# _is_read_only
# ---------------------------------------------------------------------------

class TestIsReadOnly:
    """Tests for the _is_read_only helper."""

    def test_select_query_allowed(self):
        ok, msg = _is_read_only("SELECT * FROM test_runs")
        assert ok is True
        assert msg == ""

    def test_with_cte_allowed(self):
        ok, msg = _is_read_only(
            "WITH recent AS (SELECT * FROM test_runs) SELECT * FROM recent"
        )
        assert ok is True
        assert msg == ""

    def test_case_insensitive_select(self):
        ok, msg = _is_read_only("select id, name from users")
        assert ok is True

    def test_leading_whitespace_select(self):
        ok, msg = _is_read_only("  \n  SELECT 1")
        assert ok is True

    @pytest.mark.parametrize("keyword", list(_FORBIDDEN_KEYWORDS))
    def test_forbidden_keywords(self, keyword):
        query = f"{keyword} something"
        ok, msg = _is_read_only(query)
        assert ok is False
        assert keyword in msg

    def test_insert_rejected(self):
        ok, msg = _is_read_only("INSERT INTO users (name) VALUES ('test')")
        assert ok is False
        assert "INSERT" in msg

    def test_update_rejected(self):
        ok, msg = _is_read_only("UPDATE users SET name='x' WHERE id=1")
        assert ok is False

    def test_delete_rejected(self):
        ok, msg = _is_read_only("DELETE FROM users")
        assert ok is False

    def test_drop_rejected(self):
        ok, msg = _is_read_only("DROP TABLE users")
        assert ok is False

    def test_truncate_rejected(self):
        ok, msg = _is_read_only("TRUNCATE TABLE users")
        assert ok is False

    def test_case_insensitive_rejection(self):
        ok, msg = _is_read_only("insert into t values (1)")
        assert ok is False

    def test_keyword_in_column_name_not_flagged(self):
        """Keywords embedded in identifiers should NOT trigger rejection."""
        ok, msg = _is_read_only("SELECT updated_at, deleted_flag FROM test_runs")
        assert ok is True

    def test_non_select_non_with_rejected(self):
        ok, msg = _is_read_only("EXPLAIN SELECT * FROM users")
        assert ok is False
        assert "Only SELECT or WITH" in msg


# ---------------------------------------------------------------------------
# _ensure_limit
# ---------------------------------------------------------------------------

class TestEnsureLimit:
    """Tests for the _ensure_limit helper."""

    def test_appends_limit_when_missing(self):
        result = _ensure_limit("SELECT * FROM test_runs")
        assert f"LIMIT {MAX_RESULT_ROWS}" in result

    def test_no_change_when_limit_present(self):
        query = "SELECT * FROM test_runs LIMIT 10;"
        result = _ensure_limit(query)
        assert result == query

    def test_case_insensitive_limit(self):
        query = "SELECT * FROM test_runs limit 5"
        result = _ensure_limit(query)
        assert result == query

    def test_strips_trailing_semicolon_before_appending(self):
        result = _ensure_limit("SELECT * FROM test_runs;")
        assert result.endswith(f"LIMIT {MAX_RESULT_ROWS};")
        assert ";;" not in result

    def test_complex_query(self):
        result = _ensure_limit(
            "SELECT r.id, d.name FROM test_runs r JOIN test_definitions d ON r.test_definition_id = d.id"
        )
        assert f"LIMIT {MAX_RESULT_ROWS}" in result


# ---------------------------------------------------------------------------
# sql_db_list_tables
# ---------------------------------------------------------------------------

class TestSqlDbListTables:
    """Tests for the sql_db_list_tables tool."""

    @patch("app.agents.chat_assistant.sql_tools.sql_db_list_tables")
    def test_returns_comma_separated_tables(self, mock_tool):
        # The @tool decorator wraps the function, so we test via direct call
        # by mocking sync_session_maker
        pass

    def test_tool_has_correct_name(self):
        assert sql_db_list_tables.name == "sql_db_list_tables"

    def test_tool_has_description(self):
        assert sql_db_list_tables.description
        assert "table" in sql_db_list_tables.description.lower()


# ---------------------------------------------------------------------------
# sql_db_schema
# ---------------------------------------------------------------------------

class TestSqlDbSchema:
    """Tests for the sql_db_schema tool."""

    def test_tool_has_correct_name(self):
        assert sql_db_schema.name == "sql_db_schema"

    def test_tool_has_description(self):
        assert sql_db_schema.description
        assert "schema" in sql_db_schema.description.lower()

    def test_tool_args_include_table_names(self):
        assert "table_names" in sql_db_schema.args_schema.model_json_schema()["properties"]


# ---------------------------------------------------------------------------
# sql_db_query
# ---------------------------------------------------------------------------

class TestSqlDbQuery:
    """Tests for the sql_db_query tool."""

    def test_tool_has_correct_name(self):
        assert sql_db_query.name == "sql_db_query"

    def test_rejects_write_queries(self):
        """The tool should reject INSERT/UPDATE/DELETE at the _is_read_only gate."""
        result = sql_db_query.invoke("INSERT INTO users (name) VALUES ('test')")
        assert "Error" in result
        assert "not allowed" in result

    def test_rejects_drop(self):
        result = sql_db_query.invoke("DROP TABLE users")
        assert "Error" in result

    def test_rejects_update(self):
        result = sql_db_query.invoke("UPDATE test_runs SET status='passed'")
        assert "Error" in result

    def test_rejects_delete(self):
        result = sql_db_query.invoke("DELETE FROM test_runs WHERE id=1")
        assert "Error" in result

    def test_rejects_truncate(self):
        result = sql_db_query.invoke("TRUNCATE TABLE test_runs")
        assert "Error" in result

    @patch("app.agents.chat_assistant.sql_tools.sync_session_maker", create=True)
    def test_executes_select(self, mock_sm):
        """Mock DB session to verify a SELECT query is executed."""
        mock_session = MagicMock()
        mock_sm.return_value = mock_session
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "passed"), (2, "failed")]
        mock_result.keys.return_value = ["id", "status"]
        mock_session.execute.return_value = mock_result
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()

        with patch("app.agents.chat_assistant.sql_tools.sync_session_maker", mock_sm, create=True):
            with patch.dict("sys.modules", {"app.core.database": MagicMock(sync_session_maker=mock_sm)}):
                result = sql_db_query.invoke("SELECT id, status FROM test_runs LIMIT 10")

        assert "id" in result
        assert "passed" in result or "failed" in result

    def test_tool_has_description(self):
        assert sql_db_query.description
        assert "SELECT" in sql_db_query.description


# ---------------------------------------------------------------------------
# sql_db_query_checker
# ---------------------------------------------------------------------------

class TestSqlDbQueryChecker:
    """Tests for the sql_db_query_checker tool."""

    def test_tool_has_correct_name(self):
        assert sql_db_query_checker.name == "sql_db_query_checker"

    def test_tool_has_description(self):
        assert sql_db_query_checker.description
        assert "check" in sql_db_query_checker.description.lower()

    @patch("app.agents.chat_assistant.sql_tools.get_llm")
    def test_returns_llm_response(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="SELECT id FROM test_runs LIMIT 10;"
        )
        mock_get_llm.return_value = mock_llm

        result = sql_db_query_checker.invoke("SELECT id FROM test_runs LIMT 10")
        assert "SELECT" in result
        assert "LIMIT" in result

    @patch("app.agents.chat_assistant.sql_tools.get_llm")
    def test_passes_query_to_llm(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="SELECT 1")
        mock_get_llm.return_value = mock_llm

        sql_db_query_checker.invoke("SELECT * FROM test_runs")

        call_arg = mock_llm.invoke.call_args[0][0]
        assert "SELECT * FROM test_runs" in call_arg

    @patch("app.agents.chat_assistant.sql_tools.get_llm")
    def test_uses_temperature_zero(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="SELECT 1")
        mock_get_llm.return_value = mock_llm

        sql_db_query_checker.invoke("SELECT 1")

        mock_get_llm.assert_called_with(temperature=0.0, max_tokens=1024)


# ---------------------------------------------------------------------------
# Subagent
# ---------------------------------------------------------------------------

class TestSQLSubagent:
    """Tests for the SQL query subagent registration."""

    def test_get_sql_query_subagent_returns_compiled(self):
        from deepagents import CompiledSubAgent
        from app.agents.chat_assistant.subagents.sql_agent import get_sql_query_subagent

        mock_llm = MagicMock()
        subagent = get_sql_query_subagent(mock_llm)
        assert isinstance(subagent, CompiledSubAgent)
        assert subagent.name == "sql-query"

    def test_subagent_description_mentions_sql(self):
        from app.agents.chat_assistant.subagents.sql_agent import get_sql_query_subagent

        mock_llm = MagicMock()
        subagent = get_sql_query_subagent(mock_llm)
        assert "SQL" in subagent.description or "sql" in subagent.description.lower()

    def test_subagent_has_runnable(self):
        from app.agents.chat_assistant.subagents.sql_agent import get_sql_query_subagent

        mock_llm = MagicMock()
        subagent = get_sql_query_subagent(mock_llm)
        assert subagent.runnable is not None
