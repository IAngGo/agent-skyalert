"""
JWT token service for SkyAlert magic-link authentication.

Tokens are signed with HS256 using SECRET_KEY from the environment.
They are short-lived (15 minutes) and contain the user's id and email.
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

_ALGORITHM = "HS256"
_EXPIRY_MINUTES = 15


def _secret() -> str:
    """Read SECRET_KEY from environment or raise at startup."""
    key = os.getenv("SECRET_KEY")
    if not key:
        raise RuntimeError(
            "SECRET_KEY environment variable is required. "
            "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    return key


def create_magic_token(user_id: UUID, email: str) -> str:
    """
    Generate a signed JWT for magic-link login.

    Args:
        user_id: UUID of the user to authenticate.
        email: Email address embedded in the token for verification.

    Returns:
        Signed JWT string, valid for 15 minutes.
    """
    exp = datetime.now(timezone.utc) + timedelta(minutes=_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": exp,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def verify_magic_token(token: str) -> dict:
    """
    Decode and validate a magic-link JWT.

    Args:
        token: The signed JWT string from the magic-link URL.

    Returns:
        Decoded payload dict with keys "sub" (user_id str) and "email".

    Raises:
        JWTError: If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
