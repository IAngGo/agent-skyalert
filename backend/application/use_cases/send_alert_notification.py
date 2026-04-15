"""
Use case: Dispatch a price-drop notification for a pending Alert.

Called by the Celery task that polls for PENDING alerts.
Attempts all enabled notification channels for the user.
Marks the Alert as SENT or FAILED depending on the outcome.
"""

from datetime import datetime, timezone

from backend.application.commands import SendAlertNotificationCommand
from backend.application.exceptions import (
    AlertNotFoundError,
    NotificationFailedError,
    SearchNotFoundError,
    UserNotFoundError,
)
from backend.domain.entities import AlertStatus
from backend.domain.ports import (
    AlertRepository,
    NotificationService,
    SearchRepository,
    UserRepository,
)


class SendAlertNotification:
    """
    Fetch a PENDING Alert and notify its owner through all enabled channels.

    Notification strategy:
    - Always attempt email (SendGrid).
    - Attempt WhatsApp (Twilio) only if user.whatsapp_enabled is True.
    - If at least one channel succeeds → mark SENT.
    - If all channels fail → mark FAILED and raise NotificationFailedError.

    Idempotency: If the Alert is not in PENDING status, returns True immediately
    to avoid duplicate notifications on retry.

    Resolution path: Alert.search_id → Search.user_id → User
    This is why SearchRepository is required in addition to UserRepository.
    """

    def __init__(
        self,
        alerts: AlertRepository,
        searches: SearchRepository,
        users: UserRepository,
        notification: NotificationService,
    ) -> None:
        """
        Args:
            alerts: Port for retrieving and updating Alert entities.
            searches: Port for retrieving the parent Search (to resolve user_id).
            users: Port for retrieving the User who owns the Search.
            notification: Port for dispatching the alert message.
        """
        self._alerts = alerts
        self._searches = searches
        self._users = users
        self._notification = notification

    def execute(self, command: SendAlertNotificationCommand) -> bool:
        """
        Dispatch the notification for the given Alert.

        Args:
            command: Contains the alert_id to process.

        Returns:
            True if notification was dispatched successfully.

        Raises:
            AlertNotFoundError: If no Alert exists with command.alert_id.
            SearchNotFoundError: If the Alert's parent Search cannot be found.
            UserNotFoundError: If the Search's owning User cannot be found.
            NotificationFailedError: If every notification channel failed.
        """
        alert = self._alerts.find_by_id(command.alert_id)
        if alert is None:
            raise AlertNotFoundError(command.alert_id)

        if alert.status != AlertStatus.PENDING:
            return True

        search = self._searches.find_by_id(alert.search_id)
        if search is None:
            raise SearchNotFoundError(alert.search_id)

        user = self._users.find_by_id(search.user_id)
        if user is None:
            raise UserNotFoundError(search.user_id)

        success = self._notification.send_alert(user, alert)

        now = datetime.now(timezone.utc)

        if success:
            alert.status = AlertStatus.SENT
            alert.notified_at = now
        else:
            alert.status = AlertStatus.FAILED

        self._alerts.save(alert)

        if not success:
            raise NotificationFailedError(command.alert_id)

        return True
