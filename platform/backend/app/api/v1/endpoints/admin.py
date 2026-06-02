from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.auth.admin_service import AdminService
from app.middleware.admin import require_admin
from app.services.auth.audit_service import AuditService

router = APIRouter()


class SuspendUserRequest(BaseModel):
    """Request model for suspending a user."""

    reason: str = Field(..., min_length=1, max_length=500, description="Reason for suspension")


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    request: Request,
    data: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin)
):
    """
    Suspend a user account (admin only).

    Suspends the specified user account and sends a notification email.
    """
    try:
        success, error = await AdminService.suspend_user(
            db=db,
            user_id=user_id,
            reason=data.reason,
            admin_id=admin_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Log audit event
        await AuditService.log_security_event(
            db=db,
            user_id=user_id,
            event_type="account_suspended",
            details={
                "suspended_by": admin_id,
                "reason": data.reason
            },
            ip_address=request.client.host
        )

        return {"message": f"User {user_id} has been suspended successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suspend user: {str(e)}")


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin)
):
    """
    Reactivate a suspended user account (admin only).

    Reactivates the specified user account and sends a notification email.
    """
    try:
        success, error = await AdminService.reactivate_user(
            db=db,
            user_id=user_id,
            admin_id=admin_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Log audit event
        await AuditService.log_security_event(
            db=db,
            user_id=user_id,
            event_type="account_reactivated",
            details={
                "reactivated_by": admin_id
            },
            ip_address=request.client.host
        )

        return {"message": f"User {user_id} has been reactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reactivate user: {str(e)}")
