"""
FastAPI dependency for JWT authentication.

Inject get_current_user into any endpoint that requires authentication.
Returns the authenticated user's UUID extracted from the Bearer token.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.infrastructure.auth.token_service import verify_magic_token

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UUID:
    """
    Validate the Bearer JWT and return the authenticated user's UUID.

    Args:
        credentials: Authorization header parsed by HTTPBearer.

    Returns:
        UUID of the authenticated user.

    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
    """
    try:
        payload = verify_magic_token(credentials.credentials)
        return UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
