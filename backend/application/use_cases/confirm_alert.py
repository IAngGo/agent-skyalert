"""
Use case: Confirm a sent Alert and optionally trigger automatic purchase.

Triggered when the user clicks "Confirm" (or "Buy Now") in the notification
email or WhatsApp message.
"""

from datetime import datetime, timezone

from backend.application.commands import ConfirmAlertCommand
from backend.application.exceptions import (
    AlertNotFoundError,
    PurchaseFailedError,
    SearchNotFoundError,
    UserNotFoundError,
)
from backend.domain.entities import Alert, AlertStatus
from backend.domain.ports import (
    AlertRepository,
    PurchaseService,
    SearchRepository,
    UserRepository,
)


class ConfirmAlert:
    """
    Mark a SENT Alert as CONFIRMED and optionally initiate a purchase.

    State transitions allowed:
    - SENT → CONFIRMED (normal acknowledgement)
    - SENT → CONFIRMED + purchase attempt (when trigger_purchase is True)

    Alerts in any other status (PENDING, EXPIRED, FAILED) are rejected
    with a ValueError to prevent stale confirmations.
    """

    def __init__(
        self,
        alerts: AlertRepository,
        searches: SearchRepository,
        users: UserRepository,
        purchase: PurchaseService,
    ) -> None:
        """
        Args:
            alerts: Port for retrieving and updating Alert entities.
            searches: Port for retrieving the parent Search (to verify ownership).
            users: Port for retrieving the confirming User.
            purchase: Port for initiating an automatic flight purchase.
        """
        self._alerts = alerts
        self._searches = searches
        self._users = users
        self._purchase = purchase

    def execute(self, command: ConfirmAlertCommand) -> Alert:
        """
        Confirm the Alert and optionally trigger purchase.

        Args:
            command: Contains alert_id, user_id, and trigger_purchase flag.

        Returns:
            The updated Alert entity with CONFIRMED status.

        Raises:
            AlertNotFoundError: If no Alert exists with command.alert_id.
            SearchNotFoundError: If the Alert's parent Search cannot be found.
            UserNotFoundError: If no User exists with command.user_id.
            ValueError: If the Alert is not in SENT status.
            ValueError: If the confirming user does not own the Search.
            PurchaseFailedError: If trigger_purchase is True and purchase fails.
        """
        alert = self._alerts.find_by_id(command.alert_id)
        if alert is None:
            raise AlertNotFoundError(command.alert_id)

        if alert.status != AlertStatus.SENT:
            raise ValueError(
                f"Alert {command.alert_id} cannot be confirmed from status '{alert.status}'."
            )

        search = self._searches.find_by_id(alert.search_id)
        if search is None:
            raise SearchNotFoundError(alert.search_id)

        user = self._users.find_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError(command.user_id)

        if search.user_id != command.user_id:
            raise ValueError(
                f"User {command.user_id} does not own alert {command.alert_id}."
            )

        alert.status = AlertStatus.CONFIRMED

        if command.trigger_purchase:
            success = self._purchase.purchase(user, alert.flight)
            if not success:
                raise PurchaseFailedError(command.alert_id)

        return self._alerts.save(alert)
