"""
Composite NotificationService that combines email and WhatsApp.

This is the adapter injected into SendAlertNotification in production.
It tries all channels and returns True if at least one succeeds.
"""

import logging

from backend.domain.entities import Alert, User
from backend.domain.ports import NotificationService

logger = logging.getLogger(__name__)


class CompositeNotificationService(NotificationService):
    """
    Dispatches alerts through multiple NotificationService adapters in sequence.

    Returns True if at least one channel delivers successfully.
    Logs individual channel failures but does not raise — the caller
    (SendAlertNotification use case) decides whether to raise NotificationFailedError.

    Typical usage in production:
        CompositeNotificationService([
            SendGridNotificationService(),
            TwilioWhatsAppService(),
        ])
    """

    def __init__(self, services: list[NotificationService]) -> None:
        """
        Args:
            services: Ordered list of notification adapters to attempt.
                      At least one must be provided.

        Raises:
            ValueError: If the services list is empty.
        """
        if not services:
            raise ValueError("CompositeNotificationService requires at least one service.")
        self._services = services

    def send_alert(self, user: User, alert: Alert) -> bool:
        """
        Attempt to send the alert through each registered service.

        Args:
            user: The User to notify.
            alert: The Alert containing drop details and flight snapshot.

        Returns:
            True if at least one service succeeded, False if all failed.
        """
        any_success = False

        for service in self._services:
            try:
                result = service.send_alert(user, alert)
                if result:
                    any_success = True
                    logger.info(
                        "Alert %s delivered via %s",
                        alert.id,
                        type(service).__name__,
                    )
                else:
                    logger.warning(
                        "Alert %s not delivered via %s",
                        alert.id,
                        type(service).__name__,
                    )
            except Exception:
                logger.exception(
                    "Unexpected error in %s for alert %s",
                    type(service).__name__,
                    alert.id,
                )

        return any_success
