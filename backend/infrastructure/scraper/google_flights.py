"""
Playwright-based implementation of the FlightScraper port for Google Flights.

Opens Google Flights in a headless Chromium browser, navigates to the correct
search URL, waits for results to render, and parses flight cards into Flight
entities.

URL construction: Google Flights uses a base64-encoded protobuf parameter
called `tfs`. We build it directly from the search parameters — no hardcoded
dates or airport codes.

Selector strategy: Google's CSS class names change frequently (obfuscated
React output). We rely on ARIA roles, text extraction, and regex instead of
class-based selectors, which makes the parser resilient to UI rebuilds.
"""

import base64
import logging
import re
from datetime import date, datetime, timezone

from playwright.sync_api import Page, sync_playwright

from backend.domain.entities import Flight, Search, TripType
from backend.domain.ports import FlightScraper

logger = logging.getLogger(__name__)

_GF_BASE = "https://www.google.com/travel/flights/search"
_MAX_RESULTS = 10

# Known airline names used for text-matching in parsed results.
# Order matters: more specific names before shorter substrings
# (e.g. "Copa Airlines" before "Copa" would never match because Google shows "COPA").
_KNOWN_AIRLINES = [
    "Delta", "United", "American", "Southwest", "JetBlue", "Alaska",
    "British Airways", "Lufthansa", "Air France", "Emirates", "Qatar Airways",
    "KLM", "Turkish Airlines", "Iberia", "Virgin Atlantic", "Air Canada",
    "LATAM", "Aeromexico", "Copa", "Avianca", "Spirit", "Frontier",
    "Ryanair", "EasyJet", "Wizz Air", "Norwegian", "Finnair", "SAS",
    "Aer Lingus", "TAP Air Portugal", "Swiss", "Austrian",
]


def _build_tfs(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date | None,
    trip_type: TripType,
) -> str:
    """
    Encode the Google Flights `tfs` protobuf parameter for a search.

    The tfs parameter is a base64-encoded protobuf message that encodes the
    trip type, outbound leg (date + airports), and optional return leg.

    Protobuf structure (wire format, manually encoded):
      Field 1 (varint 28): flight search header constant
      Field 2 (varint):    trip type — 1 = one-way, 2 = round-trip
      Field 3 (bytes):     outbound leg
      Field 3 (bytes):     return leg (round-trip only)

    Each leg encodes:
      Field 2 (string): date "YYYY-MM-DD"
      Field 13 (bytes): origin  → {field 1: 1, field 2: "IATA"}
      Field 14 (bytes): destination → {field 1: 1, field 2: "IATA"}

    Args:
        origin: IATA departure code (e.g. "JFK").
        destination: IATA arrival code (e.g. "LHR").
        departure_date: Outbound travel date.
        return_date: Return date for round trips; None for one-way.
        trip_type: ONE_WAY or ROUND_TRIP.

    Returns:
        Base64-encoded string ready to be used as the `tfs` query parameter.
    """
    def _airport_bytes(code: str) -> bytes:
        """Encode a single airport as an inner protobuf message."""
        # field 1: varint 1   → 0x08 0x01
        # field 2: string "XXX" → 0x12 0x03 + 3 bytes
        inner = b"\x08\x01\x12\x03" + code.encode("ascii")
        return inner

    def _encode_leg(dep: date, from_code: str, to_code: str) -> bytes:
        """Encode one flight leg (date + origin + destination)."""
        date_str = dep.strftime("%Y-%m-%d").encode("ascii")
        # field 2: date string
        date_field = b"\x12" + bytes([len(date_str)]) + date_str
        # field 13: origin airport
        orig_inner = _airport_bytes(from_code)
        orig_field = b"\x6a" + bytes([len(orig_inner)]) + orig_inner
        # field 14: destination airport
        dest_inner = _airport_bytes(to_code)
        dest_field = b"\x72" + bytes([len(dest_inner)]) + dest_inner

        leg = date_field + orig_field + dest_field
        # field 3: this leg (length-delimited)
        return b"\x1a" + bytes([len(leg)]) + leg

    is_round = trip_type == TripType.ROUND_TRIP and return_date is not None

    payload = (
        b"\x08\x1c"                          # field 1: header constant 28
        + (b"\x10\x02" if is_round else b"\x10\x01")  # field 2: trip type
        + _encode_leg(departure_date, origin, destination)
    )

    if is_round:
        payload += _encode_leg(return_date, destination, origin)

    return base64.b64encode(payload).decode("ascii")


class GoogleFlightsScraper(FlightScraper):
    """
    Scrapes Google Flights using Playwright (headless Chromium).

    Each call to scrape() opens a new browser context to avoid session
    leakage between searches. Contexts are closed after each scrape
    regardless of outcome.
    """

    def scrape(self, search: Search) -> list[Flight]:
        """
        Navigate to Google Flights, wait for results, and return parsed flights.

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
                logger.info("Scraping: %s", url)
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                # Dismiss cookie/consent dialog if present (EU region)
                try:
                    page.click('button:has-text("Accept all")', timeout=4_000)
                except Exception:
                    pass

                # Wait until price data appears — [data-gs] is the reliable signal
                page.wait_for_selector("[data-gs]", timeout=20_000)
                flights = self._parse_results(page, search)
                logger.info(
                    "Search %s: parsed %d flights.", search.id, len(flights)
                )
            finally:
                context.close()
                browser.close()

        return flights

    def _build_url(self, search: Search) -> str:
        """
        Construct the Google Flights deep-link URL for a Search.

        Uses the `tfs` protobuf parameter to encode the full search —
        origin, destination, dates, and trip type.

        Args:
            search: The Search entity.

        Returns:
            Full Google Flights URL with encoded search parameters.
        """
        tfs = _build_tfs(
            origin=search.origin,
            destination=search.destination,
            departure_date=search.departure_date,
            return_date=search.return_date,
            trip_type=search.trip_type,
        )
        return f"{_GF_BASE}?tfs={tfs}&hl=en&gl=us&curr=USD"

    def _parse_results(self, page: Page, search: Search) -> list[Flight]:
        """
        Parse flight result cards from the rendered Google Flights page.

        Tries ARIA role selectors first. Falls back to a broader page-level
        search if the primary container is not found, so the parser survives
        minor UI changes between Google Flights deployments.

        Args:
            page: The Playwright Page with loaded search results.
            search: The originating Search entity.

        Returns:
            List of up to _MAX_RESULTS Flight entities.
        """
        scraped_at = datetime.now(timezone.utc)
        flights: list[Flight] = []

        # Strategy 1: flight result rows inside the results list.
        # Google Flights renders each flight as a <li> inside a <ul role="list">.
        # We filter to only those that contain a "$" price — the first few <li>
        # elements in the same list are passenger-count controls without prices.
        all_lis = page.query_selector_all('ul[role="list"] li')
        cards = [li for li in all_lis if re.search(r'\$\s*[\d,]+', li.inner_text())]

        # Strategy 2: fallback to [data-gs] if the primary structure is absent.
        if not cards:
            logger.warning(
                "No priced <li> found for search %s — trying [data-gs] fallback.",
                search.id,
            )
            cards = page.query_selector_all('[data-gs]')

        for card in cards[:_MAX_RESULTS]:
            try:
                flight = self._parse_card(card, search, scraped_at)
                if flight:
                    flights.append(flight)
            except Exception:
                logger.debug("Failed to parse a flight card — skipping.", exc_info=True)

        return flights

    def _parse_card(self, card, search: Search, scraped_at: datetime) -> Flight | None:
        """
        Extract a single Flight entity from a result card element.

        Uses text extraction with regex rather than fragile CSS class selectors,
        since Google's class names are obfuscated and change with every deploy.

        Args:
            card: A Playwright ElementHandle for one flight result card.
            search: The originating Search (provides route metadata).
            scraped_at: UTC timestamp to stamp the Flight snapshot.

        Returns:
            A Flight entity, or None if a price cannot be extracted.
        """
        text = card.inner_text()
        if not text.strip():
            return None

        # ── Price ────────────────────────────────────────────────────────────
        # Google Flights shows prices like "$1,234" or "$ 890"
        price_match = re.search(r"\$\s*([\d,]+)", text)
        if not price_match:
            return None
        price = float(price_match.group(1).replace(",", ""))

        # ── Duration ─────────────────────────────────────────────────────────
        # Formats: "10 hr 25 min" | "10hr 25min" | "10:25"
        dur_match = re.search(r"(\d+)\s*hr\s*(\d+)\s*min", text, re.IGNORECASE)
        if dur_match:
            duration_minutes = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
        else:
            hm_match = re.search(r"(\d+):(\d{2})", text)
            duration_minutes = (
                int(hm_match.group(1)) * 60 + int(hm_match.group(2))
                if hm_match else 0
            )

        # ── Stops ────────────────────────────────────────────────────────────
        if re.search(r"nonstop", text, re.IGNORECASE):
            stops = 0
        else:
            stops_match = re.search(r"(\d+)\s+stop", text, re.IGNORECASE)
            stops = int(stops_match.group(1)) if stops_match else 0

        # ── Airline ──────────────────────────────────────────────────────────
        airline = "Unknown"
        for name in _KNOWN_AIRLINES:
            if name.lower() in text.lower():
                airline = name
                break

        # ── URL ──────────────────────────────────────────────────────────────
        link_el = card.query_selector("a[href]")
        url: str = _GF_BASE
        if link_el:
            href = link_el.get_attribute("href") or ""
            url = href if href.startswith("http") else f"https://www.google.com{href}"

        return Flight(
            origin=search.origin,
            destination=search.destination,
            departure_date=search.departure_date,
            return_date=search.return_date,
            price=price,
            currency_code="USD",
            airline=airline,
            url=url,
            scraped_at=scraped_at,
            duration_minutes=duration_minutes,
            stops=stops,
        )
