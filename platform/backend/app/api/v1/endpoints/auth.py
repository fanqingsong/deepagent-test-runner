from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
from app.core.security import get_current_user
from app.core.rate_limit_decorator import rate_limit
from app.models.user import User
from app.schemas.user import UserProfileUpdate

router = APIRouter()

# Cookie settings for secure token storage
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": False,  # Set to True for HTTPS (production), False for HTTP (development)
    "samesite": "lax",
}


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


@router.post("/login")
@rate_limit(max_attempts=5, window_seconds=900)  # 5 attempts per 15 minutes
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """User login with email and password. Sets httpOnly secure cookies for tokens."""
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

    # Check if user is admin by querying users table
    is_admin = False
    token_user_id = user.id  # Default to user_accounts ID
    user_roles = []
    user_permissions = []
    try:
        from app.models.user import User as UserModel
        from app.models.role import Role
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(Role.permissions))
            .where(UserModel.email == user.email)
        )
        legacy_user = result.scalar_one_or_none()
        if legacy_user:
            is_admin = legacy_user.is_admin
            token_user_id = legacy_user.id  # Use users table ID for token
            user_roles = [r.name for r in legacy_user.roles]
            user_permissions = list({p.name for r in legacy_user.roles for p in r.permissions})
    except Exception:
        pass  # If users table doesn't exist or query fails, default to non-admin

    # Generate JWT tokens with the correct user ID (prefer users table ID)
    access_token, refresh_token = SessionService.generate_tokens(token_user_id, user.email, remember_me=data.remember_me)

    # SECURITY FIX: Set httpOnly cookies instead of returning tokens in response body
    max_age = (30 * 24 * 60 * 60) if data.remember_me else (24 * 60 * 60)  # 30 days or 1 day

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=15 * 60,  # 15 minutes for access token
        **COOKIE_SETTINGS
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        **COOKIE_SETTINGS
    )

    response.set_cookie(
        key="session_token",
        value=session.session_token,
        max_age=max_age,
        **COOKIE_SETTINGS
    )

    # Return user info without tokens in response body
    return JSONResponse(
        content={
            "message": "Login successful",
            "mfa_required": False,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_verified": user.is_verified,
                "mfa_enabled": user.mfa_enabled,
                "status": user.status,
                "is_admin": is_admin,
                "roles": user_roles,
                "permissions": user_permissions,
            }
        },
        headers=dict(response.headers)
    )


@router.post("/logout")
async def logout(
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate session. Clears httpOnly cookies."""
    # Get session token from cookie or header (for backward compatibility)
    session_token = http_request.cookies.get("session_token") or http_request.headers.get("X-Session-Token")
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

    # SECURITY FIX: Clear httpOnly cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("session_token", path="/")

    return JSONResponse(
        content={"message": "Logged out successfully"},
        headers=dict(response.headers)
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token from httpOnly cookie."""
    # SECURITY FIX: Get refresh token from cookie instead of request body
    refresh_token_value = request.cookies.get("refresh_token")

    # For backward compatibility, also check request body
    if not refresh_token_value:
        try:
            body = await request.json()
            refresh_token_value = body.get("refresh_token")
        except:
            pass

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )

    from app.core.auth_security import verify_token
    payload = verify_token(refresh_token_value, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not verified"
        )

    # Check if session has remember_me
    is_suspended, _ = await AdminService.check_suspension_during_login(db, user)
    if is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    # Look up session to check remember_me flag
    session_token_cookie = request.cookies.get("session_token")
    session_token_header = request.headers.get("X-Session-Token")
    session_token = session_token_cookie or session_token_header
    remember_me = False
    if session_token:
        session = await SessionService.validate_session_token(db, session_token)
        if session:
            remember_me = session.is_remember_me

    # Check admin status
    is_admin = False
    token_user_id = user.id
    try:
        from app.models.user import User as UserModel
        legacy_result = await db.execute(
            select(UserModel).where(UserModel.email == user.email)
        )
        legacy_user = legacy_result.scalar_one_or_none()
        if legacy_user:
            is_admin = legacy_user.is_admin
            token_user_id = legacy_user.id
    except Exception:
        pass

    access_token, new_refresh_token = SessionService.generate_tokens(
        token_user_id, user.email, remember_me=remember_me
    )

    # SECURITY FIX: Set new tokens in httpOnly cookies
    max_age = (30 * 24 * 60 * 60) if remember_me else (24 * 60 * 60)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=15 * 60,  # 15 minutes for access token
        **COOKIE_SETTINGS
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=max_age,
        **COOKIE_SETTINGS
    )

    return JSONResponse(
        content={"message": "Token refreshed successfully"},
        headers=dict(response.headers)
    )


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current user info with roles and permissions."""
    roles = [r.name for r in current_user.roles]
    permissions = list({p.name for r in current_user.roles for p in r.permissions})
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "roles": roles,
        "permissions": permissions,
    }


@router.put("/me")
async def update_me(
    profile_data: UserProfileUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile (username only)."""
    from app.models.user import User as UserModel

    # Check if username is being changed and if it's already taken
    if profile_data.username and profile_data.username != current_user.username:
        result = await db.execute(
            select(UserModel).where(UserModel.username == profile_data.username)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use"
            )

    # Update username if provided
    if profile_data.username is not None:
        current_user.username = profile_data.username

    await db.commit()
    await db.refresh(current_user)

    # Return updated user info
    roles = [r.name for r in current_user.roles]
    permissions = list({p.name for r in current_user.roles for p in r.permissions})
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "roles": roles,
        "permissions": permissions,
    }
