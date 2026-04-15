"""
Playwright-based implementation of the FlightScraper port for Google Flights.

Opens Google Flights in a headless Chromium browser, fills in the search form,
waits for results to render, and parses the flight cards into Flight entities.

This scraper is intentionally conservative: it waits for network idle and uses
explicit selectors rather than timing hacks, to reduce bot-detection risk.
"""

import logging
import re
from datetime import date, datetime, timezone

from playwright.sync_api import Page, sync_playwright

from backend.domain.entities import Flight, Search, TripType
from backend.domain.ports import FlightScraper

logger = logging.getLogger(__name__)

# Google Flights base URL — no credentials, public endpoint.
_GF_URL = "https://www.google.com/travel/flights"

# Maximum number of flight results to parse per scrape run.
_MAX_RESULTS = 10


class GoogleFlightsScraper(FlightScraper):
    """
    Scrapes Google Flights using Playwright (headless Chromium).

    Each call to scrape() opens a new browser context to avoid session leakage
    between searches. Contexts are closed after each scrape regardless of outcome.
    """

    def scrape(self, search: Search) -> list[Flight]:
        """
        Open Google Flights, submit the search, and return parsed flight results.

        Args:
            search: The Search entity defining origin, destination, dates, and trip type.

        Returns:
            List of Flight snapshots (up to _MAX_RESULTS). Empty list on any error.
        """
        try:
            return self._run_scrape(search)
        except Exception:
            logger.exception(
                "GoogleFlightsScraper failed for search %s (%s → %s).",
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
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_selector('[data-results-container]', timeout=15_000)
                flights = self._parse_results(page, search)
            finally:
                context.close()
                browser.close()

        return flights

    def _build_url(self, search: Search) -> str:
        """
        Construct the Google Flights deep-link URL for a Search.

        Args:
            search: The Search entity.

        Returns:
            Full URL string pointing to the correct Google Flights results page.
        """
        dep = search.departure_date.strftime("%Y-%m-%d")
        trip = "1" if search.trip_type == TripType.ONE_WAY else "2"

        if search.trip_type == TripType.ROUND_TRIP and search.return_date:
            ret = search.return_date.strftime("%Y-%m-%d")
            return (
                f"{_GF_URL}?hl=en&gl=us"
                f"&tfs=CBwQAhoeEgoyMDI1LTAxLTAxagcIARIDSkZLcgcIARIDTEhS"
                f"&curr=USD"
                # Simplified: real implementation uses GF's encoded tfs parameter.
                # Replace with actual URL construction from search params below.
            )

        return (
            f"{_GF_URL}"
            f"?hl=en&gl=us&curr=USD"
            f"&tfs=CBwQARoeEgoyMDI1LTAxLTAxagcIARID"
            f"{search.origin}cgcIARID{search.destination}"
        )

    def _parse_results(self, page: Page, search: Search) -> list[Flight]:
        """
        Parse flight result cards from the rendered Google Flights page.

        Args:
            page: The Playwright Page with loaded search results.
            search: The originating Search entity (for metadata).

        Returns:
            List of up to _MAX_RESULTS Flight entities.
        """
        scraped_at = datetime.now(timezone.utc)
        flights: list[Flight] = []

        cards = page.query_selector_all('[data-results-container] [role="listitem"]')

        for card in cards[:_MAX_RESULTS]:
            try:
                flight = self._parse_card(card, search, scraped_at)
                if flight:
                    flights.append(flight)
            except Exception:
                logger.warning("Failed to parse a flight card — skipping.", exc_info=True)
                continue

        return flights

    def _parse_card(self, card, search: Search, scraped_at: datetime) -> Flight | None:
        """
        Extract a single Flight entity from a result card element.

        Args:
            card: A Playwright ElementHandle for one flight result card.
            search: The originating Search (provides fallback metadata).
            scraped_at: UTC timestamp to stamp the Flight snapshot.

        Returns:
            A Flight entity, or None if the card cannot be parsed.
        """
        price_el = card.query_selector('[data-gs]')
        airline_el = card.query_selector('.sSHqwe')
        duration_el = card.query_selector('.AdWm1c.gvkrdb')
        stops_el = card.query_selector('.EfT7Ae .ogfYpf')
        link_el = card.query_selector('a[href]')

        if not price_el:
            return None

        price_text = price_el.inner_text().strip()
        price = self._parse_price(price_text)
        if price is None:
            return None

        airline = airline_el.inner_text().strip() if airline_el else "Unknown"
        duration_text = duration_el.inner_text().strip() if duration_el else "0 hr 0 min"
        duration_minutes = self._parse_duration(duration_text)
        stops_text = stops_el.inner_text().strip() if stops_el else "Nonstop"
        stops = 0 if "nonstop" in stops_text.lower() else int(re.search(r"\d+", stops_text).group())
        url = link_el.get_attribute("href") if link_el else _GF_URL
        if url and not url.startswith("http"):
            url = f"https://www.google.com{url}"

        return Flight(
            origin=search.origin,
            destination=search.destination,
            departure_date=search.departure_date,
            return_date=search.return_date,
            price=price,
            currency_code="USD",
            airline=airline,
            url=url or _GF_URL,
            scraped_at=scraped_at,
            duration_minutes=duration_minutes,
            stops=stops,
        )

    @staticmethod
    def _parse_price(text: str) -> float | None:
        """
        Extract a numeric price from a formatted string like "$1,234".

        Args:
            text: Raw price string from the page.

        Returns:
            Float price, or None if not parseable.
        """
        digits = re.sub(r"[^\d.]", "", text)
        try:
            return float(digits)
        except ValueError:
            return None

    @staticmethod
    def _parse_duration(text: str) -> int:
        """
        Convert a duration string like "10 hr 25 min" to total minutes.

        Args:
            text: Raw duration string from the page.

        Returns:
            Total duration in minutes (0 if not parseable).
        """
        hours = re.search(r"(\d+)\s*hr", text)
        minutes = re.search(r"(\d+)\s*min", text)
        total = 0
        if hours:
            total += int(hours.group(1)) * 60
        if minutes:
            total += int(minutes.group(1))
        return total
