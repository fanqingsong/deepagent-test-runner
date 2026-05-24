"""
RunConfig Service

CRUD operations for reusable execution configuration templates.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_config import RunConfig

logger = logging.getLogger(__name__)


class RunConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], created_by: str) -> RunConfig:
        config = RunConfig(**data, created_by=created_by)
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get(self, config_id: int) -> Optional[RunConfig]:
        result = await self.db.execute(
            select(RunConfig).where(RunConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[RunConfig]:
        result = await self.db.execute(
            select(RunConfig)
            .order_by(RunConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, config_id: int, data: Dict[str, Any]) -> Optional[RunConfig]:
        config = await self.get(config_id)
        if not config:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete(self, config_id: int) -> bool:
        config = await self.get(config_id)
        if not config:
            return False
        await self.db.delete(config)
        await self.db.commit()
        return True

    def merge_environment(
        self,
        base: Dict[str, Any],
        config_env: Dict[str, Any],
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Three-layer environment merge: base < config < overrides."""
        return {**base, **config_env, **overrides}
