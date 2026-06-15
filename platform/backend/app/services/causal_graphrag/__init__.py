"""
Causal GraphRAG - Test Failure Root Cause Analysis (MVP)

A self-contained module that combines:
- GraphRAG: builds a knowledge graph of test executions in Neo4j and runs
  community detection to cluster similar failures ("failure communities").
- Causal inference: uses dowhy to distinguish script regressions, flaky tests,
  and environment-specific issues from mere correlations.
- LLM summarization: reuses the existing GLM client to produce natural-language
  root cause explanations.

This module is intentionally decoupled from the main execution pipeline and only
reads from the existing PostgreSQL tables (test_runs / test_cases /
test_definitions); it does not modify the relational schema.
"""

from app.services.causal_graphrag.neo4j_client import Neo4jClient
from app.services.causal_graphrag.root_cause_service import RootCauseService

__all__ = ["Neo4jClient", "RootCauseService"]
