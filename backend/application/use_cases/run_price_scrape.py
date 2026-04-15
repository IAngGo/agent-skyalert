"""
Use case: Run a price scrape for a single active Search.

Called by the Celery beat task every 5 minutes for each active Search.
Scrapes current flights, records each price in history, then hands off
to EvaluatePriceDrop for alert detection.
"""

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.commands import EvaluatePriceDropCommand, RunPriceScrapeCommand
from backend.application.exceptions import SearchInactiveError, SearchNotFoundError
from backend.application.use_cases.evaluate_price_drop import EvaluatePriceDrop
from backend.domain.entities import Flight, PriceHistory
from backend.domain.ports import (
    FlightScraper,
    PriceHistoryRepository,
    SearchRepository,
)


class RunPriceScrape:
    """
    Scrape current flight prices for a Search and record observations.

    For each flight returned by the scraper:
    1. Persist a PriceHistory record.
    2. Delegate to EvaluatePriceDrop to check for an alert condition.

    Only the cheapest flight per scrape run is evaluated for a drop,
    to avoid duplicate alerts for the same market movement.
    """

    def __init__(
        self,
        searches: SearchRepository,
        price_history: PriceHistoryRepository,
        scraper: FlightScraper,
        evaluate_price_drop: EvaluatePriceDrop,
    ) -> None:
        """
        Args:
            searches: Port for retrieving Search entities.
            price_history: Port for persisting price observations.
            scraper: Port for fetching live flight data.
            evaluate_price_drop: Use case for alert detection (injected to avoid duplication).
        """
        self._searches = searches
        self._price_history = price_history
        self._scraper = scraper
        self._evaluate = evaluate_price_drop

    def execute(self, command: RunPriceScrapeCommand) -> list[PriceHistory]:
        """
        Scrape prices for the given Search and evaluate the cheapest result.

        Args:
            command: Contains the search_id to scrape.

        Returns:
            List of PriceHistory records persisted during this run.

        Raises:
            SearchNotFoundError: If no Search exists with command.search_id.
            SearchInactiveError: If the Search is not currently active.
        """
        search = self._searches.find_by_id(command.search_id)
        if search is None:
            raise SearchNotFoundError(command.search_id)
        if not search.is_active:
            raise SearchInactiveError(command.search_id)

        flights: list[Flight] = self._scraper.scrape(search)
        if not flights:
            return []

        records: list[PriceHistory] = []
        for flight in flights:
            record = PriceHistory(
                id=uuid4(),
                search_id=search.id,
                price=flight.price,
                currency_code=flight.currency_code,
                scraped_at=datetime.now(timezone.utc),
            )
            records.append(self._price_history.save(record))

        cheapest: Flight = min(flights, key=lambda f: f.price)
        self._evaluate.execute(
            EvaluatePriceDropCommand(
                search_id=search.id,
                current_price=cheapest.price,
                currency_code=cheapest.currency_code,
            )
        )

        return records
