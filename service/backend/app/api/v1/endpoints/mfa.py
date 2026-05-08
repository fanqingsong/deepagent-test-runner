from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.mfa import (
    MFAVerificationRequest,
    MFASetupResponse,
    MFAEnableRequest,
    MFAEnabledResponse,
)
from app.services.auth.mfa_service import MFAService
from app.services.auth.auth_service import AuthService
from app.core.rate_limit_decorator import rate_limit

router = APIRouter()


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Initiate MFA setup - generate TOTP secret and recovery codes"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    from app.services.auth.session_service import SessionService
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Setup MFA
    success, error_message, data = await MFAService.setup_mfa(db, session.user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return MFASetupResponse(
        secret=data["secret"],
        qr_code=data["qr_code"],
        recovery_codes=data["recovery_codes"]
    )


@router.post("/enable", response_model=MFAEnabledResponse)
async def enable_mfa(
    request: MFAEnableRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Enable MFA with TOTP code verification"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    from app.services.auth.session_service import SessionService
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Enable MFA
    success, error_message = await MFAService.enable_mfa(
        db=db,
        user_id=session.user_id,
        totp_code=request.totp_code
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return MFAEnabledResponse(
        message="MFA enabled successfully. You will need to enter a verification code when logging in."
    )


@router.post("/disable")
async def disable_mfa(
    request: MFAVerificationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Disable MFA (requires password and optional TOTP verification)"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    from app.services.auth.session_service import SessionService
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Disable MFA
    success, error_message = await MFAService.disable_mfa(
        db=db,
        user_id=session.user_id,
        password=request.password,
        totp_code=getattr(request, 'totp_code', None)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return {"message": "MFA disabled successfully"}


@router.post("/verify")
@rate_limit(max_attempts=10, window_seconds=300)  # 10 attempts per 5 minutes
async def verify_mfa(
    request: MFAVerificationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA code during login or recovery code"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    from app.services.auth.session_service import SessionService
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Try TOTP verification first
    if request.totp_code:
        success, error_message = await MFAService.verify_mfa(
            db=db,
            user_id=session.user_id,
            totp_code=request.totp_code
        )

        if success:
            return {"message": "MFA verification successful"}
        elif error_message:
            # If TOTP failed, try recovery code
            pass

    # Try recovery code verification
    if request.recovery_code:
        success, error_message = await MFAService.verify_recovery_code(
            db=db,
            user_id=session.user_id,
            recovery_code=request.recovery_code
        )

        if success:
            return {"message": "Recovery code verified successfully"}

    # If both failed
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification code. Please try again."
    )
