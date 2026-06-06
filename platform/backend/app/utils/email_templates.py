"""
Shared email template rendering.

Used by both direct SMTP (email_tasks) and Temporal activities (email_activities).
"""

from typing import Any, Dict


def render_email_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render an email template with the given context."""
    templates = {
        "verification": _render_verification_template,
        "password_reset": _render_password_reset_template,
        "account_suspended": _render_account_suspended_template,
    }
    renderer = templates.get(template_name)
    if not renderer:
        raise ValueError(f"Unknown email template: {template_name}")
    return renderer(context)


def _render_verification_template(context: Dict[str, Any]) -> str:
    verification_url = context.get("verification_url", "")
    return f"""
    <html>
    <body>
        <h2>Verify Your Email Address</h2>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link will expire in 24 hours.</p>
    </body>
    </html>
    """


def _render_password_reset_template(context: Dict[str, Any]) -> str:
    reset_url = context.get("reset_url", "")
    return f"""
    <html>
    <body>
        <h2>Reset Your Password</h2>
        <p>Please click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
    </body>
    </html>
    """


def _render_account_suspended_template(context: Dict[str, Any]) -> str:
    reason = context.get("reason", "Security policy violation")
    return f"""
    <html>
    <body>
        <h2>Account Suspended</h2>
        <p>Your account has been suspended.</p>
        <p><strong>Reason:</strong> {reason}</p>
        <p>Please contact support for assistance.</p>
    </body>
    </html>
    """
