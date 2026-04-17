"""
Unit tests for the ConfirmAlert use case.

Cases under test:
1. Happy path — SENT alert is confirmed, status changes to CONFIRMED.
2. Purchase triggered successfully — PurchaseService is called once.
3. Purchase fails → PurchaseFailedError is raised.
4. Alert is not in SENT status → ValueError.
5. User does not own the search → ValueError.
6. Alert does not exist → AlertNotFoundError.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.application.commands import ConfirmAlertCommand
from backend.application.exceptions import AlertNotFoundError, PurchaseFailedError
from backend.application.use_cases.confirm_alert import ConfirmAlert
from backend.domain.entities import Alert, AlertStatus
from tests.fakes import (
    InMemoryAlertRepository,
    InMemorySearchRepository,
    InMemoryUserRepository,
    StubPurchaseService,
)


def make_use_case(
    alerts: InMemoryAlertRepository,
    searches: InMemorySearchRepository,
    users: InMemoryUserRepository,
    purchase: StubPurchaseService,
) -> ConfirmAlert:
    """Construct ConfirmAlert with the given fakes."""
    return ConfirmAlert(
        alerts=alerts,
        searches=searches,
        users=users,
        purchase=purchase,
    )


class TestConfirmAlert:
    """Tests for ConfirmAlert.execute()."""

    def test_confirms_sent_alert(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        purchase: StubPurchaseService,
        sample_sent_alert: Alert,
        sample_user,
    ) -> None:
        """A SENT alert becomes CONFIRMED; purchase is NOT called."""
        use_case = make_use_case(alerts, searches, users, purchase)
        cmd = ConfirmAlertCommand(
            alert_id=sample_sent_alert.id,
            user_id=sample_user.id,
            trigger_purchase=False,
        )

        result = use_case.execute(cmd)

        assert result.status == AlertStatus.CONFIRMED
        assert purchase.calls == []  # no purchase attempted

    def test_triggers_purchase_when_requested(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        purchase: StubPurchaseService,
        sample_sent_alert: Alert,
        sample_user,
    ) -> None:
        """When trigger_purchase=True, PurchaseService.purchase is called once."""
        use_case = make_use_case(alerts, searches, users, purchase)
        cmd = ConfirmAlertCommand(
            alert_id=sample_sent_alert.id,
            user_id=sample_user.id,
            trigger_purchase=True,
        )

        result = use_case.execute(cmd)

        assert result.status == AlertStatus.CONFIRMED
        assert len(purchase.calls) == 1
        called_user, called_flight = purchase.calls[0]
        assert called_user.id == sample_user.id
        assert called_flight == sample_sent_alert.flight

    def test_raises_when_purchase_fails(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        sample_sent_alert: Alert,
        sample_user,
    ) -> None:
        """A purchase failure raises PurchaseFailedError."""
        failing_purchase = StubPurchaseService(should_succeed=False)
        use_case = make_use_case(alerts, searches, users, failing_purchase)
        cmd = ConfirmAlertCommand(
            alert_id=sample_sent_alert.id,
            user_id=sample_user.id,
            trigger_purchase=True,
        )

        with pytest.raises(PurchaseFailedError):
            use_case.execute(cmd)

    def test_raises_when_alert_not_in_sent_status(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        purchase: StubPurchaseService,
        sample_sent_alert: Alert,
        sample_user,
    ) -> None:
        """Confirming an alert that is not SENT raises ValueError."""
        # Move the alert to PENDING so it can't be confirmed
        sample_sent_alert.status = AlertStatus.PENDING
        alerts.save(sample_sent_alert)

        use_case = make_use_case(alerts, searches, users, purchase)
        cmd = ConfirmAlertCommand(
            alert_id=sample_sent_alert.id,
            user_id=sample_user.id,
        )

        with pytest.raises(ValueError):
            use_case.execute(cmd)

    def test_raises_when_user_does_not_own_search(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        purchase: StubPurchaseService,
        sample_sent_alert: Alert,
    ) -> None:
        """A user who does not own the search cannot confirm the alert."""
        # Create a different user and save them so the use case can find them
        from datetime import datetime, timezone
        from backend.domain.entities import User
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            phone="+19995550001",
            whatsapp_enabled=False,
            created_at=datetime.now(timezone.utc),
        )
        users.save(other_user)

        use_case = make_use_case(alerts, searches, users, purchase)
        cmd = ConfirmAlertCommand(
            alert_id=sample_sent_alert.id,
            user_id=other_user.id,  # wrong owner
        )

        with pytest.raises(ValueError):
            use_case.execute(cmd)

    def test_raises_when_alert_not_found(
        self,
        alerts: InMemoryAlertRepository,
        searches: InMemorySearchRepository,
        users: InMemoryUserRepository,
        purchase: StubPurchaseService,
        sample_user,
    ) -> None:
        """An alert_id that does not exist raises AlertNotFoundError."""
        use_case = make_use_case(alerts, searches, users, purchase)
        cmd = ConfirmAlertCommand(
            alert_id=uuid4(),  # no alert with this id
            user_id=sample_user.id,
        )

        with pytest.raises(AlertNotFoundError):
            use_case.execute(cmd)
