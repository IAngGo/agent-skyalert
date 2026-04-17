"""
SendGrid implementation of the AuthNotificationService port.

Sends magic-link login emails. Reads SENDGRID_API_KEY and
SENDGRID_FROM_EMAIL from the environment.
"""

import logging
import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from backend.domain.ports import AuthNotificationService

logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set.")
    return value


class SendGridAuthService(AuthNotificationService):
    """Sends magic-link login emails via the SendGrid API."""

    def __init__(self) -> None:
        """Load SendGrid credentials from environment on instantiation."""
        self._api_key = _require_env("SENDGRID_API_KEY")
        self._from_email = _require_env("SENDGRID_FROM_EMAIL")
        self._client = SendGridAPIClient(self._api_key)

    def send_magic_link(self, to_email: str, link: str) -> bool:
        """
        Send a magic-link login email.

        Args:
            to_email: Recipient email address.
            link: Full verify URL the user must click.

        Returns:
            True if SendGrid accepted the email, False on any error.
        """
        message = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject="Your SkyAlert login link",
            html_content=self._build_body(link),
        )
        try:
            response = self._client.send(message)
            success = 200 <= response.status_code < 300
            if not success:
                logger.error("SendGrid rejected magic-link email to %s: %s", to_email, response.status_code)
            return success
        except Exception:
            logger.exception("SendGrid magic-link email failed for %s", to_email)
            return False

    def _build_body(self, link: str) -> str:
        return f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
          <h2 style="color:#2563eb;margin-bottom:8px">✈ SkyAlert</h2>
          <p style="color:#374151;font-size:15px">
            Click the button below to sign in. This link expires in 15 minutes.
          </p>
          <a href="{link}"
             style="display:inline-block;margin-top:16px;padding:12px 24px;
                    background:#2563eb;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;font-size:15px">
            Sign in to SkyAlert
          </a>
          <p style="color:#9ca3af;font-size:12px;margin-top:24px">
            If you didn't request this, you can safely ignore this email.
          </p>
        </div>
        """
