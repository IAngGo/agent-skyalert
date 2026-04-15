"""
Twilio WhatsApp implementation of the NotificationService port.

Reads TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM
from environment. Never hardcodes credentials.

Twilio WhatsApp requires the sender number to be prefixed with "whatsapp:".
"""

import logging
import os

from twilio.rest import Client

from backend.domain.entities import Alert, User
from backend.domain.ports import NotificationService

logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    """
    Read a required environment variable or raise at startup.

    Args:
        key: The environment variable name.

    Returns:
        The variable's string value.

    Raises:
        RuntimeError: If the variable is not set.
    """
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set.")
    return value


class TwilioWhatsAppService(NotificationService):
    """
    Sends price-drop alert messages via Twilio WhatsApp.

    Only sends if user.whatsapp_enabled is True — callers may also gate on
    this, but the check is repeated here as a safety guard.
    """

    def __init__(self) -> None:
        """Load Twilio credentials from environment on instantiation."""
        self._account_sid = _require_env("TWILIO_ACCOUNT_SID")
        self._auth_token = _require_env("TWILIO_AUTH_TOKEN")
        self._from_number = _require_env("TWILIO_WHATSAPP_FROM")
        self._client = Client(self._account_sid, self._auth_token)

    def send_alert(self, user: User, alert: Alert) -> bool:
        """
        Send a price-drop WhatsApp message to the given user.

        Skips silently (returns False) if user has not enabled WhatsApp.

        Args:
            user: The User to notify (uses user.phone).
            alert: The Alert containing drop details and flight snapshot.

        Returns:
            True if the message was accepted by Twilio.
            False if WhatsApp is disabled for the user or on any error.
        """
        if not user.whatsapp_enabled:
            return False

        body = self._build_message(alert)
        to_number = f"whatsapp:{user.phone}"
        from_number = f"whatsapp:{self._from_number}"

        try:
            message = self._client.messages.create(
                body=body,
                from_=from_number,
                to=to_number,
            )
            success = message.sid is not None
            if not success:
                logger.error(
                    "Twilio returned no SID for alert %s to %s",
                    alert.id,
                    user.phone,
                )
            return success
        except Exception:
            logger.exception(
                "Twilio WhatsApp failed for alert %s to %s", alert.id, user.phone
            )
            return False

    def _build_message(self, alert: Alert) -> str:
        """
        Render the WhatsApp message text for a price-drop alert.

        Args:
            alert: The Alert entity with flight and price data.

        Returns:
            Plain-text string for the WhatsApp message body.
        """
        flight = alert.flight
        return (
            f"SkyAlert: Price drop!\n"
            f"{flight.origin} -> {flight.destination} on {flight.departure_date}\n"
            f"Airline: {flight.airline}\n"
            f"Now: {flight.currency_code} {flight.price:.2f} "
            f"({alert.drop_pct:.1f}% below avg)\n"
            f"Book: {flight.url}"
        )
