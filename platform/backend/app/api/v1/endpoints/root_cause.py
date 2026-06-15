"""
Root Cause Analysis API (Causal GraphRAG)

Endpoints for building the failure knowledge graph and running GraphRAG +
causal-inference based root cause analysis.

Routes (mounted under /api/v1/analysis):
- POST /root-cause/build         (re)build the Neo4j graph from PostgreSQL
- GET  /root-cause/run/{run_id}  local search + causal analysis for one run
- GET  /root-cause/global        global search over failure communities
- GET  /root-cause/graph/{run_id} subgraph nodes/edges for visualization
- GET  /root-cause/health        Neo4j connectivity check
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import provide_root_cause_service
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.root_cause import (
    BuildResponse,
    GlobalAnalysisResponse,
    HealthResponse,
    RunAnalysisResponse,
)
from app.services.causal_graphrag.root_cause_service import RootCauseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/root-cause/health", response_model=HealthResponse)
async def root_cause_health(
    service: RootCauseService = Depends(provide_root_cause_service),
):
    """Check whether Neo4j is reachable."""
    return await service.health()


@router.post("/root-cause/build", response_model=BuildResponse)
async def build_graph(
    days: int = Query(90, ge=1, le=365, description="Look-back window for graph build"),
    current_user: User = Depends(get_current_user),
    service: RootCauseService = Depends(provide_root_cause_service),
    db: AsyncSession = Depends(get_db),
):
    """Extract test execution data and (re)build the Neo4j knowledge graph."""
    return await service.build_graph(db=db, days=days)


@router.get("/root-cause/run/{run_id}", response_model=RunAnalysisResponse)
async def analyze_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    service: RootCauseService = Depends(provide_root_cause_service),
    db: AsyncSession = Depends(get_db),
):
    """Local search + causal analysis explaining why a run failed."""
    return await service.analyze_run(db=db, run_id=run_id)


@router.get("/root-cause/global", response_model=GlobalAnalysisResponse)
async def analyze_global(
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    service: RootCauseService = Depends(provide_root_cause_service),
    db: AsyncSession = Depends(get_db),
):
    """Global search: summarize the dominant failure communities."""
    return await service.analyze_global(db=db, days=days)


@router.get("/root-cause/graph/{run_id}")
async def get_run_graph(
    run_id: str,
    current_user: User = Depends(get_current_user),
    service: RootCauseService = Depends(provide_root_cause_service),
):
    """Return the run's local subgraph as nodes/edges for visualization."""
    return await service.get_run_graph(run_id)
