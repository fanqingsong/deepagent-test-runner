#!/usr/bin/env python3
"""
Test admin functionality directly
"""
import asyncio
import sys
sys.path.insert(0, '/home/fqs/workspace/self/claude-code-test-runner/service/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.auth.user_account import UserAccount
from app.services.auth.admin_service import AdminService
from datetime import datetime

async def test_admin_functions():
    # Create async engine
    engine = create_async_engine(
        "postgresql+asyncpg://cc_test_user:cc_test_pass@localhost:5433/cc_test_db",
        echo=False
    )

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        try:
            # Test 1: Suspend user
            print("\n=== TEST ADM-001: Admin suspend user ===")
            success, error = await AdminService.suspend_user(
                db=db,
                user_id=7,  # demotest@example.com
                reason="Testing suspension functionality",
                admin_id=3   # test@example.com (admin)
            )
            print(f"Success: {success}")
            print(f"Error: {error}")

            # Test 2: Check user status
            print("\n=== Check suspended user status ===")
            result = await db.execute(
                f"SELECT id, email, status FROM user_accounts WHERE id = 7"
            )
            user = result.fetchone()
            if user:
                print(f"User ID: {user[0]}, Email: {user[1]}, Status: {user[2]}")

            # Test 3: Reactivate user
            print("\n=== TEST ADM-002: Admin reactivate user ===")
            success, error = await AdminService.reactivate_user(
                db=db,
                user_id=7,
                admin_id=3
            )
            print(f"Success: {success}")
            print(f"Error: {error}")

            # Test 4: Check reactivated user status
            print("\n=== Check reactivated user status ===")
            result = await db.execute(
                f"SELECT id, email, status FROM user_accounts WHERE id = 7"
            )
            user = result.fetchone()
            if user:
                print(f"User ID: {user[0]}, Email: {user[1]}, Status: {user[2]}")

            # Test 5: Try to suspend self
            print("\n=== TEST ADM-003: Self-suspend prevention ===")
            success, error = await AdminService.suspend_user(
                db=db,
                user_id=3,  # admin themselves
                reason="Trying to suspend myself",
                admin_id=3  # same admin
            )
            print(f"Success: {success}")
            print(f"Error: {error}")
            if "Cannot suspend your own account" in str(error):
                print("✓ Self-suspend prevention works correctly!")
            else:
                print("✗ FAIL: Self-suspend prevention did not work")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_admin_functions())
