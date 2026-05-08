"""
Create Authentication Tables

This script creates the database tables required for the authentication service.
Run this after deploying the backend with auth functionality.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_db
from app.models.auth import (
    UserAccount,
    UserSession,
    MFASecret,
    RecoveryCode,
    EmailToken,
    AuditLog,
)


async def create_auth_tables():
    """Create all authentication-related database tables."""
    print("Creating authentication tables...")

    async with engine.begin() as conn:
        # Import Base from the models
        from app.models.auth.user_account import UserAccount
        from app.models.auth.user_session import UserSession
        from app.models.auth.mfa_secret import MFASecret
        from app.models.auth.recovery_code import RecoveryCode
        from app.models.auth.email_token import EmailToken
        from app.models.auth.audit_log import AuditLog

        # Get the metadata
        from app.core.database import Base

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        print("✓ Created user_accounts table")
        print("✓ Created user_sessions table")
        print("✓ Created mfa_secrets table")
        print("✓ Created recovery_codes table")
        print("✓ Created email_tokens table")
        print("✓ Created audit_logs table")

    print("\nAuthentication tables created successfully!")


async def verify_tables():
    """Verify that tables were created successfully."""
    print("\nVerifying table creation...")

    async with engine.begin() as conn:
        result = await conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN (
                'user_accounts',
                'user_sessions',
                'mfa_secrets',
                'recovery_codes',
                'email_tokens',
                'audit_logs'
            )
            ORDER BY table_name
        """)

        tables = [row[0] for row in result.fetchall()]

        if len(tables) == 6:
            print(f"✓ All 6 authentication tables verified")
            for table in tables:
                print(f"  - {table}")
        else:
            print(f"✗ Expected 6 tables, found {len(tables)}")
            return False

    return True


async def main():
    """Main function to create and verify auth tables."""
    try:
        await create_auth_tables()
        success = await verify_tables()

        if success:
            print("\n✓ Authentication database setup completed successfully!")
        else:
            print("\n✗ Authentication database setup failed!")
            return 1

    except Exception as e:
        print(f"\n✗ Error creating authentication tables: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
