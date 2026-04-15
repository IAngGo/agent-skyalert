"""
PostgreSQL implementation of the AlertRepository port.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.entities import Alert, AlertStatus
from backend.domain.ports import AlertRepository
from backend.infrastructure.persistence.mappers import alert_to_domain, alert_to_model
from backend.infrastructure.persistence.models import AlertModel


class PostgresAlertRepository(AlertRepository):
    """
    Concrete AlertRepository backed by PostgreSQL via SQLAlchemy.

    Transaction management is the caller's responsibility.
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: An active SQLAlchemy Session.
        """
        self._session = session

    def save(self, alert: Alert) -> Alert:
        """
        Persist an Alert entity via upsert (merge by primary key).

        Args:
            alert: The Alert entity to persist.

        Returns:
            The saved Alert entity.
        """
        model = alert_to_model(alert)
        merged = self._session.merge(model)
        self._session.flush()
        return alert_to_domain(merged)

    def find_by_id(self, alert_id: UUID) -> Alert | None:
        """
        Retrieve an Alert by primary key.

        Args:
            alert_id: UUID of the target Alert.

        Returns:
            The Alert entity if found, None otherwise.
        """
        model = self._session.get(AlertModel, alert_id)
        return alert_to_domain(model) if model else None

    def find_by_search(self, search_id: UUID) -> list[Alert]:
        """
        Retrieve all Alerts for a given Search, most recent first.

        Args:
            search_id: UUID of the parent Search.

        Returns:
            List of Alert entities.
        """
        models = (
            self._session.query(AlertModel)
            .filter(AlertModel.search_id == search_id)
            .order_by(AlertModel.triggered_at.desc())
            .all()
        )
        return [alert_to_domain(m) for m in models]

    def find_pending(self) -> list[Alert]:
        """
        Retrieve all Alerts with PENDING status.

        Returns:
            List of Alert entities awaiting notification dispatch.
        """
        models = (
            self._session.query(AlertModel)
            .filter(AlertModel.status == AlertStatus.PENDING.value)
            .order_by(AlertModel.triggered_at.asc())
            .all()
        )
        return [alert_to_domain(m) for m in models]
