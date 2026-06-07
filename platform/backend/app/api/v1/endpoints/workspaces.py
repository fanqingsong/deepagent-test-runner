"""
Apps API Endpoints — LLM-APP-style test workspace.

Provides CRUD + run/refine/publish operations for test-as-APP workflow.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.app import (
    TestWorkspaceCreate,
    TestWorkspacePublishResponse,
    TestWorkspaceResponse,
    TestWorkspaceRunRequest,
    TestWorkspaceRunResponse,
    TestWorkspaceSummaryResponse,
    TestWorkspaceUpdate,
)
from app.services.app_service import AppService
from app.services.analytics_service import AnalyticsService
from app.core.security import get_current_user
from app.core.permissions import RequirePermission
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TestWorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_app(
    data: TestWorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("create:test-case")),
):
    svc = AppService(db)
    workspace = await svc.create_app(current_user.id, data.model_dump())
    return _build_response(workspace)


@router.get("/", response_model=List[TestWorkspaceSummaryResponse])
async def list_apps(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    svc = AppService(db)
    apps = await svc.list_apps(current_user.id, status=status_filter, search=search, skip=skip, limit=limit)
    return apps


@router.get("/marketplace", response_model=List[TestWorkspaceSummaryResponse])
async def list_published_apps(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch published test cases for marketplace display."""
    svc = AppService(db)
    apps = await svc.list_apps(
        user_id=None,
        status="published",
        search=search,
        skip=skip,
        limit=limit
    )
    return apps


@router.get("/{workspace_id}/published-versions")
async def get_published_versions(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all approved/published versions of an app for marketplace browsing."""
    svc = AppService(db)
    return await svc.get_published_versions(workspace_id)


@router.get("/{workspace_id}", response_model=TestWorkspaceResponse)
async def get_app(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    svc = AppService(db)

    # Sync run results if app is in testing state, with fallback
    try:
        workspace = await svc.sync_run_result(workspace_id)
    except Exception:
        logger.warning("sync_run_result failed for workspace %s, falling back to direct load", workspace_id, exc_info=True)
        workspace = await svc.get_app(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"TestWorkspace {workspace_id} not found")

    return _build_response(workspace)


@router.put("/{workspace_id}", response_model=TestWorkspaceResponse)
async def update_app(
    workspace_id: int,
    data: TestWorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    svc = AppService(db)
    workspace = await svc.update_app(workspace_id, data.model_dump(exclude_none=True))
    if not workspace:
        raise HTTPException(status_code=404, detail=f"TestWorkspace {workspace_id} not found")
    return _build_response(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_app(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("delete:test-case")),
):
    svc = AppService(db)
    workspace = await svc.archive_app(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"TestWorkspace {workspace_id} not found")


@router.post("/{workspace_id}/run", response_model=TestWorkspaceRunResponse)
async def run_app(
    workspace_id: int,
    data: TestWorkspaceRunRequest = TestWorkspaceRunRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("execute:test")),
):
    svc = AppService(db)
    try:
        result = await svc.run_app(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return TestWorkspaceRunResponse(**result)


@router.post("/{workspace_id}/publish", response_model=TestWorkspacePublishResponse)
async def publish_app(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    svc = AppService(db)
    try:
        result = await svc.publish_app(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return TestWorkspacePublishResponse(**result)


@router.post("/{workspace_id}/copy", response_model=TestWorkspaceResponse)
async def copy_app(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("create:test-case")),
):
    """Copy an existing app to create a new one in the user's workspace."""
    svc = AppService(db)
    try:
        workspace = await svc.copy_app(workspace_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _build_response(workspace)


@router.get("/{workspace_id}/runs")
async def get_app_runs(
    workspace_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    svc = AppService(db)
    workspace = await svc.get_app(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"TestWorkspace {workspace_id} not found")

    analytics_svc = AnalyticsService()
    runs = await analytics_svc.get_test_runs_for_app(
        db=db, app_id=workspace_id, limit=limit, offset=offset,
    )
    return runs


@router.get("/{workspace_id}/step-versions")
async def get_step_versions(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    svc = AppService(db)
    versions = await svc.get_step_versions(workspace_id)
    return versions


@router.post("/{workspace_id}/step-versions/{version_id}/restore")
async def restore_step_version(
    workspace_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    svc = AppService(db)
    try:
        result = await svc.restore_step_version(workspace_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{workspace_id}/step-versions/{version_id}/submit")
async def submit_version_for_review(
    workspace_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    svc = AppService(db)
    try:
        result = await svc.submit_version_for_review(workspace_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/{workspace_id}/create-draft", response_model=TestWorkspaceResponse)
async def create_draft_from_current(
    workspace_id: int,
    from_version_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    """
    Create a new draft version from current state or specific version.
    Used when switching from read-only to draft mode.
    """
    from app.models.test_version import TestVersion
    from app.models.test_definition import TestDefinition

    svc = AppService(db)

    # Get workspace
    workspace = await svc.get_app(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not workspace.test_definition_id:
        raise HTTPException(status_code=400, detail="Workspace has no test definition")

    # Get test definition
    td_stmt = select(TestDefinition).where(
        TestDefinition.id == workspace.test_definition_id
    )
    test_def = (await db.execute(td_stmt)).scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    # Check if draft already exists
    stmt = select(TestVersion).where(
        TestVersion.test_definition_id == test_def.id,
        TestVersion.review_status == "draft",
    ).order_by(TestVersion.id.desc()).limit(1)
    existing_draft = (await db.execute(stmt)).scalar_one_or_none()
    if existing_draft:
        return _build_response(workspace)

    # Create draft from specified version or current workspace state
    if from_version_id:
        # Load version and create draft from its snapshot
        ver_stmt = select(TestVersion).where(TestVersion.id == from_version_id)
        result = await db.execute(ver_stmt)
        version = result.scalar_one_or_none()
        if not version or version.test_definition_id != workspace.test_definition_id:
            raise HTTPException(status_code=404, detail="Version not found")
        snapshot = version.snapshot
        change_desc = f"New draft created from v{version.version}"
    else:
        # Build snapshot from current workspace state
        snapshot = await svc._build_snapshot(workspace, test_def)
        change_desc = "New draft created from current state"

    # Create new draft version with next version number
    next_version = test_def.version + 1
    draft = TestVersion(
        test_definition_id=workspace.test_definition_id,
        version=next_version,
        snapshot=snapshot,
        change_description=change_desc,
        review_status="draft",
        created_by=current_user.username if current_user else "system",
    )
    db.add(draft)
    await db.commit()

    return _build_response(workspace)


@router.get("/{workspace_id}/run-progress")
async def get_run_progress(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    svc = AppService(db)
    workspace = await svc.get_app(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"TestWorkspace {workspace_id} not found")

    if not workspace.latest_run_id:
        return {"status": "idle", "completed_steps": [], "current_step": 0, "total_steps": 0}

    from app.core.job_store import get_job
    job = get_job(workspace.latest_run_id)
    if not job:
        return {"status": "unknown", "completed_steps": [], "current_step": 0, "total_steps": 0}

    return {
        "status": job.get("status", "unknown"),
        "run_id": workspace.latest_run_id,
        "completed_steps": job.get("completed_steps", []),
        "current_step": job.get("current_step", 0),
        "total_steps": job.get("total_steps", 0),
        "browser_url": job.get("browser_url", ""),
        "browser_title": job.get("browser_title", ""),
    }


def _build_response(workspace) -> dict:
    messages = []
    if workspace.conversation_thread:
        messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_,
                "created_at": m.created_at,
            }
            for m in workspace.conversation_thread.messages
        ]

    review_status = None
    if workspace.test_definition:
        review_status = workspace.test_definition.review_status

    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "url": workspace.url,
        "status": workspace.status,
        "test_goal": workspace.test_goal,
        "test_context": workspace.test_context or {},
        "test_definition_id": workspace.test_definition_id,
        "latest_run_id": workspace.latest_run_id,
        "latest_result": workspace.latest_result or {},
        "iteration_count": workspace.iteration_count,
        "icon": workspace.icon,
        "color": workspace.color,
        "created_by": workspace.created_by,
        "created_at": workspace.created_at,
        "updated_at": workspace.updated_at,
        "review_status": review_status,
        "messages": messages,
    }
