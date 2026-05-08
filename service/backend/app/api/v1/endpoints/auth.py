from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    RegistrationRequest,
    RegistrationResponse,
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.session_service import SessionService
from app.services.auth.admin_service import AdminService
from app.schemas.auth_user import User as AuthUser
from app.core.rate_limit_decorator import rate_limit

router = APIRouter()


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_attempts=3, window_seconds=3600)  # 3 attempts per hour
async def register(
    request: Request,
    data: RegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register new user account"""
    success, error_message, user = await AuthService.register_user(
        db=db,
        email=data.email,
        password=data.password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if error_message == "Invalid email format" else status.HTTP_409_CONFLICT,
            detail=error_message
        )

    return RegistrationResponse(
        message="Registration successful. Please check your email to verify your account.",
        user_id=user.id
    )


@router.post("/verify-email")
async def verify_email(
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email address with token"""
    success, error_message, user = await AuthService.verify_email(
        db=db,
        token=data.token
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=LoginResponse)
@rate_limit(max_attempts=5, window_seconds=900)  # 5 attempts per 15 minutes
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """User login with email and password"""
    # Get client IP address
    ip_address = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "")

    # Authenticate user
    success, error_message, user = await AuthService.authenticate_user(
        db=db,
        email=data.email,
        password=data.password,
        ip_address=ip_address
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message
        )

    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    # Check if account is suspended
    is_suspended, suspension_message = await AdminService.check_suspension_during_login(db, user)
    if is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=suspension_message
        )

    # Check if MFA is required
    if error_message == "MFA_REQUIRED":
        # Return a response indicating MFA verification is needed
        # Don't create session or tokens yet - wait for MFA verification
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={
                "message": "MFA verification required",
                "require_mfa": True,
                "user_id": user.id
            }
        )

    # Create session
    session = await SessionService.create_user_session(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        remember_me=data.remember_me
    )

    # Generate JWT tokens
    access_token, refresh_token = SessionService.generate_tokens(user.id, user.email)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        session_token=session.session_token,
        user=AuthUser(
            id=user.id,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
    )


@router.post("/logout")
async def logout(
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate session"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # For now, we'll need to extract user_id from the session token
    # In production, this would come from JWT token validation
    from app.services.auth.session_service import SessionService
    session = await SessionService.validate_session_token(db, session_token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Logout user
    success, error_message = await AuthService.logout_user(
        db=db,
        user_id=session.user_id,
        session_token=session_token
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return {"message": "Logged out successfully"}
