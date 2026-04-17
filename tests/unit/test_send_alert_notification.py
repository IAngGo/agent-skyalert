"""
Unit tests for the SendAlertNotification use case.

Covers:
- Happy path: PENDING alert is sent, status becomes SENT, notified_at is set.
- Notification failure: status becomes FAILED, NotificationFailedError is raised.
- Alert not found: AlertNotFoundError is raised immediately.
- Idempotency: non-PENDING alerts return True without re-sending.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.application.commands import SendAlertNotificationCommand
from backend.application.exceptions import AlertNotFoundError, NotificationFailedError
from backend.application.use_cases.send_alert_notification import SendAlertNotification
from backend.domain.entities import Alert, AlertStatus
from tests.fakes import (
    InMemoryAlertRepository,
    InMemorySearchRepository,
    InMemoryUserRepository,
    StubNotificationService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_use_case(
    alerts: InMemoryAlertRepository,
    searches: InMemorySearchRepository,
    users: InMemoryUserRepository,
    notifier: StubNotificationService,
) -> SendAlertNotification:
    return SendAlertNotification(
        alerts=alerts,
        searches=searches,
        users=users,
        notification=notifier,
    )


def _pending_alert(search_id, flight) -> Alert:
    return Alert(
        id=uuid4(),
        search_id=search_id,
        flight=flight,
        historical_avg=550.00,
        current_price=450.00,
        drop_pct=18.18,
        status=AlertStatus.PENDING,
        triggered_at=datetime.now(timezone.utc),
        notified_at=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSendAlertNotification:
    """Tests for the SendAlertNotification use case."""

    def test_happy_path_sends_and_marks_sent(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        notifier: StubNotificationService,
        sample_search,
        sample_user,
        sample_flight,
    ) -> None:
        """Successful notification marks the alert SENT and sets notified_at."""
        alert = _pending_alert(sample_search.id, sample_flight)
        alerts.save(alert)

        use_case = _make_use_case(alerts, searches, users, notifier)
        result = use_case.execute(SendAlertNotificationCommand(alert_id=alert.id))

        assert result is True

        saved = alerts.find_by_id(alert.id)
        assert saved.status == AlertStatus.SENT
        assert saved.notified_at is not None

        # Verify the correct user and alert were passed to the notifier
        assert len(notifier.calls) == 1
        called_user, called_alert = notifier.calls[0]
        assert called_user.id == sample_user.id
        assert called_alert.id == alert.id

    def test_notification_failure_marks_failed_and_raises(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        sample_search,
        sample_flight,
    ) -> None:
        """When the notifier returns False the alert becomes FAILED and NotificationFailedError is raised."""
        failing_notifier = StubNotificationService(should_succeed=False)
        alert = _pending_alert(sample_search.id, sample_flight)
        alerts.save(alert)

        use_case = _make_use_case(alerts, searches, users, failing_notifier)

        with pytest.raises(NotificationFailedError) as exc_info:
            use_case.execute(SendAlertNotificationCommand(alert_id=alert.id))

        assert exc_info.value.alert_id == alert.id

        saved = alerts.find_by_id(alert.id)
        assert saved.status == AlertStatus.FAILED
        assert saved.notified_at is None

    def test_raises_when_alert_not_found(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        notifier: StubNotificationService,
    ) -> None:
        """AlertNotFoundError is raised if the alert_id does not exist."""
        missing_id = uuid4()
        use_case = _make_use_case(alerts, searches, users, notifier)

        with pytest.raises(AlertNotFoundError) as exc_info:
            use_case.execute(SendAlertNotificationCommand(alert_id=missing_id))

        assert exc_info.value.alert_id == missing_id
        assert notifier.calls == []

    def test_idempotent_for_non_pending_alert(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        notifier: StubNotificationService,
        sample_sent_alert,
    ) -> None:
        """An alert that is already SENT is skipped without re-notifying."""
        use_case = _make_use_case(alerts, searches, users, notifier)
        result = use_case.execute(
            SendAlertNotificationCommand(alert_id=sample_sent_alert.id)
        )

        assert result is True
        assert notifier.calls == []
