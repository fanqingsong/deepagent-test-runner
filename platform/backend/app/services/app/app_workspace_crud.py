"""
App Workspace CRUD Operations

Basic create, read, update, delete operations for TestWorkspace.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.test_workspace import TestWorkspace
from app.models.conversation import ConversationMessage, ConversationThread
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class AppWorkspaceCrud:
    """Handles basic CRUD operations for test workspaces."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_app(self, user_id: int, data: dict) -> TestWorkspace:
        """Create a new test workspace with conversation thread."""
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_workspace"},
        )
        self.db.add(thread)
        await self.db.flush()

        app = TestWorkspace(
            name=data.get("name") or "未命名测试",
            description=data.get("description"),
            url=data.get("url") or "",
            test_goal=data.get("test_goal") or "",
            test_context=data.get("test_context", {}),
            icon=data.get("icon", "test-tube"),
            color=data.get("color", "#0f62fe"),
            status="draft",
            created_by=user_id,
            conversation_thread_id=thread.id,
        )
        self.db.add(app)
        await self.db.flush()

        system_msg = ConversationMessage(
            thread_id=thread.id,
            role="system",
            content=f"Created APP: {app.name}\nTarget: {app.url}\nGoal: {app.test_goal}",
            metadata={"type": "app_created", "app_id": app.id},
        )
        self.db.add(system_msg)
        await self.db.commit()
        return await self.get_app(app.id)

    async def get_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        """Get a single workspace with eager-loaded relationships."""
        stmt = (
            select(TestWorkspace)
            .options(
                selectinload(TestWorkspace.conversation_thread).selectinload(
                    ConversationThread.messages
                ),
                selectinload(TestWorkspace.test_definition),
            )
            .where(TestWorkspace.id == workspace_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_apps(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        """List workspaces with filtering and pagination."""
        conditions = [TestWorkspace.status != "archived"]
        if user_id is not None:
            conditions.append(TestWorkspace.created_by == user_id)
        if status:
            status_list = [s.strip() for s in status.split(",")]
            conditions.append(TestWorkspace.status.in_(status_list))
        if search:
            conditions.append(TestWorkspace.name.ilike(f"%{search}%"))

        stmt = (
            select(TestWorkspace)
            .where(and_(*conditions))
            .order_by(TestWorkspace.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        workspaces = list(result.scalars().all())

        # For published items, fetch the latest published version number
        output = []
        for workspace in workspaces:
            workspace_dict = {
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
                "url": workspace.url,
                "status": workspace.status,
                "test_goal": workspace.test_goal,
                "icon": workspace.icon,
                "color": workspace.color,
                "iteration_count": workspace.iteration_count,
                "latest_result": workspace.latest_result or {},
                "created_at": workspace.created_at,
                "updated_at": workspace.updated_at,
            }

            # If this is a published marketplace item, get the latest published version
            if workspace.status == "published" and workspace.test_definition_id:
                from app.models.test_version import TestVersion
                ver_stmt = (
                    select(TestVersion)
                    .where(
                        TestVersion.test_definition_id == workspace.test_definition_id,
                        TestVersion.review_status == "published",
                    )
                    .order_by(TestVersion.version.desc())
                    .limit(1)
                )
                ver_result = await self.db.execute(ver_stmt)
                published_version = ver_result.scalar_one_or_none()
                if published_version:
                    workspace_dict["iteration_count"] = published_version.version

            output.append(workspace_dict)

        return output

    async def update_app(self, workspace_id: int, data: dict) -> Optional[TestWorkspace]:
        """Update workspace fields and sync to draft version snapshot."""
        app = await self.get_app(workspace_id)
        if not app:
            return None
        for key in ("name", "description", "url", "test_goal", "test_context", "icon", "color"):
            if key in data and data[key] is not None:
                setattr(app, key, data[key])

        # Sync config changes to the draft version snapshot
        if app.test_definition_id:
            from app.models.test_version import TestVersion
            stmt = (
                select(TestVersion)
                .where(
                    TestVersion.test_definition_id == app.test_definition_id,
                    TestVersion.review_status == "draft",
                )
                .order_by(TestVersion.id.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            draft_version = result.scalar_one_or_none()
            if draft_version:
                td_stmt = select(TestDefinition).where(
                    TestDefinition.id == app.test_definition_id
                )
                td_result = await self.db.execute(td_stmt)
                test_def = td_result.scalar_one_or_none()
                if test_def:
                    from app.services.app.app_version_service import AppVersionService
                    version_service = AppVersionService(self.db)
                    draft_version.snapshot = await version_service.build_snapshot(app, test_def)

        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def archive_app(self, workspace_id: int) -> Optional[TestWorkspace]:
        """Archive a workspace (soft delete)."""
        app = await self.get_app(workspace_id)
        if not app:
            return None
        app.status = "archived"
        await self.db.commit()
        return app

    async def copy_app(self, workspace_id: int, user_id: int) -> TestWorkspace:
        """Copy an existing app to create a new one for the user."""
        original = await self.get_app(workspace_id)
        if not original:
            raise ValueError(f"App {workspace_id} not found")

        # Create new conversation thread for the copy
        thread = ConversationThread(
            thread_type="planning",
            status="active",
            created_by=user_id,
            metadata={"source": "app_copy", "original_app_id": workspace_id},
        )
        self.db.add(thread)
        await self.db.flush()

        # Create the copy with modified metadata
        app = TestWorkspace(
            name=f"{original.name} (Copy)",
            description=original.description,
            url=original.url,
            test_goal=original.test_goal,
            test_context=original.test_context,
            icon=original.icon,
            color=original.color,
            status="draft",
            iteration_count=0,
            created_by=user_id,
            conversation_thread_id=thread.id,
        )
        self.db.add(app)
        await self.db.flush()

        # Add system message to the new thread
        system_msg = ConversationMessage(
            thread_id=thread.id,
            role="system",
            content=f"Copied from: {original.name}\nTarget: {app.url}\nGoal: {app.test_goal}",
            metadata={"type": "app_copied", "original_app_id": workspace_id, "app_id": app.id},
        )
        self.db.add(system_msg)

        # Copy test definition if exists
        if original.test_definition_id:
            original_test_def = await self.db.execute(
                select(TestDefinition).where(TestDefinition.id == original.test_definition_id)
            )
            original_test_def = original_test_def.scalar_one_or_none()

            if original_test_def:
                test_def = TestDefinition(
                    name=f"[APP] {app.name}",
                    description=app.description or app.test_goal,
                    test_id=f"app-{app.id}-{uuid.uuid4().hex[:8]}",
                    url=app.url,
                    test_goal=app.test_goal,
                    test_context=app.test_context,
                    environment={},
                    tags=["app-copied"],
                    is_active=True,
                    is_draft=True,
                    source_app_id=app.id,
                    created_by=user_id,
                )
                self.db.add(test_def)
                await self.db.flush()
                app.test_definition_id = test_def.id

        await self.db.commit()
        await self.db.refresh(app)
        return app
