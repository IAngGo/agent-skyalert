"""
Use case: Evaluate whether a scraped price constitutes a price-drop alert.

Called by RunPriceScrape after each successful scrape.
Computes the rolling historical average and compares it to the current price.
Creates an Alert entity if the drop meets the Search threshold.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.application.commands import EvaluatePriceDropCommand
from backend.application.exceptions import (
    InsufficientPriceHistoryError,
    SearchNotFoundError,
)
from backend.domain.entities import Alert, AlertStatus, Flight
from backend.domain.ports import (
    AlertRepository,
    FlightScraper,
    PriceHistoryRepository,
    SearchRepository,
)

# Minimum observations required before we consider an average meaningful.
MIN_OBSERVATIONS = 3


class EvaluatePriceDrop:
    """
    Compute the rolling average for a Search and create an Alert if warranted.

    The drop percentage is calculated as:
        drop_pct = (historical_avg - current_price) / historical_avg * 100

    An Alert is created only when drop_pct >= search.threshold_pct.
    If history is insufficient, InsufficientPriceHistoryError is raised so
    the caller (RunPriceScrape) can log and skip without crashing.
    """

    def __init__(
        self,
        searches: SearchRepository,
        price_history: PriceHistoryRepository,
        alerts: AlertRepository,
        scraper: FlightScraper,
    ) -> None:
        """
        Args:
            searches: Port for retrieving Search entities.
            price_history: Port for reading historical price observations.
            alerts: Port for persisting new Alert entities.
            scraper: Port for fetching the flight snapshot to attach to the alert.
        """
        self._searches = searches
        self._price_history = price_history
        self._alerts = alerts
        self._scraper = scraper

    def execute(self, command: EvaluatePriceDropCommand) -> Alert | None:
        """
        Evaluate a price against the rolling historical average.

        Args:
            command: Contains search_id, current_price, currency_code,
                     and history_window_days.

        Returns:
            A persisted Alert if a drop was detected, None otherwise.

        Raises:
            SearchNotFoundError: If no Search exists with command.search_id.
            InsufficientPriceHistoryError: If fewer than MIN_OBSERVATIONS
                exist within the history window.
        """
        search = self._searches.find_by_id(command.search_id)
        if search is None:
            raise SearchNotFoundError(command.search_id)

        since = datetime.now(timezone.utc) - timedelta(days=command.history_window_days)
        historical_avg = self._price_history.get_average(search.id, since=since)

        if historical_avg is None:
            observations = self._price_history.find_by_search(search.id, limit=MIN_OBSERVATIONS)
            raise InsufficientPriceHistoryError(
                search_id=search.id,
                required=MIN_OBSERVATIONS,
                available=len(observations),
            )

        drop_pct = (historical_avg - command.current_price) / historical_avg * 100

        if drop_pct < search.threshold_pct:
            return None

        flights: list[Flight] = self._scraper.scrape(search)
        if not flights:
            return None
        cheapest: Flight = min(flights, key=lambda f: f.price)

        alert = Alert(
            id=uuid4(),
            search_id=search.id,
            flight=cheapest,
            historical_avg=historical_avg,
            current_price=command.current_price,
            drop_pct=drop_pct,
            status=AlertStatus.PENDING,
            triggered_at=datetime.now(timezone.utc),
        )

        return self._alerts.save(alert)
