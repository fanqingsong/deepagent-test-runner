from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.password import (
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordChangeRequest,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.session_service import SessionService
from app.services.auth.audit_service import AuditService
from app.core.rate_limit_decorator import rate_limit

router = APIRouter()


@router.post("/reset")
@rate_limit(max_attempts=3, window_seconds=3600)  # 3 attempts per hour
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset email.

    Generates a password reset token and sends it to the user's email.
    Always returns success to prevent email enumeration.
    """
    try:
        success, error, _ = await AuthService.generate_password_reset_token(
            db=db,
            email=data.email
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Log audit event
        await AuditService.log_security_event(
            db=db,
            user_id=None,
            event_type="password_reset_requested",
            details={"email": data.email},
            ip_address=request.client.host
        )

        return {"message": "If the email exists, a password reset link has been sent"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process reset request: {str(e)}")


@router.post("/reset/confirm")
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm password reset with token.

    Validates the reset token and updates the user's password.
    """
    try:
        success, error = await AuthService.reset_password(
            db=db,
            token=data.token,
            new_password=data.new_password
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Log audit event
        await AuditService.log_security_event(
            db=db,
            user_id=None,
            event_type="password_reset_completed",
            details={"token_used": True},
            ip_address=request.client.host
        )

        return {"message": "Password has been reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


@router.post("/change")
async def change_password(
    request: Request,
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Change password (requires authentication).

    Allows authenticated users to change their password by providing current password.
    Invalidates all other sessions after password change for security.
    """
    # Get user from session
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token required")

    session = await SessionService.validate_session_token(db, session_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        success, error = await AuthService.change_password(
            db=db,
            user_id=session.user_id,
            current_password=data.current_password,
            new_password=data.new_password
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Log audit event
        await AuditService.log_security_event(
            db=db,
            user_id=session.user_id,
            event_type="password_changed",
            details={"sessions_terminated": True},
            ip_address=request.client.host
        )

        return {"message": "Password changed successfully. All other sessions have been terminated."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")
