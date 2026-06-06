"""
SQL Query Subagent — Specialized for querying the database with natural language.

Provides tools to explore database schema, generate SQL queries, validate them,
and return results. Read-only access only.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.sql_tools import (
    sql_db_list_tables,
    sql_db_schema,
    sql_db_query,
    sql_db_query_checker,
)


def create_sql_query_graph(llm):
    """Create the compiled graph for the SQL query subagent."""
    return create_agent(
        model=llm,
        tools=[sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker],
        system_prompt=(
            "You are a SQL expert specializing in querying a PostgreSQL database "
            "for an E2E testing platform. Your job is to translate natural-language "
            "questions into correct SQL queries and return the results.\n\n"
            "**Workflow:**\n"
            "1. ALWAYS start by calling sql_db_list_tables to see available tables.\n"
            "2. Use sql_db_schema to inspect relevant tables' columns and sample rows.\n"
            "3. Write a SQL query for the user's question.\n"
            "4. ALWAYS validate with sql_db_query_checker before executing.\n"
            "5. Execute the query with sql_db_query.\n"
            "6. Present the results clearly in natural language.\n\n"
            "**Rules:**\n"
            "- Only SELECT queries are allowed (no INSERT/UPDATE/DELETE/DROP).\n"
            "- Always limit results to at most 100 rows.\n"
            "- Only select relevant columns, never SELECT *.\n"
            "- If a query fails, fix it and retry.\n"
            "- Respond in the same language as the user's message.\n"
        ),
    )


def get_sql_query_subagent(llm):
    """Get the compiled SQL query subagent."""
    return CompiledSubAgent(
        name="sql-query",
        description=(
            "Query the application database (PostgreSQL) using natural language. "
            "Use this when the user asks about data in the database — test results, "
            "run counts, schedules, user statistics, analytics, or any question that "
            "requires SQL to answer. Generates, validates, and executes read-only SQL."
        ),
        runnable=create_sql_query_graph(llm),
    )
