"""
SQL Agent Tools — Database exploration tools for the SQL Agent.

Four tools following the LangChain SQL Agent pattern:
- sql_db_list_tables: List all tables in the database
- sql_db_schema: Get schema and sample rows for tables
- sql_db_query: Execute read-only SQL queries
- sql_db_query_checker: Validate SQL queries using LLM

All tools use sync_session_maker since LangGraph executes tool calls in
sync thread pools where async SQLAlchemy cannot run.
"""

import logging
import re

from langchain_core.tools import tool
from sqlalchemy import text

from app.core.agent_config import get_llm

logger = logging.getLogger(__name__)

_FORBIDDEN_KEYWORDS = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "COPY", "VACUUM",
})

MAX_RESULT_ROWS = 100
QUERY_TIMEOUT_SECONDS = 30


def _is_read_only(query: str) -> tuple[bool, str]:
    """Validate that a SQL query is read-only."""
    stripped = query.strip().upper()
    for kw in _FORBIDDEN_KEYWORDS:
        if kw in stripped.split():
            return False, f"DML/DDL keyword '{kw}' is not allowed. Only SELECT queries are permitted."
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return False, "Only SELECT or WITH (CTE) queries are allowed."
    return True, ""


def _ensure_limit(query: str) -> str:
    """Append LIMIT clause if not present."""
    if re.search(r"\bLIMIT\b", query, re.IGNORECASE):
        return query
    return f"{query.rstrip(';')} LIMIT {MAX_RESULT_ROWS};"


@tool
def sql_db_list_tables() -> str:
    """List all available tables in the database.
    Returns a comma-separated list of table names.
    Always call this tool first before querying any table."""
    from app.core.database import sync_session_maker

    db = sync_session_maker()
    try:
        result = db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
        )
        tables = [row[0] for row in result.fetchall()]
        return ", ".join(tables)
    finally:
        db.close()


@tool
def sql_db_schema(table_names: str) -> str:
    """Get the schema and sample rows for specified tables.
    Input is a comma-separated list of table names.
    Example Input: 'users, test_definitions'
    Always verify table names exist by calling sql_db_list_tables first!"""
    from app.core.database import sync_session_maker

    db = sync_session_maker()
    try:
        valid_result = db.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        )
        valid_tables = {row[0] for row in valid_result.fetchall()}

        results = []
        for table_name in table_names.split(","):
            table_name = table_name.strip()
            if table_name not in valid_tables:
                results.append(f"Error: table '{table_name}' not found in database")
                continue

            col_result = db.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = :table ORDER BY ordinal_position;"
                ),
                {"table": table_name},
            )
            columns = col_result.fetchall()

            schema_lines = [f'CREATE TABLE "{table_name}" (']
            col_defs = []
            col_names = []
            for col_name, data_type, is_nullable in columns:
                nullable = "" if is_nullable == "YES" else " NOT NULL"
                col_defs.append(f'  "{col_name}" {data_type}{nullable}')
                col_names.append(col_name)
            schema_lines.append(",\n".join(col_defs))
            schema_lines.append(");")
            results.append("\n".join(schema_lines))

            try:
                safe_name = table_name.replace('"', '""')
                sample_result = db.execute(
                    text(f'SELECT * FROM "{safe_name}" LIMIT 3;')
                )
                rows = sample_result.fetchall()
                if rows:
                    header = "\t".join(col_names)
                    row_lines = [
                        "\t".join(str(v) for v in row) for row in rows
                    ]
                    results.append(
                        f"/*\n3 rows from {table_name} table:\n{header}\n"
                        + "\n".join(row_lines)
                        + "\n*/"
                    )
            except Exception as e:
                results.append(f"Error fetching sample rows: {e}")

        return "\n\n".join(results)
    finally:
        db.close()


@tool
def sql_db_query(query: str) -> str:
    """Execute a SQL query against the PostgreSQL database and return results.
    Only SELECT queries are allowed. Results are limited to 100 rows.
    If the query is incorrect, an error message will be returned.
    Always use sql_db_query_checker before executing to verify correctness."""
    from app.core.database import sync_session_maker

    ok, msg = _is_read_only(query)
    if not ok:
        return f"Error: {msg}"

    query = _ensure_limit(query)

    db = sync_session_maker()
    try:
        # SECURITY FIX: Use parameterized query to prevent SQL injection
        db.execute(text("SET LOCAL statement_timeout :timeout"), {"timeout": f"{QUERY_TIMEOUT_SECONDS}s"})
        result = db.execute(text(query))
        rows = result.fetchall()

        if not rows:
            return "Query returned no results."

        col_names = list(result.keys())
        header = " | ".join(col_names)
        separator = "-+-".join("-" * len(c) for c in col_names)
        row_strs = [" | ".join(str(v) for v in row) for row in rows]

        if len(row_strs) > MAX_RESULT_ROWS:
            row_strs = row_strs[:MAX_RESULT_ROWS]
            row_strs.append(f"... ({len(rows)} total rows, showing first {MAX_RESULT_ROWS})")

        return f"{header}\n{separator}\n" + "\n".join(row_strs)
    except Exception as e:
        return f"Error: {e}"
    finally:
        db.rollback()
        db.close()


@tool
def sql_db_query_checker(query: str) -> str:
    """Use this tool to double-check if your SQL query is correct before executing it.
    Input is a SQL query string. Returns the corrected query or the original if no issues found.
    Always use this tool before executing a query with sql_db_query!"""
    checker_prompt = f"""{query}

Double check the PostgreSQL query above for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins
- PostgreSQL-specific syntax issues (e.g., using double quotes for identifiers, proper type casting with ::)

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

Output the final SQL query only.

SQL Query: """

    llm = get_llm(temperature=0.0, max_tokens=1024)
    response = llm.invoke(checker_prompt)
    return response.content.strip()
