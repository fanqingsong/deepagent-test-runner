"""
Suite Permission Service — manages test suite access control.
"""

from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite_permission import TestSuitePermission
from app.models.user import User


VALID_PERMISSION_TYPES = {"view", "edit", "execute", "admin"}


class SuitePermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_permissions(self, test_suite_id: int) -> list[dict]:
        stmt = (
            select(TestSuitePermission, User)
            .join(User, TestSuitePermission.user_id == User.id)
            .where(TestSuitePermission.test_suite_id == test_suite_id)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": perm.id,
                "test_suite_id": perm.test_suite_id,
                "user_id": perm.user_id,
                "username": user.username,
                "email": user.email,
                "permission_type": perm.permission_type,
                "granted_by": perm.granted_by,
                "created_at": perm.created_at.isoformat() if perm.created_at else None,
            }
            for perm, user in rows
        ]

    async def add_permission(
        self, test_suite_id: int, user_id: int, permission_type: str, granted_by: Optional[int] = None
    ) -> dict:
        if permission_type not in VALID_PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        stmt = select(TestSuitePermission).where(
            and_(
                TestSuitePermission.test_suite_id == test_suite_id,
                TestSuitePermission.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.permission_type = permission_type
            existing.granted_by = granted_by
            await self.db.flush()
            return self._to_dict(existing)

        perm = TestSuitePermission(
            test_suite_id=test_suite_id,
            user_id=user_id,
            permission_type=permission_type,
            granted_by=granted_by,
        )
        self.db.add(perm)
        await self.db.flush()
        return self._to_dict(perm)

    async def update_permission(
        self, test_suite_id: int, user_id: int, permission_type: str
    ) -> Optional[dict]:
        if permission_type not in VALID_PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        stmt = select(TestSuitePermission).where(
            and_(
                TestSuitePermission.test_suite_id == test_suite_id,
                TestSuitePermission.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            return None
        perm.permission_type = permission_type
        await self.db.flush()
        return self._to_dict(perm)

    async def remove_permission(self, test_suite_id: int, user_id: int) -> bool:
        stmt = select(TestSuitePermission).where(
            and_(
                TestSuitePermission.test_suite_id == test_suite_id,
                TestSuitePermission.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            return False
        await self.db.delete(perm)
        await self.db.flush()
        return True

    def _to_dict(self, perm: TestSuitePermission) -> dict:
        return {
            "id": perm.id,
            "test_suite_id": perm.test_suite_id,
            "user_id": perm.user_id,
            "permission_type": perm.permission_type,
            "granted_by": perm.granted_by,
            "created_at": perm.created_at.isoformat() if perm.created_at else None,
        }
