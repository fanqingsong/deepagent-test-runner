"""
Idempotent RBAC seed for application startup.

Creates default roles and permissions if they don't exist.
Safe to run on every startup — only creates missing entries.
"""

import logging

from sqlalchemy import select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.role import Permission, Role, role_permissions

logger = logging.getLogger(__name__)

PERMISSIONS = [
    # User management
    {"name": "create:user", "resource": "user", "action": "create", "description": "Create new users"},
    {"name": "read:user", "resource": "user", "action": "read", "description": "View users"},
    {"name": "update:user", "resource": "user", "action": "update", "description": "Update users"},
    {"name": "delete:user", "resource": "user", "action": "delete", "description": "Delete users"},
    # Test management
    {"name": "create:test", "resource": "test", "action": "create", "description": "Create tests"},
    {"name": "read:test", "resource": "test", "action": "read", "description": "View tests"},
    {"name": "update:test", "resource": "test", "action": "update", "description": "Update tests"},
    {"name": "delete:test", "resource": "test", "action": "delete", "description": "Delete tests"},
    {"name": "execute:test", "resource": "test", "action": "execute", "description": "Execute tests"},
    # Schedule management
    {"name": "create:schedule", "resource": "schedule", "action": "create", "description": "Create schedules"},
    {"name": "read:schedule", "resource": "schedule", "action": "read", "description": "View schedules"},
    {"name": "update:schedule", "resource": "schedule", "action": "update", "description": "Update schedules"},
    {"name": "delete:schedule", "resource": "schedule", "action": "delete", "description": "Delete schedules"},
    # Role management
    {"name": "create:role", "resource": "role", "action": "create", "description": "Create roles"},
    {"name": "read:role", "resource": "role", "action": "read", "description": "View roles"},
    {"name": "update:role", "resource": "role", "action": "update", "description": "Update roles"},
    {"name": "delete:role", "resource": "role", "action": "delete", "description": "Delete roles"},
    # Job management
    {"name": "read:job", "resource": "job", "action": "read", "description": "View jobs"},
    {"name": "execute:job", "resource": "job", "action": "execute", "description": "Create and execute jobs"},
    {"name": "delete:job", "resource": "job", "action": "delete", "description": "Cancel/delete jobs"},
    # Analytics
    {"name": "read:analytics", "resource": "analytics", "action": "read", "description": "View analytics dashboard"},
    # Conversation
    {"name": "create:conversation", "resource": "conversation", "action": "create", "description": "Create conversations"},
    {"name": "read:conversation", "resource": "conversation", "action": "read", "description": "View conversations"},
    # Test suite
    {"name": "create:suite", "resource": "suite", "action": "create", "description": "Create test suites"},
    {"name": "read:suite", "resource": "suite", "action": "read", "description": "View test suites"},
    {"name": "update:suite", "resource": "suite", "action": "update", "description": "Update test suites"},
    {"name": "delete:suite", "resource": "suite", "action": "delete", "description": "Delete test suites"},
    # App workspace
    {"name": "create:app", "resource": "app", "action": "create", "description": "Create app workspaces"},
    {"name": "read:app", "resource": "app", "action": "read", "description": "View app workspaces"},
    {"name": "update:app", "resource": "app", "action": "update", "description": "Update app workspaces"},
    {"name": "delete:app", "resource": "app", "action": "delete", "description": "Delete app workspaces"},
    # Review/approval
    {"name": "review:test", "resource": "test", "action": "review", "description": "Review and approve/reject test definitions"},
    {"name": "review:suite", "resource": "suite", "action": "review", "description": "Review and approve/reject test suites"},
]

# Resources that testers can manage (everything except user/role admin)
TESTER_RESOURCES = {"test", "schedule", "job", "conversation", "suite", "app", "analytics"}

ROLES = {
    "admin": {
        "description": "Administrator with full system access",
        "is_system": True,
        "filter": lambda _perms: True,  # all permissions
    },
    "tester": {
        "description": "Tester with test, schedule, and job management",
        "is_system": True,
        "filter": lambda perms: perms.resource in TESTER_RESOURCES and perms.action != "review",
    },
    "viewer": {
        "description": "Read-only access across all resources",
        "is_system": True,
        "filter": lambda perms: perms.action == "read",
    },
}


async def _seed_permissions(session: AsyncSession) -> list[Permission]:
    """Create missing permissions, return all permissions."""
    created = 0
    for perm_data in PERMISSIONS:
        result = await session.execute(
            select(Permission).where(Permission.name == perm_data["name"])
        )
        if result.scalar_one_or_none() is None:
            session.add(Permission(**perm_data))
            created += 1

    await session.flush()

    result = await session.execute(select(Permission))
    all_perms = list(result.scalars().all())

    if created:
        logger.info("RBAC seed: created %d new permissions", created)
    return all_perms


async def _seed_roles(session: AsyncSession, all_perms: list[Permission]) -> None:
    """Create or update roles with their permission assignments."""
    for role_name, config in ROLES.items():
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()

        if role is None:
            role = Role(
                name=role_name,
                description=config["description"],
                is_system=config["is_system"],
            )
            session.add(role)
            await session.flush()
            logger.info("RBAC seed: created role '%s'", role_name)

        # Sync permissions via association table (avoids lazy-loading issues)
        if role.is_system:
            desired_ids = {p.id for p in all_perms if config["filter"](p)}

            result = await session.execute(
                select(role_permissions.c.permission_id)
                .where(role_permissions.c.role_id == role.id)
            )
            current_ids = {row[0] for row in result.fetchall()}

            if desired_ids != current_ids:
                await session.execute(
                    delete(role_permissions).where(role_permissions.c.role_id == role.id)
                )
                if desired_ids:
                    await session.execute(
                        insert(role_permissions),
                        [{"role_id": role.id, "permission_id": pid} for pid in desired_ids],
                    )
                logger.info("RBAC seed: synced permissions for role '%s'", role_name)


async def ensure_rbac_seeded() -> None:
    """Idempotent RBAC initialization. Safe to call on every startup."""
    try:
        async with async_session_maker() as session:
            all_perms = await _seed_permissions(session)
            await _seed_roles(session, all_perms)
            await session.commit()
            logger.info("RBAC seed: check complete")
    except Exception:
        logger.warning("RBAC seed: skipped (tables may not exist yet)", exc_info=True)
