"""
PostgreSQL implementation of the PriceHistoryRepository port.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.domain.entities import PriceHistory
from backend.domain.ports import PriceHistoryRepository
from backend.infrastructure.persistence.mappers import (
    price_history_to_domain,
    price_history_to_model,
)
from backend.infrastructure.persistence.models import PriceHistoryModel


class PostgresPriceHistoryRepository(PriceHistoryRepository):
    """
    Concrete PriceHistoryRepository backed by PostgreSQL via SQLAlchemy.

    Observations are append-only — save() never updates existing rows.
    Transaction management is the caller's responsibility.
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: An active SQLAlchemy Session.
        """
        self._session = session

    def save(self, record: PriceHistory) -> PriceHistory:
        """
        Append a new PriceHistory observation.

        Args:
            record: The PriceHistory entity to persist.

        Returns:
            The persisted PriceHistory entity.
        """
        model = price_history_to_model(record)
        self._session.add(model)
        self._session.flush()
        return price_history_to_domain(model)

    def get_average(self, search_id: UUID, since: datetime) -> float | None:
        """
        Compute the average price for a Search within a time window.

        Args:
            search_id: UUID of the parent Search.
            since: Only include observations at or after this UTC timestamp.

        Returns:
            Average price as float, or None if no observations exist in the window.
        """
        result = (
            self._session.query(func.avg(PriceHistoryModel.price))
            .filter(
                PriceHistoryModel.search_id == search_id,
                PriceHistoryModel.scraped_at >= since,
            )
            .scalar()
        )
        return float(result) if result is not None else None

    def find_by_search(self, search_id: UUID, limit: int = 100) -> list[PriceHistory]:
        """
        Retrieve the most recent price observations for a Search.

        Args:
            search_id: UUID of the parent Search.
            limit: Maximum number of records to return (most recent first).

        Returns:
            List of PriceHistory entities ordered by scraped_at descending.
        """
        models = (
            self._session.query(PriceHistoryModel)
            .filter(PriceHistoryModel.search_id == search_id)
            .order_by(PriceHistoryModel.scraped_at.desc())
            .limit(limit)
            .all()
        )
        return [price_history_to_domain(m) for m in models]
