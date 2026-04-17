"""
Use case: Verify a magic-link token and return the authenticated user.
"""

from uuid import UUID

from jose import JWTError

from backend.application.commands import VerifyMagicLinkCommand
from backend.application.exceptions import InvalidTokenError, UserNotFoundError
from backend.domain.entities import User
from backend.domain.ports import UserRepository
from backend.infrastructure.auth.token_service import verify_magic_token


class VerifyMagicLink:
    """
    Validate a magic-link JWT and return the corresponding User.

    Raises InvalidTokenError for any token problem (expired, tampered,
    malformed) so the caller never needs to catch JWTError directly.
    """

    def __init__(self, users: UserRepository) -> None:
        """
        Args:
            users: Port for retrieving User entities by ID.
        """
        self._users = users

    def execute(self, command: VerifyMagicLinkCommand) -> User:
        """
        Decode the token and look up the user.

        Args:
            command: Contains the raw JWT string.

        Returns:
            The authenticated User entity.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
            UserNotFoundError: If the user embedded in the token no longer exists.
        """
        try:
            payload = verify_magic_token(command.token)
        except JWTError:
            raise InvalidTokenError()

        user_id = UUID(payload["sub"])
        user = self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        return user
