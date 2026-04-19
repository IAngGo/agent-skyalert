"""
SendGrid email implementation of the NotificationService port.

Reads SENDGRID_API_KEY and SENDGRID_FROM_EMAIL from environment.
Never hardcodes credentials.
"""

import logging
import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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


class SendGridNotificationService(NotificationService):
    """
    Sends price-drop alert emails via the SendGrid API.

    The email body includes the route, price drop percentage, current price,
    and a deep-link to the flight offer.
    """

    def __init__(self) -> None:
        """Load SendGrid credentials from environment on instantiation."""
        self._api_key = _require_env("SENDGRID_API_KEY")
        self._from_email = _require_env("SENDGRID_FROM_EMAIL")
        self._client = SendGridAPIClient(self._api_key)

    def send_alert(self, user: User, alert: Alert) -> bool:
        """
        Send a price-drop alert email to the given user.

        Args:
            user: The User to notify (uses user.email).
            alert: The Alert containing drop details and flight snapshot.

        Returns:
            True if the email was accepted by SendGrid (2xx response).
            False on any error (logs the exception).
        """
        subject = (
            f"Price drop alert: {alert.flight.origin} → {alert.flight.destination} "
            f"({alert.drop_pct:.1f}% off)"
        )
        body = self._build_email_body(alert)

        from urllib.parse import urlparse
        parsed = urlparse(alert.flight.url)
        safe_url = alert.flight.url if parsed.scheme in ("http", "https") else "https://www.google.com/travel/flights"
        body = body.replace(alert.flight.url, safe_url)

        message = Mail(
            from_email=self._from_email,
            to_emails=user.email,
            subject=subject,
            html_content=body,
        )

        try:
            response = self._client.send(message)
            success = 200 <= response.status_code < 300
            if not success:
                logger.error(
                    "SendGrid rejected email for alert %s: status %s",
                    alert.id,
                    response.status_code,
                )
            return success
        except Exception:
            logger.exception("SendGrid email failed for alert %s", alert.id)
            return False

    def _build_email_body(self, alert: Alert) -> str:
        """
        Render the HTML email body for a price-drop alert.

        Args:
            alert: The Alert entity with flight and price data.

        Returns:
            HTML string for the email body.
        """
        flight = alert.flight
        return f"""
        <h2>Price Drop Detected!</h2>
        <p>
            <strong>Route:</strong> {flight.origin} → {flight.destination}<br>
            <strong>Date:</strong> {flight.departure_date}<br>
            <strong>Airline:</strong> {flight.airline}<br>
            <strong>Current price:</strong> {flight.currency_code} {flight.price:.2f}<br>
            <strong>Historical average:</strong> {flight.currency_code} {alert.historical_avg:.2f}<br>
            <strong>Drop:</strong> {alert.drop_pct:.1f}%<br>
            <strong>Stops:</strong> {flight.stops}<br>
            <strong>Duration:</strong> {flight.duration_minutes} min
        </p>
        <p><a href="{flight.url}">View offer on Google Flights</a></p>
        <p><small>Alert ID: {alert.id}</small></p>
        """
