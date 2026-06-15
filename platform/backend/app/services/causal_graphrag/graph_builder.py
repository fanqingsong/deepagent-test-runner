"""
Graph builder.

Writes the extracted test-execution DataFrame into Neo4j as a knowledge graph
and runs community detection (GDS Louvain) over the ErrorPattern co-occurrence
graph to cluster similar failures into "failure communities".

Graph model:
    (TestRun)-[:RAN]->(TestDefinition)
    (TestRun)-[:HAS_RESULT]->(TestCaseResult)
    (TestCaseResult)-[:FAILED_WITH]->(ErrorPattern)
    (ErrorPattern)-[:INVOLVES]->(Selector)
    (TestDefinition)-[:TARGETS]->(Url)
    (TestDefinition)-[:IN_ENV]->(Environment)
    (ErrorPattern)-[:CO_OCCURS_WITH {weight}]-(ErrorPattern)
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from app.services.causal_graphrag.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


_CONSTRAINTS = [
    "CREATE CONSTRAINT def_id IF NOT EXISTS FOR (d:TestDefinition) REQUIRE d.def_id IS UNIQUE",
    "CREATE CONSTRAINT run_id IF NOT EXISTS FOR (r:TestRun) REQUIRE r.run_id IS UNIQUE",
    "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:TestCaseResult) REQUIRE c.case_id IS UNIQUE",
    "CREATE CONSTRAINT err_sig IF NOT EXISTS FOR (e:ErrorPattern) REQUIRE e.signature IS UNIQUE",
    "CREATE CONSTRAINT sel_val IF NOT EXISTS FOR (s:Selector) REQUIRE s.value IS UNIQUE",
    "CREATE CONSTRAINT env_name IF NOT EXISTS FOR (e:Environment) REQUIRE e.name IS UNIQUE",
    "CREATE CONSTRAINT url_val IF NOT EXISTS FOR (u:Url) REQUIRE u.value IS UNIQUE",
]

# Structural part: definitions, runs, cases, env, url and their edges.
_STRUCTURE_QUERY = """
UNWIND $rows AS row
MERGE (d:TestDefinition {def_id: row.def_id})
  SET d.name = row.def_name,
      d.url = row.def_url,
      d.version = row.def_version,
      d.environment = row.environment,
      d.browser = row.browser
MERGE (r:TestRun {run_id: row.run_id})
  SET r.status = row.run_status,
      r.created_at = row.run_created_at
MERGE (c:TestCaseResult {case_id: row.case_id})
  SET c.test_id = row.case_test_id,
      c.status = row.status,
      c.passed = row.passed,
      c.duration = row.duration,
      c.screenshot_path = row.screenshot_path,
      c.error_category = row.error_category,
      c.run_id = row.run_id
MERGE (r)-[:RAN]->(d)
MERGE (r)-[:HAS_RESULT]->(c)
MERGE (env:Environment {name: row.environment})
MERGE (d)-[:IN_ENV]->(env)
FOREACH (_ IN CASE WHEN row.def_url <> '' THEN [1] ELSE [] END |
    MERGE (u:Url {value: row.def_url})
    MERGE (d)-[:TARGETS]->(u)
)
"""

# Failure part: error patterns, FAILED_WITH and selectors (failed rows only).
_FAILURE_QUERY = """
UNWIND $rows AS row
MATCH (c:TestCaseResult {case_id: row.case_id})
MERGE (e:ErrorPattern {signature: row.error_signature})
  SET e.category = row.error_category
MERGE (c)-[:FAILED_WITH]->(e)
FOREACH (sel IN row.selectors |
    MERGE (s:Selector {value: sel})
    MERGE (e)-[:INVOLVES]->(s)
)
"""

# Build co-occurrence edges between error patterns that fail in the same run.
_COOCCURRENCE_QUERY = """
MATCH (r:TestRun)-[:HAS_RESULT]->(:TestCaseResult)-[:FAILED_WITH]->(e:ErrorPattern)
WITH r, collect(DISTINCT e) AS errs
UNWIND errs AS e1
UNWIND errs AS e2
WITH e1, e2 WHERE elementId(e1) < elementId(e2)
MERGE (e1)-[c:CO_OCCURS_WITH]-(e2)
ON CREATE SET c.weight = 1
ON MATCH SET c.weight = coalesce(c.weight, 0) + 1
"""

# Self-loop so isolated error patterns still get projected by GDS.
_SELFLOOP_QUERY = """
MATCH (e:ErrorPattern)
WHERE NOT (e)-[:CO_OCCURS_WITH]-()
MERGE (e)-[c:CO_OCCURS_WITH]-(e)
ON CREATE SET c.weight = 1
"""


class GraphBuilder:
    """Persists the analysis DataFrame into Neo4j and detects communities."""

    def __init__(self, client: Neo4jClient):
        self._client = client

    async def ensure_constraints(self) -> None:
        for stmt in _CONSTRAINTS:
            try:
                await self._client.run_write(stmt)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Constraint skipped: %s (%s)", stmt, exc)

    async def clear(self) -> None:
        """Remove all causal-graphrag nodes for a clean rebuild."""
        await self._client.run_write(
            "MATCH (n) WHERE n:TestDefinition OR n:TestRun OR n:TestCaseResult "
            "OR n:ErrorPattern OR n:Selector OR n:Environment OR n:Url "
            "DETACH DELETE n"
        )

    def _to_rows(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for rec in df.to_dict(orient="records"):
            run_created = rec.get("run_created_at")
            rows.append(
                {
                    "def_id": int(rec["def_id"]) if pd.notna(rec.get("def_id")) else -1,
                    "def_name": str(rec.get("def_name") or "unknown"),
                    "def_url": str(rec.get("def_url") or ""),
                    "def_version": int(rec.get("def_version") or 1),
                    "environment": str(rec.get("environment") or "default"),
                    "browser": str(rec.get("browser") or "chromium"),
                    "run_id": str(rec.get("run_id")),
                    "run_status": str(rec.get("run_status") or "unknown"),
                    "run_created_at": run_created.isoformat() if hasattr(run_created, "isoformat") else str(run_created or ""),
                    "case_id": int(rec["case_id"]),
                    "case_test_id": str(rec.get("case_test_id") or ""),
                    "status": str(rec.get("status") or ""),
                    "passed": int(rec.get("passed") or 0),
                    "duration": int(rec.get("duration") or 0),
                    "screenshot_path": rec.get("screenshot_path") or "",
                    "error_category": str(rec.get("error_category") or "None"),
                    "error_signature": str(rec.get("error_signature") or "None"),
                    "selectors": list(rec.get("selectors") or []),
                }
            )
        return rows

    async def build(self, df: pd.DataFrame, clear: bool = True, batch_size: int = 500) -> Dict[str, Any]:
        """
        Build the full graph from the DataFrame.

        Returns a small stats dict describing what was written.
        """
        if df is None or df.empty:
            return {"nodes_written": 0, "failed_cases": 0, "communities": 0}

        await self.ensure_constraints()
        if clear:
            await self.clear()

        rows = self._to_rows(df)

        # Structure (all rows).
        for i in range(0, len(rows), batch_size):
            await self._client.run_batch(_STRUCTURE_QUERY, rows[i : i + batch_size])

        # Failures only.
        failed_rows = [r for r in rows if r["error_signature"] != "None"]
        for i in range(0, len(failed_rows), batch_size):
            await self._client.run_batch(_FAILURE_QUERY, failed_rows[i : i + batch_size])

        # Co-occurrence edges + self loops so every pattern is projectable.
        await self._client.run_write(_COOCCURRENCE_QUERY)
        await self._client.run_write(_SELFLOOP_QUERY)

        communities = await self.detect_communities()

        return {
            "nodes_written": len(rows),
            "failed_cases": len(failed_rows),
            "communities": communities,
        }

    async def detect_communities(self) -> int:
        """
        Run GDS Louvain community detection over the ErrorPattern co-occurrence
        graph, writing the `community` property back to each node.

        Falls back to grouping by category if GDS is unavailable.

        Returns the number of distinct communities detected.
        """
        graph_name = "errGraph"
        try:
            # Drop any stale projection.
            await self._client.run_query(
                "CALL gds.graph.exists($name) YIELD exists "
                "WITH exists WHERE exists "
                "CALL gds.graph.drop($name) YIELD graphName RETURN graphName",
                {"name": graph_name},
            )
            await self._client.run_query(
                "CALL gds.graph.project($name, 'ErrorPattern', "
                "{CO_OCCURS_WITH: {orientation: 'UNDIRECTED', properties: 'weight'}}) "
                "YIELD graphName RETURN graphName",
                {"name": graph_name},
            )
            await self._client.run_query(
                "CALL gds.louvain.write($name, "
                "{writeProperty: 'community', relationshipWeightProperty: 'weight'}) "
                "YIELD communityCount RETURN communityCount",
                {"name": graph_name},
            )
            await self._client.run_query(
                "CALL gds.graph.drop($name) YIELD graphName RETURN graphName",
                {"name": graph_name},
            )
            rows = await self._client.run_query(
                "MATCH (e:ErrorPattern) RETURN count(DISTINCT e.community) AS c"
            )
            count = rows[0]["c"] if rows else 0
            logger.info("GDS Louvain detected %d communities", count)
            return int(count)
        except Exception as exc:  # noqa: BLE001 - fall back gracefully
            logger.warning("GDS Louvain unavailable (%s); falling back to category grouping", exc)
            await self._client.run_write(
                "MATCH (e:ErrorPattern) "
                "WITH e, e.category AS cat "
                "WITH collect(DISTINCT cat) AS cats "
                "UNWIND range(0, size(cats)-1) AS idx "
                "MATCH (e:ErrorPattern {category: cats[idx]}) "
                "SET e.community = idx"
            )
            rows = await self._client.run_query(
                "MATCH (e:ErrorPattern) RETURN count(DISTINCT e.community) AS c"
            )
            return int(rows[0]["c"]) if rows else 0
