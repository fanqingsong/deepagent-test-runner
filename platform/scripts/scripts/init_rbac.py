"""
Initialize RBAC system with default roles and permissions.

Run this script to create the initial roles and permissions for the system.
"""

import asyncio
from sys import path

path.append("..")

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.role import Permission, Role
from app.models.user import User


async def create_permissions():
    """Create default permissions."""
    permissions_data = [
        # User management permissions
        {"name": "create:user", "resource": "user", "action": "create", "description": "Create new users"},
        {"name": "read:user", "resource": "user", "action": "read", "description": "View users"},
        {"name": "update:user", "resource": "user", "action": "update", "description": "Update users"},
        {"name": "delete:user", "resource": "user", "action": "delete", "description": "Delete users"},

        # Test management permissions
        {"name": "create:test", "resource": "test", "action": "create", "description": "Create tests"},
        {"name": "read:test", "resource": "test", "action": "read", "description": "View tests"},
        {"name": "update:test", "resource": "test", "action": "update", "description": "Update tests"},
        {"name": "delete:test", "resource": "test", "action": "delete", "description": "Delete tests"},
        {"name": "execute:test", "resource": "test", "action": "execute", "description": "Execute tests"},

        # Schedule management permissions
        {"name": "create:schedule", "resource": "schedule", "action": "create", "description": "Create schedules"},
        {"name": "read:schedule", "resource": "schedule", "action": "read", "description": "View schedules"},
        {"name": "update:schedule", "resource": "schedule", "action": "update", "description": "Update schedules"},
        {"name": "delete:schedule", "resource": "schedule", "action": "delete", "description": "Delete schedules"},

        # Role management permissions
        {"name": "create:role", "resource": "role", "action": "create", "description": "Create roles"},
        {"name": "read:role", "resource": "role", "action": "read", "description": "View roles"},
        {"name": "update:role", "resource": "role", "action": "update", "description": "Update roles"},
        {"name": "delete:role", "resource": "role", "action": "delete", "description": "Delete roles"},
    ]

    async with async_session_maker() as session:
        for perm_data in permissions_data:
            result = await session.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                permission = Permission(**perm_data)
                session.add(permission)
                print(f"Created permission: {perm_data['name']}")

        await session.commit()
        print("✓ Permissions created successfully")


async def create_roles():
    """Create default roles with permissions."""
    async with async_session_maker() as session:
        # Get all permissions
        result = await session.execute(select(Permission))
        all_permissions = result.scalars().all()

        # Create Admin role (all permissions)
        admin_result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = admin_result.scalar_one_or_none()

        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrator with full system access",
                is_system=True
            )
            admin_role.permissions = all_permissions
            session.add(admin_role)
            print("Created role: admin (all permissions)")
        else:
            print("Role 'admin' already exists")

        # Create Tester role
        tester_permissions = [p for p in all_permissions if p.resource in ["test", "schedule"]]
        tester_result = await session.execute(select(Role).where(Role.name == "tester"))
        tester_role = tester_result.scalar_one_or_none()

        if not tester_role:
            tester_role = Role(
                name="tester",
                description="Tester role with test and schedule management",
                is_system=False
            )
            tester_role.permissions = tester_permissions
            session.add(tester_role)
            print("Created role: tester")
        else:
            print("Role 'tester' already exists")

        # Create Viewer role
        viewer_permissions = [p for p in all_permissions if p.action == "read"]
        viewer_result = await session.execute(select(Role).where(Role.name == "viewer"))
        viewer_role = viewer_result.scalar_one_or_none()

        if not viewer_role:
            viewer_role = Role(
                name="viewer",
                description="Viewer role with read-only access",
                is_system=False
            )
            viewer_role.permissions = viewer_permissions
            session.add(viewer_role)
            print("Created role: viewer")
        else:
            print("Role 'viewer' already exists")

        await session.commit()
        print("✓ Roles created successfully")


async def main():
    """Initialize RBAC system."""
    print("Initializing RBAC system...")
    print("-" * 50)

    await create_permissions()
    print()
    await create_roles()

    print("-" * 50)
    print("✓ RBAC initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())
