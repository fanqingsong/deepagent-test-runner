"""
App Version Service

Manages test definition versioning, snapshots, and review workflow.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.test_workspace import TestWorkspace
from app.models.test_definition import TestDefinition

logger = logging.getLogger(__name__)


class AppVersionService:
    """Handles versioning and snapshot management for test workspaces."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_draft_test_definition(self, workspace: TestWorkspace) -> "TestDefinition":
        """Return the linked draft TestDefinition, creating one if needed."""
        test_def = None
        if workspace.test_definition_id:
            stmt = select(TestDefinition).where(
                TestDefinition.id == workspace.test_definition_id
            )
            result = await self.db.execute(stmt)
            test_def = result.scalar_one_or_none()

        if not test_def:
            test_def = TestDefinition(
                name=f"[APP] {workspace.name}",
                description=workspace.description or workspace.test_goal,
                test_id=f"app-{workspace.id}-{uuid.uuid4().hex[:8]}",
                url=workspace.url,
                test_goal=workspace.test_goal,
                test_context=workspace.test_context,
                environment={},
                tags=["app-generated"],
                is_active=True,
                is_draft=True,
                source_app_id=workspace.id,
                created_by=workspace.created_by,
            )
            self.db.add(test_def)
            await self.db.flush()
            workspace.test_definition_id = test_def.id
        else:
            test_def.test_goal = workspace.test_goal
            test_def.url = workspace.url

        await self.db.flush()
        return test_def

    async def build_snapshot(self, app: TestWorkspace, test_def: "TestDefinition") -> dict:
        """Build snapshot for version storage, including permissions."""
        from app.models.test_workspace_permission import TestWorkspacePermission
        from app.models.user import User

        # Load current permissions for this workspace
        stmt = select(TestWorkspacePermission, User).join(
            User, TestWorkspacePermission.user_id == User.id
        ).where(TestWorkspacePermission.workspace_id == app.id)
        result = await self.db.execute(stmt)
        permissions = [
            {
                "user_id": perm.user_id,
                "username": user.username,
                "email": user.email,
                "permission_type": perm.permission_type,
            }
            for perm, user in result.all()
        ]

        return {
            "name": app.name,
            "url": app.url,
            "test_goal": app.test_goal,
            "description": app.description,
            "test_context": app.test_context or {},
            "execution_mode": test_def.execution_mode,
            "script_status": test_def.script_status,
            "playwright_script": test_def.playwright_script,
            "script_metadata": test_def.script_metadata or {},
            "permissions": permissions,
        }

    async def apply_permissions_to_workspace(
        self, workspace_id: int, permissions: list
    ) -> None:
        """Apply permissions from snapshot to workspace permissions table."""
        from app.models.test_workspace_permission import TestWorkspacePermission

        # Clear existing permissions
        stmt = select(TestWorkspacePermission).where(
            TestWorkspacePermission.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().all()
        for perm in existing:
            await self.db.delete(perm)

        # Apply new permissions from snapshot
        for perm_data in permissions:
            perm = TestWorkspacePermission(
                workspace_id=workspace_id,
                user_id=perm_data["user_id"],
                permission_type=perm_data["permission_type"],
                granted_by=None,  # From version restore
            )
            self.db.add(perm)

        await self.db.flush()

    async def get_or_create_draft_version(
        self, workspace: TestWorkspace, test_def: "TestDefinition"
    ) -> "TestVersion":
        """Return the single active draft TestVersion, creating one if needed."""
        from app.models.test_version import TestVersion

        stmt = (
            select(TestVersion)
            .where(
                TestVersion.test_definition_id == test_def.id,
                TestVersion.review_status == "draft",
            )
            .order_by(TestVersion.id.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        draft = TestVersion(
            test_definition_id=test_def.id,
            version=0,  # Will be assigned next version number on submit
            snapshot=await self.build_snapshot(workspace, test_def),
            change_description="Initial draft",
            review_status="draft",
            created_by="system",
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def persist_steps(
        self, workspace: TestWorkspace, test_def: "TestDefinition", run_status: str = "", run_summary: str = ""
    ) -> int:
        """Update the existing draft version's snapshot in-place."""
        draft_version = await self.get_or_create_draft_version(workspace, test_def)
        draft_version.snapshot = await self.build_snapshot(workspace, test_def)
        draft_version.change_description = run_summary or "Draft updated"
        await self.db.flush()
        return 1

    async def get_step_versions(self, app_id: int) -> list:
        """Return version history for the app's test definition steps."""
        from app.models.test_version import TestVersion
        from app.services.app.app_workspace_crud import AppWorkspaceCrud

        crud = AppWorkspaceCrud(self.db)
        app = await crud.get_app(app_id)
        if not app or not app.test_definition_id:
            return []

        result = await self.db.execute(
            select(TestVersion)
            .where(TestVersion.test_definition_id == app.test_definition_id)
            .order_by(TestVersion.version.desc())
        )
        versions = result.scalars().all()

        out = []
        for v in versions:
            desc = v.change_description or ""
            run_status = ""
            if desc.lower().startswith("passed"):
                run_status = "passed"
            elif desc.lower().startswith("failed"):
                run_status = "failed"

            out.append({
                "id": v.id,
                "version": v.version,
                "snapshot": v.snapshot,
                "change_description": desc,
                "run_status": run_status,
                "review_status": v.review_status or "draft",
                "rejection_reason": v.rejection_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })
        return out

    async def get_published_versions(self, app_id: int) -> list:
        """Return all approved/published versions for marketplace browsing."""
        from app.models.test_version import TestVersion
        from app.services.app.app_workspace_crud import AppWorkspaceCrud

        crud = AppWorkspaceCrud(self.db)
        app = await crud.get_app(app_id)
        if not app or not app.test_definition_id:
            return []

        result = await self.db.execute(
            select(TestVersion)
            .where(
                TestVersion.test_definition_id == app.test_definition_id,
                TestVersion.review_status.in_(["approved", "published"]),
            )
            .order_by(TestVersion.version.desc())
        )
        versions = result.scalars().all()
        return [
            {
                "id": v.id,
                "version": v.version,
                "snapshot": v.snapshot,
                "change_description": v.change_description,
                "review_status": v.review_status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def restore_step_version(self, app_id: int, version_id: int) -> dict:
        """Restore steps from a previous version snapshot."""
        from app.models.test_version import TestVersion
        from app.services.app.app_workspace_crud import AppWorkspaceCrud

        crud = AppWorkspaceCrud(self.db)
        app = await crud.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")
        if not app.test_definition_id:
            raise ValueError("App has no test definition")

        td_stmt = select(TestDefinition).where(
            TestDefinition.id == app.test_definition_id
        )
        test_def = (await self.db.execute(td_stmt)).scalar_one_or_none()
        if not test_def:
            raise ValueError("Test definition not found")

        ver_stmt = select(TestVersion).where(
            TestVersion.id == version_id,
            TestVersion.test_definition_id == test_def.id,
        )
        version = (await self.db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        # Restore test definition data from snapshot
        snapshot = version.snapshot or {}
        if snapshot.get("test_goal"):
            test_def.test_goal = snapshot["test_goal"]
        if snapshot.get("url"):
            test_def.url = snapshot["url"]
        if snapshot.get("playwright_script"):
            test_def.playwright_script = snapshot["playwright_script"]
        if snapshot.get("script_metadata"):
            test_def.script_metadata = snapshot["script_metadata"]
        app.iteration_count += 1

        # Apply permissions from snapshot
        if "permissions" in snapshot:
            await self.apply_permissions_to_workspace(
                app.id, snapshot["permissions"]
            )

        count = await self.persist_steps(
            app, test_def, run_summary=f"Restored from v{version.version}"
        )
        await self.db.commit()

        return {
            "app_id": app.id,
            "restored_from_version": version.version,
            "steps_count": count,
        }

    async def submit_version_for_review(self, app_id: int, version_id: int) -> dict:
        """Submit an existing version for admin review."""
        from app.models.test_version import TestVersion
        from app.services.app.app_workspace_crud import AppWorkspaceCrud

        crud = AppWorkspaceCrud(self.db)
        app = await crud.get_app(app_id)
        if not app:
            raise ValueError(f"App {app_id} not found")
        if not app.test_definition_id:
            raise ValueError("App has no test definition")

        ver_stmt = select(TestVersion).where(
            TestVersion.id == version_id,
            TestVersion.test_definition_id == app.test_definition_id,
        )
        version = (await self.db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        if version.review_status not in ("draft", "rejected"):
            raise ValueError(f"Cannot submit version with status '{version.review_status}'")

        # Lock in version number on submit
        td_stmt = select(TestDefinition).where(
            TestDefinition.id == app.test_definition_id
        )
        test_def = (await self.db.execute(td_stmt)).scalar_one_or_none()
        if test_def and version.version == 0:
            # Legacy support: if draft still uses version=0, assign now
            test_def.version += 1
            version.version = test_def.version
        elif test_def and version.version > test_def.version:
            # Draft already has a version number, update test_definition.version to match
            test_def.version = version.version

        version.review_status = "pending_review"
        version.rejection_reason = None
        app.status = "pending_review"
        await self.db.commit()

        return {
            "app_id": app.id,
            "version_id": version.id,
            "version": version.version,
            "review_status": "pending_review",
        }
