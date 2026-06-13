"""
Playwright-based implementation of the FlightScraper port for Kayak.

Acts as a second, independent price source so SkyAlert's price history
doesn't rely solely on Google Flights. Combined with GoogleFlightsScraper
via CompositeFlightScraper.

URL construction: Kayak's flight search URL is a simple path of
origin/destination/dates — no encoded protobuf parameter is needed.

Card parsing lives in kayak_parser.py — see that module for the
resilience strategy (text-shape matching instead of class selectors).
"""

import logging
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from backend.domain.entities import Flight, Search, TripType
from backend.domain.ports import FlightScraper
from backend.infrastructure.scraper.kayak_parser import CARD_FINDER_JS, parse_results

logger = logging.getLogger(__name__)

_KAYAK_BASE = "https://www.kayak.com/flights"


class KayakScraper(FlightScraper):
    """
    Scrapes Kayak using Playwright (headless Chromium).

    Each call to scrape() opens a new browser context to avoid session
    leakage between searches. Contexts are closed after each scrape
    regardless of outcome.
    """

    def scrape(self, search: Search) -> list[Flight]:
        """
        Navigate to Kayak, wait for results, and return parsed flights.

        Args:
            search: The Search entity defining origin, destination, dates, and trip type.

        Returns:
            List of Flight snapshots. Empty list on any error.
        """
        try:
            return self._run_scrape(search)
        except Exception:
            logger.exception(
                "KayakScraper failed for search %s (%s → %s).",
                search.id,
                search.origin,
                search.destination,
            )
            return []

    def _run_scrape(self, search: Search) -> list[Flight]:
        """
        Execute the Playwright session and return parsed results.

        Args:
            search: The Search entity to scrape.

        Returns:
            List of parsed Flight entities.
        """
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                locale="en-US",
                timezone_id="UTC",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            try:
                url = self._build_url(search)
                logger.info("Scraping: %s", url)
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                # Dismiss cookie/consent dialog if present (EU region)
                try:
                    page.click('button:has-text("Accept")', timeout=4_000)
                except Exception:
                    pass

                # Kayak's price elements load asynchronously and are not
                # reliably reported as "visible" by Playwright, so we give
                # the results panel a fixed window to populate instead of
                # waiting on a selector.
                page.wait_for_timeout(7_000)

                texts: list[str] = page.evaluate(CARD_FINDER_JS)
                scraped_at = datetime.now(timezone.utc)
                flights = parse_results(texts, search, scraped_at, self._build_url)
                logger.info(
                    "Search %s: parsed %d flights from Kayak.", search.id, len(flights)
                )
            finally:
                context.close()
                browser.close()

        return flights

    def _build_url(self, search: Search) -> str:
        """
        Construct the Kayak flight search URL for a Search.

        Args:
            search: The Search entity.

        Returns:
            Full Kayak URL with origin, destination, and dates in the path.
        """
        path = f"{search.origin}-{search.destination}/{search.departure_date.isoformat()}"
        if search.trip_type == TripType.ROUND_TRIP and search.return_date is not None:
            path += f"/{search.return_date.isoformat()}"
        return f"{_KAYAK_BASE}/{path}?currency=USD"
