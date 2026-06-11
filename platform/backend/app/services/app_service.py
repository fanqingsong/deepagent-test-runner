"""
App Service — orchestration layer for the LLM-APP-style test workspace.

Coordinates ExecutionService, conversation models, and
Temporal workflows to provide the generate → execute → refine/publish workflow.

Refactored into focused modules:
- AppWorkspaceCrud: create, get, list, update, archive, copy
- AppVersionService: version snapshots, history, restore
- AppExecutionService: run_app, publish_app, sync_run_result
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.test_workspace import TestWorkspace
from typing import Optional

# Import the split service modules
from app.services.app.app_workspace_crud import AppWorkspaceCrud
from app.services.app.app_version_service import AppVersionService
from app.services.app.app_execution_service import AppExecutionService


class AppService:
    """
    Facade for app workspace operations.

    Delegates to specialized service modules for better organization.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._crud = AppWorkspaceCrud(db)
        self._version = AppVersionService(db)
        self._execution = AppExecutionService(db)

    # ------------------------------------------------------------------
    # CRUD operations (delegated to AppWorkspaceCrud)
    # ------------------------------------------------------------------

    async def create_app(self, user_id: int, data: dict) -> TestWorkspace:
        return await self._crud.create_app(user_id, data)

    async def get_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        return await self._crud.get_app(workspace_id)

    async def list_apps(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list:
        return await self._crud.list_apps(user_id, status, search, skip, limit)

    async def update_app(self, workspace_id: int, data: dict) -> Optional[TestWorkspace]:
        return await self._crud.update_app(workspace_id, data)

    async def archive_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        return await self._crud.archive_app(workspace_id)

    async def copy_app(self, workspace_id: int, user_id: int) -> TestWorkspace:
        return await self._crud.copy_app(workspace_id, user_id)

    # ------------------------------------------------------------------
    # Version management (delegated to AppVersionService)
    # ------------------------------------------------------------------

    async def get_step_versions(self, app_id: int) -> list:
        return await self._version.get_step_versions(app_id)

    async def get_published_versions(self, app_id: int) -> list:
        return await self._version.get_published_versions(app_id)

    async def restore_step_version(self, app_id: int, version_id: int) -> dict:
        return await self._version.restore_step_version(app_id, version_id)

    async def submit_version_for_review(self, app_id: int, version_id: int) -> dict:
        return await self._version.submit_version_for_review(app_id, version_id)

    # ------------------------------------------------------------------
    # Execution and publishing (delegated to AppExecutionService)
    # ------------------------------------------------------------------

    async def run_app(self, app_id: int) -> dict:
        return await self._execution.run_app(app_id)

    async def publish_app(self, app_id: int) -> dict:
        return await self._execution.publish_app(app_id)

    async def sync_run_result(self, app_id: int) -> Optional[TestWorkspace]:
        return await self._execution.sync_run_result(app_id)
