"""
RunConfig API Endpoints

CRUD for reusable execution configuration templates.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.run_configs import RunConfigCreate, RunConfigResponse, RunConfigUpdate
from app.services.run_config_service import RunConfigService

router = APIRouter()


@router.post("/", response_model=RunConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_run_config(
    data: RunConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = RunConfigService(db)
    config = await svc.create(data.model_dump(), created_by=str(current_user.id))
    return config


@router.get("/", response_model=List[RunConfigResponse])
async def list_run_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = RunConfigService(db)
    return await svc.list_all(skip=skip, limit=limit)


@router.get("/{config_id}", response_model=RunConfigResponse)
async def get_run_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = RunConfigService(db)
    config = await svc.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"RunConfig {config_id} not found")
    return config


@router.put("/{config_id}", response_model=RunConfigResponse)
async def update_run_config(
    config_id: int,
    data: RunConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = RunConfigService(db)
    config = await svc.update(config_id, data.model_dump(exclude_unset=True))
    if not config:
        raise HTTPException(status_code=404, detail=f"RunConfig {config_id} not found")
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = RunConfigService(db)
    if not await svc.delete(config_id):
        raise HTTPException(status_code=404, detail=f"RunConfig {config_id} not found")
    return None
