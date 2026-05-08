"""
Admin middleware for role-based access control.
"""

from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth.session_service import SessionService


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Dependency to require admin role for endpoints.

    Checks if the current user has admin privileges by checking
    if their email domain or specific user ID has admin access.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        User ID if admin

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    # Get session token
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate session
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check if user is admin (simple implementation - in production, use proper role system)
    # For now, check if email ends with @admin.com or specific user IDs
    from sqlalchemy import select
    from app.models.auth.user_account import UserAccount

    query = select(UserAccount).where(UserAccount.id == session.user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Admin check: email domain or specific users
    # In production, use a proper roles/permissions system
    admin_domains = ["admin.com", "example.com"]  # Configure as needed
    admin_user_ids = [1]  # First user is admin by default

    is_admin = (
        any(user.email.endswith(f"@{domain}") for domain in admin_domains) or
        user.id in admin_user_ids
    )

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return user.id
