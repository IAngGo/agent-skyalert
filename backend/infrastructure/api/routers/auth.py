"""
FastAPI router for magic-link authentication.

POST /auth/magic-link  — request a login email
GET  /auth/verify      — validate the token and return user identity
"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.application.commands import RequestMagicLinkCommand, VerifyMagicLinkCommand
from backend.application.use_cases.request_magic_link import RequestMagicLink
from backend.application.use_cases.verify_magic_link import VerifyMagicLink
from backend.infrastructure.notifications.sendgrid_auth_service import SendGridAuthService
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.user_repository import PostgresUserRepository

router = APIRouter(tags=["auth"])


class MagicLinkRequest(BaseModel):
    """Request body for POST /auth/magic-link."""
    email: EmailStr


class MagicLinkResponse(BaseModel):
    """Acknowledgement that the email was dispatched."""
    message: str


class VerifyResponse(BaseModel):
    """Payload returned after successful token verification."""
    user_id: UUID
    email: str


def _frontend_base_url() -> str:
    """Read FRONTEND_BASE_URL from env, defaulting to localhost for dev."""
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:8000")


@router.post("/auth/magic-link", response_model=MagicLinkResponse)
def request_magic_link(
    body: MagicLinkRequest,
    db: Session = Depends(get_db),
) -> MagicLinkResponse:
    """
    Send a magic-link login email to the given address.

    Creates a new user account if no account exists for that email.

    Args:
        body: Contains the recipient email address.
        db: SQLAlchemy session.

    Returns:
        Confirmation message (always — we never reveal whether the email exists).
    """
    users = PostgresUserRepository(db)

    try:
        auth_notification = SendGridAuthService()
    except RuntimeError:
        # SendGrid not configured in this environment — log and return success
        # so the UX flow isn't broken during local development without credentials.
        import logging
        logging.getLogger(__name__).warning(
            "SendGrid not configured — magic link not sent for %s.", body.email
        )
        # Still create the user so the flow can be tested without email.
        from backend.application.use_cases.request_magic_link import RequestMagicLink as _UC
        from backend.infrastructure.notifications.stub_auth_service import StubAuthService
        use_case = _UC(users=users, auth_notification=StubAuthService())
        use_case.execute(RequestMagicLinkCommand(email=body.email, base_url=_frontend_base_url()))
        db.commit()
        return MagicLinkResponse(message="Magic link sent (check server logs in dev mode).")

    use_case = RequestMagicLink(users=users, auth_notification=auth_notification)
    use_case.execute(RequestMagicLinkCommand(
        email=body.email,
        base_url=_frontend_base_url(),
    ))
    db.commit()
    return MagicLinkResponse(message="Magic link sent — check your inbox.")


@router.get("/auth/verify", response_model=VerifyResponse)
def verify_magic_link(
    token: str,
    db: Session = Depends(get_db),
) -> VerifyResponse:
    """
    Validate a magic-link token and return the user's identity.

    Args:
        token: JWT from the magic-link URL query parameter.
        db: SQLAlchemy session.

    Returns:
        VerifyResponse with user_id and email.

    Raises:
        InvalidTokenError: If the token is invalid or expired (→ 400).
        UserNotFoundError: If the user no longer exists (→ 404).
    """
    users = PostgresUserRepository(db)
    use_case = VerifyMagicLink(users=users)
    user = use_case.execute(VerifyMagicLinkCommand(token=token))
    return VerifyResponse(user_id=user.id, email=user.email)
