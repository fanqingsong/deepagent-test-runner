from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets
import logging

from app.models.auth import UserAccount, UserSession
from app.core.auth_security import verify_password, create_access_token, create_refresh_token, hash_password
from app.core.auth_rate_limit import check_rate_limit
from app.schemas.user import Session as SessionSchema

logger = logging.getLogger(__name__)


class SessionService:
    """Session management service for login, logout, and session validation"""

    @staticmethod
    async def create_user_session(
        db: AsyncSession,
        user: UserAccount,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> UserSession:
        """
        Create a new user session with concurrent limit enforcement.

        Args:
            db: Database session
            user: User account
            ip_address: Client IP address
            user_agent: Client user agent
            remember_me: Whether to create persistent session (30 days) or session-only (24 hours)

        Returns:
            Created UserSession object
        """
        try:
            # Check concurrent session limit (max 5)
            await SessionService.enforce_concurrent_session_limit(db, user.id)

            # Create session
            session_token = UserSession.generate_session_token()
            expires_at = UserSession.create_expires_at(remember_me)

            new_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                user_agent=user_agent[:500] if user_agent else None,
                ip_address=ip_address,
                is_remember_me=remember_me,
                expires_at=expires_at
            )

            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)

            logger.info(f"Session created for user {user.id}: remember_me={remember_me}")
            return new_session

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating session: {str(e)}")
            raise

    @staticmethod
    async def enforce_concurrent_session_limit(db: AsyncSession, user_id: int, max_sessions: int = 5):
        """
        Enforce maximum concurrent sessions (5). Terminate oldest inactive session if limit exceeded.

        Args:
            db: Database session
            user_id: User ID
            max_sessions: Maximum allowed concurrent sessions
        """
        # Count active sessions for user
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        )
        result = await db.execute(query)
        active_sessions = result.scalars().all()

        if len(active_sessions) >= max_sessions:
            # Find oldest inactive session to terminate
            sessions_list = list(active_sessions)
            sessions_list.sort(key=lambda s: s.last_active)

            # Terminate oldest session
            oldest = sessions_list[0]
            oldest.terminate()
            logger.info(f"Terminated oldest session {oldest.id} for user {user_id} due to limit")

    @staticmethod
    async def validate_session_token(
        db: AsyncSession,
        session_token: str
    ) -> Optional[UserSession]:
        """
        Validate session token and return session if valid.

        Args:
            db: Database session
            session_token: Session token to validate

        Returns:
            UserSession if valid, None otherwise
        """
        query = select(UserSession).where(
            UserSession.session_token == session_token
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        if session.is_expired():
            return None

        # Refresh last active timestamp
        session.refresh_last_active()
        await db.commit()

        return session

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: int
    ) -> list[UserSession]:
        """
        Get all active sessions for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of active UserSession objects
        """
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.last_active.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def terminate_session(
        db: AsyncSession,
        session_id: int,
        user_id: int
    ) -> bool:
        """
        Terminate a specific session.

        Args:
            db: Database session
            session_id: Session ID to terminate
            user_id: User ID (for authorization)

        Returns:
            True if terminated, False otherwise
        """
        query = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return False

        session.terminate()
        await db.commit()

        logger.info(f"Session {session_id} terminated for user {user_id}")
        return True

    @staticmethod
    async def terminate_all_user_sessions(
        db: AsyncSession,
        user_id: int,
        exclude_session_id: Optional[int] = None
    ):
        """
        Terminate all sessions for a user (optionally excluding current session).

        Args:
            db: Database session
            user_id: User ID
            exclude_session_id: Session ID to exclude from termination
        """
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        )

        if exclude_session_id:
            query = query.where(UserSession.id != exclude_session_id)

        result = await db.execute(query)
        sessions = result.scalars().all()

        for session in sessions:
            session.terminate()

        await db.commit()
        logger.info(f"Terminated {len(sessions)} sessions for user {user_id}")

    @staticmethod
    def generate_tokens(user_id: int, email: str) -> Tuple[str, str]:
        """
        Generate JWT access and refresh tokens.

        Args:
            user_id: User ID
            email: User email

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = create_access_token({"sub": str(user_id), "email": email})
        refresh_token = create_refresh_token({"sub": str(user_id), "email": email})

        return access_token, refresh_token
