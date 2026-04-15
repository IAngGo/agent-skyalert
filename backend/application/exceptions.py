"""
Domain-level exceptions raised by SkyAlert use cases.

These exceptions represent business rule violations, not infrastructure errors.
They are raised in the application layer and caught at the infrastructure
boundary (e.g. FastAPI exception handlers) for translation into HTTP responses.

No infrastructure imports allowed here.
"""


class SkyAlertError(Exception):
    """Base class for all SkyAlert application exceptions."""


class UserNotFoundError(SkyAlertError):
    """Raised when a required User does not exist in the repository."""

    def __init__(self, user_id: object) -> None:
        """
        Args:
            user_id: The UUID that was looked up and not found.
        """
        super().__init__(f"User not found: {user_id}")
        self.user_id = user_id


class SearchNotFoundError(SkyAlertError):
    """Raised when a required Search does not exist in the repository."""

    def __init__(self, search_id: object) -> None:
        """
        Args:
            search_id: The UUID that was looked up and not found.
        """
        super().__init__(f"Search not found: {search_id}")
        self.search_id = search_id


class AlertNotFoundError(SkyAlertError):
    """Raised when a required Alert does not exist in the repository."""

    def __init__(self, alert_id: object) -> None:
        """
        Args:
            alert_id: The UUID that was looked up and not found.
        """
        super().__init__(f"Alert not found: {alert_id}")
        self.alert_id = alert_id


class InsufficientPriceHistoryError(SkyAlertError):
    """
    Raised when there is not enough historical data to compute a meaningful average.

    This is expected on the first few scrapes for a new Search and should be
    handled gracefully — store the observation, skip alert evaluation.
    """

    def __init__(self, search_id: object, required: int, available: int) -> None:
        """
        Args:
            search_id: UUID of the Search with insufficient history.
            required: Minimum number of observations needed.
            available: Number of observations currently available.
        """
        super().__init__(
            f"Search {search_id} has {available} price observations; "
            f"need at least {required} to evaluate a drop."
        )
        self.search_id = search_id
        self.required = required
        self.available = available


class InvalidThresholdError(SkyAlertError):
    """Raised when a threshold_pct value is outside the allowed range (0, 100)."""

    def __init__(self, value: float) -> None:
        """
        Args:
            value: The invalid threshold value that was supplied.
        """
        super().__init__(
            f"threshold_pct must be between 0 and 100 exclusive; got {value}."
        )
        self.value = value


class NotificationFailedError(SkyAlertError):
    """Raised when all notification channels fail to deliver an alert."""

    def __init__(self, alert_id: object) -> None:
        """
        Args:
            alert_id: UUID of the Alert that could not be delivered.
        """
        super().__init__(f"Failed to deliver notification for alert: {alert_id}")
        self.alert_id = alert_id


class PurchaseFailedError(SkyAlertError):
    """Raised when the automatic purchase flow fails to initiate."""

    def __init__(self, alert_id: object) -> None:
        """
        Args:
            alert_id: UUID of the Alert whose purchase could not be initiated.
        """
        super().__init__(f"Purchase failed for alert: {alert_id}")
        self.alert_id = alert_id


class SearchInactiveError(SkyAlertError):
    """Raised when an operation is attempted on a Search that is not active."""

    def __init__(self, search_id: object) -> None:
        """
        Args:
            search_id: UUID of the inactive Search.
        """
        super().__init__(f"Search {search_id} is not active.")
        self.search_id = search_id
