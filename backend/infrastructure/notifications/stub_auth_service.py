"""
Stub AuthNotificationService for local development without SendGrid credentials.

Logs the magic link to stdout so developers can click it directly.
"""

import logging

from backend.domain.ports import AuthNotificationService

logger = logging.getLogger(__name__)


class StubAuthService(AuthNotificationService):
    """Prints the magic link to the log instead of sending an email."""

    def send_magic_link(self, to_email: str, link: str) -> bool:
        """Log the link and return True."""
        logger.warning(
            "\n\n  [DEV] Magic link for %s:\n  %s\n",
            to_email,
            link,
        )
        print(f"\n[DEV] Magic link for {to_email}:\n{link}\n")
        return True
