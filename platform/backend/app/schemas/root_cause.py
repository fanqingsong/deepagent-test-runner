"""
Pydantic schemas for the Causal GraphRAG root cause analysis API.

Nested causal/graph payloads are intentionally typed as flexible dicts since
their shape is analysis-dependent; the top-level envelopes are typed for clear
OpenAPI docs.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    group: str
    community: Optional[int] = None
    passed: Optional[int] = None
    signature: Optional[str] = None
    status: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class SubGraph(BaseModel):
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class CommunityInfo(BaseModel):
    id: Optional[int] = None
    label: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    signatures: List[str] = Field(default_factory=list)
    selectors: List[str] = Field(default_factory=list)
    failure_count: int = 0
    pattern_count: int = 0


class BuildResponse(BaseModel):
    status: str
    message: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)


class RunAnalysisResponse(BaseModel):
    run_id: str
    def_id: Optional[int] = None
    verdict: Optional[str] = None
    summary: str = ""
    causal: Dict[str, Any] = Field(default_factory=dict)
    community: Optional[Dict[str, Any]] = None
    top_selectors: List[str] = Field(default_factory=list)
    subgraph: Dict[str, Any] = Field(default_factory=dict)


class GlobalAnalysisResponse(BaseModel):
    days: int
    community_count: int
    communities: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class HealthResponse(BaseModel):
    neo4j_connected: bool
