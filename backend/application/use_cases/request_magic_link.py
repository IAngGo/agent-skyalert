"""
Use case: Request a magic-link login email.

If the email belongs to an existing user, generates a signed JWT and
sends it. If no user exists with that email, creates a minimal account
first — magic link is both registration and login for new users.
"""

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.commands import RequestMagicLinkCommand
from backend.domain.entities import User
from backend.domain.ports import AuthNotificationService, UserRepository
from backend.infrastructure.auth.token_service import create_magic_token


class RequestMagicLink:
    """
    Generate a magic-link token and send it to the given email address.

    Creates the user if no account exists for the email, so this use case
    doubles as registration for first-time users.
    """

    def __init__(
        self,
        users: UserRepository,
        auth_notification: AuthNotificationService,
    ) -> None:
        """
        Args:
            users: Port for finding and persisting User entities.
            auth_notification: Port for sending the magic-link email.
        """
        self._users = users
        self._auth_notification = auth_notification

    def execute(self, command: RequestMagicLinkCommand) -> None:
        """
        Find or create the user, generate a token, and send the email.

        Args:
            command: Contains the recipient email and frontend base_url.
        """
        user = self._users.find_by_email(command.email)
        if user is None:
            user = User(
                id=uuid4(),
                email=command.email,
                phone="",
                whatsapp_enabled=False,
                created_at=datetime.now(timezone.utc),
            )
            self._users.save(user)

        token = create_magic_token(user.id, user.email)
        link = f"{command.base_url.rstrip('/')}/app/verify.html?token={token}"
        self._auth_notification.send_magic_link(user.email, link)
