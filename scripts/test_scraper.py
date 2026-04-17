"""
Standalone scraper diagnostic script.

Run from the project root:
    python scripts/test_scraper.py

No Docker, no Celery, no database needed — just Playwright.
Prints the generated URL, DOM element counts, and parsed flights.
Saves a screenshot to scripts/scraper_debug.png on any parse failure.
"""

import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timezone
from uuid import uuid4

from backend.domain.entities import Search, TripType
from backend.infrastructure.scraper.google_flights import GoogleFlightsScraper, _build_tfs

# ── Search parameters — edit these to test different routes ──────────────────
ORIGIN      = "BOG"
DESTINATION = "MIA"
DEPARTURE   = date(2026, 7, 15)
RETURN_DATE = date(2026, 7, 22)
TRIP_TYPE   = TripType.ROUND_TRIP
# ─────────────────────────────────────────────────────────────────────────────

SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "scraper_debug.png")


def main() -> None:
    search = Search(
        id=uuid4(),
        user_id=uuid4(),
        origin=ORIGIN,
        destination=DESTINATION,
        departure_date=DEPARTURE,
        return_date=RETURN_DATE,
        trip_type=TRIP_TYPE,
        threshold_pct=10.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        auto_purchase=False,
    )

    # ── 1. Show the URL we're about to hit ───────────────────────────────────
    tfs = _build_tfs(ORIGIN, DESTINATION, DEPARTURE, RETURN_DATE, TRIP_TYPE)
    url = f"https://www.google.com/travel/flights/search?tfs={tfs}&hl=en&gl=us&curr=USD"
    print("\n── URL ─────────────────────────────────────────────────────────────")
    print(url)
    print("\nPaste the URL above into your browser and verify it shows real results.")
    input("\nPress Enter to launch Playwright and run the scrape…")

    # ── 2. Run with verbose internal instrumentation ─────────────────────────
    print("\n── Running scraper ─────────────────────────────────────────────────")
    flights = _run_verbose(search)

    # ── 3. Report ────────────────────────────────────────────────────────────
    print(f"\n── Results: {len(flights)} flight(s) parsed ──────────────────────")
    if not flights:
        print("  ⚠  No flights parsed. Check scraper_debug.png for the page state.")
    for i, f in enumerate(flights, 1):
        print(
            f"  {i}. {f.airline:20s}  ${f.price:>7.0f}  "
            f"{f.duration_minutes // 60}h{f.duration_minutes % 60:02d}m  "
            f"{'nonstop' if f.stops == 0 else str(f.stops) + ' stop(s)'}"
        )


def _run_verbose(search: Search):
    """
    Run the scraper with extra diagnostic output and a fallback screenshot.
    """
    from playwright.sync_api import sync_playwright
    import re
    from backend.infrastructure.scraper.google_flights import (
        _GF_BASE,
        _KNOWN_AIRLINES,
        _MAX_RESULTS,
    )

    scraper = GoogleFlightsScraper()
    url = scraper._build_url(search)

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
        flights = []

        try:
            print(f"  → goto {url[:80]}…")
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            print(f"  → page title: {page.title()!r}")

            # Consent dialog
            try:
                page.click('button:has-text("Accept all")', timeout=4_000)
                print("  → dismissed consent dialog")
            except Exception:
                print("  → no consent dialog (or already dismissed)")

            # Wait for price signals
            print("  → waiting for price elements…")
            try:
                page.wait_for_selector(
                    '[aria-label*="$"], [data-gs], span:has-text("$")',
                    timeout=20_000,
                )
                print("  → price elements found ✓")
            except Exception:
                print("  ⚠  price selector timed out — saving screenshot")
                page.screenshot(path=SCREENSHOT_PATH, full_page=True)
                print(f"  → screenshot saved to {SCREENSHOT_PATH}")
                return []

            # Count candidate elements
            listitems = page.query_selector_all('[role="listitem"]')
            data_gs   = page.query_selector_all('[data-gs]')
            print(f"  → [role=listitem] count : {len(listitems)}")
            print(f"  → [data-gs]       count : {len(data_gs)}")

            if not listitems and not data_gs:
                print("  ⚠  no result cards found — saving screenshot")
                page.screenshot(path=SCREENSHOT_PATH, full_page=True)
                print(f"  → screenshot saved to {SCREENSHOT_PATH}")
                return []

            # Save screenshot regardless so we can inspect the page
            page.screenshot(path=SCREENSHOT_PATH, full_page=False)
            print(f"  → viewport screenshot saved to {SCREENSHOT_PATH}")

            cards = listitems or data_gs
            print(f"\n── Parsing {min(len(cards), _MAX_RESULTS)} cards ──────────────────────────────────")

            from datetime import datetime, timezone as tz
            scraped_at = datetime.now(tz.utc)

            for i, card in enumerate(cards[:_MAX_RESULTS]):
                text = card.inner_text().replace("\n", " ")
                price_match = re.search(r"\$\s*([\d,]+)", text)
                price_str   = price_match.group(0) if price_match else "no price"
                airline_found = next(
                    (n for n in _KNOWN_AIRLINES if n.lower() in text.lower()), "Unknown"
                )
                print(f"  card {i+1}: price={price_str:10s}  airline={airline_found:20s}  text[:80]={text[:80]!r}")

            flights = scraper._parse_results(page, search)

        except Exception as exc:
            print(f"  ✗ unexpected error: {exc}")
            try:
                page.screenshot(path=SCREENSHOT_PATH, full_page=True)
                print(f"  → screenshot saved to {SCREENSHOT_PATH}")
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    return flights


if __name__ == "__main__":
    main()
