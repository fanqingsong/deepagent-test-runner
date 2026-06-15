"""
Root cause service - orchestration.

Ties together the extractor, graph builder, causal analyzer and summarizer to
serve three operations used by the API:

- build_graph(db, days):   (re)build the Neo4j knowledge graph from PostgreSQL.
- analyze_run(db, run_id): local search + causal analysis for one failed run.
- analyze_global(db, days): global search over failure communities.
- get_run_graph(run_id):    nodes/edges JSON for frontend visualization.
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.causal_graphrag.causal_inference import CausalAnalyzer
from app.services.causal_graphrag.extractor import DataExtractor
from app.services.causal_graphrag.graph_builder import GraphBuilder
from app.services.causal_graphrag.neo4j_client import Neo4jClient
from app.services.causal_graphrag.summarizer import Summarizer

logger = logging.getLogger(__name__)


_RUN_SUBGRAPH_QUERY = """
MATCH (r:TestRun {run_id: $run_id})
OPTIONAL MATCH (r)-[:RAN]->(d:TestDefinition)
OPTIONAL MATCH (r)-[:HAS_RESULT]->(c:TestCaseResult)
OPTIONAL MATCH (c)-[:FAILED_WITH]->(e:ErrorPattern)
OPTIONAL MATCH (e)-[:INVOLVES]->(s:Selector)
OPTIONAL MATCH (d)-[:IN_ENV]->(env:Environment)
RETURN
  r.run_id AS run_id, r.status AS run_status,
  d.def_id AS def_id, d.name AS def_name,
  c.case_id AS case_id, c.test_id AS case_test_id,
  c.passed AS case_passed, c.error_category AS case_cat,
  e.signature AS err_sig, e.category AS err_cat, e.community AS err_comm,
  s.value AS selector,
  env.name AS env_name
"""

_RUN_COMMUNITY_QUERY = """
MATCH (r:TestRun {run_id: $run_id})-[:HAS_RESULT]->(:TestCaseResult)-[:FAILED_WITH]->(e:ErrorPattern)
WITH e.community AS community, count(*) AS cnt
WHERE community IS NOT NULL
RETURN community ORDER BY cnt DESC LIMIT 1
"""

_COMMUNITY_DETAIL_QUERY = """
MATCH (e:ErrorPattern {community: $community})
OPTIONAL MATCH (c:TestCaseResult)-[:FAILED_WITH]->(e)
OPTIONAL MATCH (e)-[:INVOLVES]->(s:Selector)
RETURN
  $community AS id,
  collect(DISTINCT e.category) AS categories,
  collect(DISTINCT e.signature)[..8] AS signatures,
  collect(DISTINCT s.value)[..8] AS selectors,
  count(DISTINCT c) AS failure_count,
  count(DISTINCT e) AS pattern_count
"""

_GLOBAL_COMMUNITIES_QUERY = """
MATCH (e:ErrorPattern)
WHERE e.community IS NOT NULL
OPTIONAL MATCH (c:TestCaseResult)-[:FAILED_WITH]->(e)
OPTIONAL MATCH (e)-[:INVOLVES]->(s:Selector)
WITH e.community AS community,
     collect(DISTINCT e.category) AS categories,
     collect(DISTINCT e.signature) AS signatures,
     collect(DISTINCT s.value) AS selectors,
     count(DISTINCT c) AS failure_count,
     count(DISTINCT e) AS pattern_count
RETURN community AS id, categories,
       signatures[..6] AS signatures,
       selectors[..6] AS selectors,
       failure_count, pattern_count
ORDER BY failure_count DESC
"""


def _dominant_label(categories: List[str]) -> str:
    cats = [c for c in (categories or []) if c and c != "None"]
    if not cats:
        return "Unknown"
    return Counter(cats).most_common(1)[0][0]


class RootCauseService:
    """Orchestrates GraphRAG + causal inference for failure root cause analysis."""

    def __init__(self, neo4j_client: Neo4jClient, llm_client: Any = None):
        self._client = neo4j_client
        self._extractor = DataExtractor()
        self._builder = GraphBuilder(neo4j_client)
        self._analyzer = CausalAnalyzer()
        self._summarizer = Summarizer(llm_client)

    async def health(self) -> Dict[str, Any]:
        connected = await self._client.verify_connectivity()
        return {"neo4j_connected": connected}

    async def build_graph(self, db: AsyncSession, days: Optional[int] = None) -> Dict[str, Any]:
        """Extract from PostgreSQL and (re)build the Neo4j graph."""
        df = await self._extractor.extract(db, days=days)
        if df.empty:
            return {"status": "empty", "message": "No test execution data found.", "stats": {}}
        stats = await self._builder.build(df, clear=True)
        return {"status": "ok", "stats": stats}

    async def analyze_run(self, db: AsyncSession, run_id: str) -> Dict[str, Any]:
        """Local search + causal analysis for a single run."""
        df = await self._extractor.extract(db, days=None)

        def_id = None
        if not df.empty:
            run_rows = df[df["run_id"] == run_id]
            if not run_rows.empty:
                def_id = int(run_rows.iloc[0]["def_id"]) if run_rows.iloc[0]["def_id"] is not None else None

        causal = self._analyzer.analyze(df, def_id)

        subgraph = await self.get_run_graph(run_id)
        community = await self._run_community(run_id)
        top_selectors = self._collect_selectors(subgraph)

        context = {
            "run_id": run_id,
            "def_id": def_id,
            "verdict": causal.get("verdict"),
            "overall_pass_rate": causal.get("overall_pass_rate"),
            "causal": causal,
            "community": community,
            "top_selectors": top_selectors,
        }

        summary = await self._summarizer.summarize_run(context)

        return {
            "run_id": run_id,
            "def_id": def_id,
            "verdict": causal.get("verdict"),
            "summary": summary,
            "causal": causal,
            "community": community,
            "top_selectors": top_selectors,
            "subgraph": subgraph,
        }

    async def analyze_global(self, db: AsyncSession, days: int = 7) -> Dict[str, Any]:
        """Global search over failure communities."""
        communities = await self._global_communities()
        for c in communities:
            c["label"] = _dominant_label(c.get("categories", []))
        summary = await self._summarizer.summarize_global(communities, days)
        return {
            "days": days,
            "community_count": len(communities),
            "communities": communities,
            "summary": summary,
        }

    async def get_run_graph(self, run_id: str) -> Dict[str, Any]:
        """Return nodes/edges JSON for the run's local subgraph."""
        try:
            rows = await self._client.run_query(_RUN_SUBGRAPH_QUERY, {"run_id": run_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_run_graph failed: %s", exc)
            return {"nodes": [], "edges": []}

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, str]] = []
        edge_set = set()

        def add_node(node_id: str, label: str, group: str, **extra):
            if node_id and node_id not in nodes:
                nodes[node_id] = {"id": node_id, "label": label, "group": group, **extra}

        def add_edge(src: str, dst: str, rel: str):
            if not src or not dst:
                return
            key = (src, dst, rel)
            if key not in edge_set:
                edge_set.add(key)
                edges.append({"source": src, "target": dst, "label": rel})

        for r in rows:
            run_node = f"run:{r['run_id']}"
            add_node(run_node, r["run_id"], "TestRun", status=r.get("run_status"))

            if r.get("def_id") is not None:
                def_node = f"def:{r['def_id']}"
                add_node(def_node, r.get("def_name") or f"def-{r['def_id']}", "TestDefinition")
                add_edge(run_node, def_node, "RAN")
                if r.get("env_name"):
                    env_node = f"env:{r['env_name']}"
                    add_node(env_node, r["env_name"], "Environment")
                    add_edge(def_node, env_node, "IN_ENV")

            if r.get("case_id") is not None:
                case_node = f"case:{r['case_id']}"
                add_node(
                    case_node,
                    r.get("case_test_id") or f"case-{r['case_id']}",
                    "TestCaseResult",
                    passed=r.get("case_passed"),
                )
                add_edge(run_node, case_node, "HAS_RESULT")

                if r.get("err_sig"):
                    err_node = f"err:{r['err_sig']}"
                    add_node(
                        err_node,
                        r.get("err_cat") or "Error",
                        "ErrorPattern",
                        community=r.get("err_comm"),
                        signature=r.get("err_sig"),
                    )
                    add_edge(case_node, err_node, "FAILED_WITH")
                    if r.get("selector"):
                        sel_node = f"sel:{r['selector']}"
                        add_node(sel_node, r["selector"], "Selector")
                        add_edge(err_node, sel_node, "INVOLVES")

        return {"nodes": list(nodes.values()), "edges": edges}

    async def _run_community(self, run_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = await self._client.run_query(_RUN_COMMUNITY_QUERY, {"run_id": run_id})
            if not rows:
                return None
            community_id = rows[0]["community"]
            detail = await self._client.run_query(
                _COMMUNITY_DETAIL_QUERY, {"community": community_id}
            )
            if not detail:
                return None
            d = detail[0]
            return {
                "id": d["id"],
                "label": _dominant_label(d.get("categories", [])),
                "categories": d.get("categories", []),
                "signatures": d.get("signatures", []),
                "selectors": d.get("selectors", []),
                "failure_count": d.get("failure_count", 0),
                "pattern_count": d.get("pattern_count", 0),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("_run_community failed: %s", exc)
            return None

    async def _global_communities(self) -> List[Dict[str, Any]]:
        try:
            rows = await self._client.run_query(_GLOBAL_COMMUNITIES_QUERY)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("_global_communities failed: %s", exc)
            return []

    @staticmethod
    def _collect_selectors(subgraph: Dict[str, Any]) -> List[str]:
        selectors = [
            n["label"] for n in subgraph.get("nodes", []) if n.get("group") == "Selector"
        ]
        return selectors[:8]
