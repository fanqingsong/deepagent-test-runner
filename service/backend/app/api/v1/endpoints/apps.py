"""
Apps API Endpoints — LLM-APP-style test workspace.

Provides CRUD + run/refine/publish operations for test-as-APP workflow.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.app import (
    AppCreate,
    AppPlanResponse,
    AppPublishResponse,
    AppRefineRequest,
    AppResponse,
    AppRunRequest,
    AppRunResponse,
    AppSaveStepsResponse,
    AppSummaryResponse,
    AppUpdate,
)
from app.services.app_service import AppService
from app.services.analytics_service import AnalyticsService
from app.core.security import get_current_user
from app.core.permissions import RequirePermission
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def create_app(
    data: AppCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("create:app")),
):
    svc = AppService(db)
    app = await svc.create_app(current_user.id, data.model_dump())
    return _build_response(app)


@router.get("/", response_model=List[AppSummaryResponse])
async def list_apps(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:app")),
):
    svc = AppService(db)
    apps = await svc.list_apps(current_user.id, status=status_filter, search=search, skip=skip, limit=limit)
    return apps


@router.get("/marketplace", response_model=List[AppSummaryResponse])
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
        current_user.id,
        status="published",
        search=search,
        skip=skip,
        limit=limit
    )
    return apps


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:app")),
):
    svc = AppService(db)

    # Sync run results if app is in testing state, with fallback
    try:
        app = await svc.sync_run_result(app_id)
    except Exception:
        logger.warning("sync_run_result failed for app %s, falling back to direct load", app_id, exc_info=True)
        app = await svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    return _build_response(app)


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: int,
    data: AppUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    app = await svc.update_app(app_id, data.model_dump(exclude_none=True))
    if not app:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")
    return _build_response(app)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("delete:app")),
):
    svc = AppService(db)
    app = await svc.archive_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")


@router.post("/{app_id}/generate-plan", response_model=AppPlanResponse)
async def generate_plan(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.generate_plan_only(app_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AppPlanResponse(**result)


@router.post("/{app_id}/save-steps", response_model=AppSaveStepsResponse)
async def save_steps(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.save_steps_to_db(app_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AppSaveStepsResponse(**result)


@router.post("/{app_id}/run", response_model=AppRunResponse)
async def run_app(
    app_id: int,
    data: AppRunRequest = AppRunRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("execute:test")),
):
    svc = AppService(db)
    try:
        result = await svc.run_app(app_id, force_regenerate=data.force_regenerate, use_existing_plan=data.use_existing_plan)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AppRunResponse(**result)


@router.post("/{app_id}/refine")
async def refine_app(
    app_id: int,
    data: AppRefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.refine_app(app_id, data.feedback)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{app_id}/publish", response_model=AppPublishResponse)
async def publish_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.publish_app(app_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AppPublishResponse(**result)


@router.post("/{app_id}/copy", response_model=AppResponse)
async def copy_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("create:app")),
):
    """Copy an existing app to create a new one in the user's workspace."""
    svc = AppService(db)
    try:
        app = await svc.copy_app(app_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _build_response(app)


@router.get("/{app_id}/runs")
async def get_app_runs(
    app_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:app")),
):
    svc = AppService(db)
    app = await svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    analytics_svc = AnalyticsService()
    runs = await analytics_svc.get_test_runs_for_app(
        db=db, app_id=app_id, limit=limit, offset=offset,
    )
    return runs


@router.get("/{app_id}/step-versions")
async def get_step_versions(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:app")),
):
    svc = AppService(db)
    versions = await svc.get_step_versions(app_id)
    return versions


@router.post("/{app_id}/step-versions/{version_id}/restore")
async def restore_step_version(
    app_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.restore_step_version(app_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{app_id}/step-versions/{version_id}/submit")
async def submit_version_for_review(
    app_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:app")),
):
    svc = AppService(db)
    try:
        result = await svc.submit_version_for_review(app_id, version_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/{app_id}/run-progress")
async def get_run_progress(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:app")),
):
    svc = AppService(db)
    app = await svc.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"App {app_id} not found")

    if not app.latest_run_id:
        return {"status": "idle", "completed_steps": [], "current_step": 0, "total_steps": 0}

    from app.core.job_store import get_job
    job = get_job(app.latest_run_id)
    if not job:
        return {"status": "unknown", "completed_steps": [], "current_step": 0, "total_steps": 0}

    return {
        "status": job.get("status", "unknown"),
        "run_id": app.latest_run_id,
        "completed_steps": job.get("completed_steps", []),
        "current_step": job.get("current_step", 0),
        "total_steps": job.get("total_steps", 0),
        "browser_url": job.get("browser_url", ""),
        "browser_title": job.get("browser_title", ""),
    }


def _build_response(app) -> dict:
    messages = []
    if app.conversation_thread:
        messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_,
                "created_at": m.created_at,
            }
            for m in app.conversation_thread.messages
        ]

    review_status = None
    if app.test_definition:
        review_status = app.test_definition.review_status

    return {
        "id": app.id,
        "name": app.name,
        "description": app.description,
        "url": app.url,
        "status": app.status,
        "test_goal": app.test_goal,
        "test_context": app.test_context or {},
        "current_plan": app.current_plan or {},
        "test_definition_id": app.test_definition_id,
        "latest_run_id": app.latest_run_id,
        "latest_result": app.latest_result or {},
        "iteration_count": app.iteration_count,
        "icon": app.icon,
        "color": app.color,
        "created_by": app.created_by,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "review_status": review_status,
        "messages": messages,
    }
