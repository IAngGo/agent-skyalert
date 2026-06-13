"""
Result-card detection and parsing for the Kayak scraper.

Kayak's CSS class names are obfuscated and change between deploys, so
result cards are found by their text shape (price + at least two
"h:mm am/pm" times + a stop count) rather than by class selectors —
the same resilience strategy used by the Google Flights scraper.
"""

import logging
import re
from datetime import datetime

from backend.domain.entities import Flight, Search
from backend.infrastructure.scraper.google_flights import _KNOWN_AIRLINES

logger = logging.getLogger(__name__)

_MAX_RESULTS = 10

_TIME_RE = re.compile(r"\d{1,2}:\d{2}\s*(?:am|pm)", re.IGNORECASE)
_PRICE_RE = re.compile(r"\$\s*([\d,]+)")
_DURATION_RE = re.compile(r"(\d+)\s*h\s*(\d+)\s*m", re.IGNORECASE)
_STOPS_RE = re.compile(r"(\d+)\s*stop", re.IGNORECASE)

# In-browser filter: finds candidate result cards by text shape rather than
# by class name, since Kayak's classes are hashed and change between deploys.
CARD_FINDER_JS = """
() => {
    const timeRe = /\\d{1,2}:\\d{2}\\s*(am|pm)/gi;
    const priceRe = /\\$\\s*[\\d,]+/;
    const stopRe = /(nonstop|\\d+\\s*stop)/i;
    const out = [];
    for (const div of document.querySelectorAll('div')) {
        const t = div.innerText;
        if (!t || t.length < 50 || t.length > 500) continue;
        if (t.includes('Go to ')) continue;
        if (!priceRe.test(t)) continue;
        const times = t.match(timeRe);
        if (!times || times.length < 2) continue;
        if (!stopRe.test(t)) continue;
        out.push(t);
    }
    return out;
}
"""


def parse_results(
    texts: list[str], search: Search, scraped_at: datetime, build_url
) -> list[Flight]:
    """
    Parse candidate card texts into Flight entities.

    Args:
        texts: Inner-text strings of candidate result cards, as returned
            by CARD_FINDER_JS.
        search: The originating Search (provides route metadata).
        scraped_at: UTC timestamp to stamp each Flight snapshot.
        build_url: Callable that returns the deep-link URL for a Search.

    Returns:
        List of up to _MAX_RESULTS Flight entities, deduplicated by
        (price, airline, duration, stops).
    """
    flights: list[Flight] = []
    seen: set[tuple[float, str, int, int]] = set()
    for text in texts:
        try:
            flight = _parse_card(text, search, scraped_at, build_url)
        except Exception:
            logger.debug("Failed to parse a Kayak card — skipping.", exc_info=True)
            continue
        if flight is None:
            continue
        key = (flight.price, flight.airline, flight.duration_minutes, flight.stops)
        if key in seen:
            continue
        seen.add(key)
        flights.append(flight)
        if len(flights) >= _MAX_RESULTS:
            break

    return flights


def _parse_card(text: str, search: Search, scraped_at: datetime, build_url) -> Flight | None:
    """
    Extract a single Flight entity from a result card's text content.

    Args:
        text: The inner text of one candidate result card.
        search: The originating Search (provides route metadata).
        scraped_at: UTC timestamp to stamp the Flight snapshot.
        build_url: Callable that returns the deep-link URL for a Search.

    Returns:
        A Flight entity, or None if a price cannot be extracted.
    """
    # ── Price ────────────────────────────────────────────────────────────────
    price_match = _PRICE_RE.search(text)
    if not price_match:
        return None
    price = float(price_match.group(1).replace(",", ""))

    # ── Duration ─────────────────────────────────────────────────────────────
    # Outbound leg duration, e.g. "3h 50m".
    dur_match = _DURATION_RE.search(text)
    duration_minutes = (
        int(dur_match.group(1)) * 60 + int(dur_match.group(2)) if dur_match else 0
    )

    # ── Stops ────────────────────────────────────────────────────────────────
    if re.search(r"nonstop", text, re.IGNORECASE):
        stops = 0
    else:
        stops_match = _STOPS_RE.search(text)
        stops = int(stops_match.group(1)) if stops_match else 0

    # ── Airline ──────────────────────────────────────────────────────────────
    airline = "Unknown"
    for name in _KNOWN_AIRLINES:
        if name.lower() in text.lower():
            airline = name
            break

    return Flight(
        origin=search.origin,
        destination=search.destination,
        departure_date=search.departure_date,
        return_date=search.return_date,
        price=price,
        currency_code="USD",
        airline=airline,
        url=build_url(search),
        scraped_at=scraped_at,
        duration_minutes=duration_minutes,
        stops=stops,
        source="kayak",
    )
