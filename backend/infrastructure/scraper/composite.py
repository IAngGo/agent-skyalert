"""
Composite FlightScraper that combines multiple price sources.

This is the adapter injected into RunPriceScrape in production.
It runs each registered scraper and concatenates their results, so
price history reflects offers from every configured site (e.g. Google
Flights and Kayak) rather than a single source.
"""

import logging

from backend.domain.entities import Flight, Search
from backend.domain.ports import FlightScraper

logger = logging.getLogger(__name__)


class CompositeFlightScraper(FlightScraper):
    """
    Scrapes flight prices through multiple FlightScraper adapters in sequence.

    A failure in one scraper does not prevent the others from running —
    each is wrapped individually, and the combined results from all
    successful scrapers are returned.

    Typical usage in production:
        CompositeFlightScraper([
            GoogleFlightsScraper(),
            KayakScraper(),
        ])
    """

    def __init__(self, scrapers: list[FlightScraper]) -> None:
        """
        Args:
            scrapers: Ordered list of scraper adapters to run.
                      At least one must be provided.

        Raises:
            ValueError: If the scrapers list is empty.
        """
        if not scrapers:
            raise ValueError("CompositeFlightScraper requires at least one scraper.")
        self._scrapers = scrapers

    def scrape(self, search: Search) -> list[Flight]:
        """
        Run every registered scraper and concatenate their results.

        Args:
            search: The Search entity defining origin, destination, dates, and trip type.

        Returns:
            Combined list of Flight snapshots from all scrapers. A scraper
            that raises or returns nothing simply contributes no flights.
        """
        all_flights: list[Flight] = []

        for scraper in self._scrapers:
            try:
                flights = scraper.scrape(search)
                logger.info(
                    "%s found %d flight(s) for search %s",
                    type(scraper).__name__,
                    len(flights),
                    search.id,
                )
                all_flights.extend(flights)
            except Exception:
                logger.exception(
                    "Unexpected error in %s for search %s",
                    type(scraper).__name__,
                    search.id,
                )

        return all_flights
