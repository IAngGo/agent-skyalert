"""
Unit tests for the EvaluatePriceDrop use case.

This use case contains the core business logic of SkyAlert:
"Is this price drop big enough to alert the user?"

Cases under test:
1. Drop meets threshold → Alert is created and persisted.
2. Drop is below threshold → returns None, no alert created.
3. Price history is insufficient → InsufficientPriceHistoryError.
4. Search does not exist → SearchNotFoundError.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.application.commands import EvaluatePriceDropCommand
from backend.application.exceptions import (
    InsufficientPriceHistoryError,
    SearchNotFoundError,
)
from backend.application.use_cases.evaluate_price_drop import EvaluatePriceDrop
from backend.domain.entities import AlertStatus, Flight, PriceHistory
from tests.fakes import (
    InMemoryAlertRepository,
    InMemoryPriceHistoryRepository,
    InMemorySearchRepository,
    InMemoryUserRepository,
    StubFlightScraper,
)


def make_use_case(
    searches: InMemorySearchRepository,
    price_history: InMemoryPriceHistoryRepository,
    alerts: InMemoryAlertRepository,
    scraper: StubFlightScraper,
) -> EvaluatePriceDrop:
    """Construct EvaluatePriceDrop with the given fakes."""
    return EvaluatePriceDrop(
        searches=searches,
        price_history=price_history,
        alerts=alerts,
        scraper=scraper,
    )


def seed_price_history(
    repo: InMemoryPriceHistoryRepository,
    search_id,
    prices: list[float],
    days_ago: int = 1,
) -> None:
    """
    Helper: insert price observations into the repository.

    All observations are stamped within the last `days_ago` days so they
    fall inside the default 7-day history window used by EvaluatePriceDrop.
    """
    base = datetime.now(timezone.utc) - timedelta(days=days_ago - 1)
    for i, price in enumerate(prices):
        repo.save(PriceHistory(
            id=uuid4(),
            search_id=search_id,
            price=price,
            currency_code="USD",
            scraped_at=base + timedelta(hours=i),
        ))


class TestEvaluatePriceDrop:
    """Tests for EvaluatePriceDrop.execute()."""

    def test_creates_alert_when_drop_meets_threshold(
        self,
        searches: InMemorySearchRepository,
        price_history: InMemoryPriceHistoryRepository,
        alerts: InMemoryAlertRepository,
        scraper: StubFlightScraper,
        sample_search,
        sample_flight: Flight,
    ) -> None:
        """
        Historical avg = 500, current = 400, drop = 20 %, threshold = 10 %.
        Expect an Alert with PENDING status to be created.
        """
        seed_price_history(price_history, sample_search.id, [500.0, 510.0, 490.0])
        scraper.flights = [sample_flight]

        use_case = make_use_case(searches, price_history, alerts, scraper)
        cmd = EvaluatePriceDropCommand(
            search_id=sample_search.id,
            current_price=400.0,
            currency_code="USD",
        )

        result = use_case.execute(cmd)

        assert result is not None
        assert result.status == AlertStatus.PENDING
        assert result.drop_pct > sample_search.threshold_pct
        assert alerts.find_by_id(result.id) is not None

    def test_returns_none_when_drop_below_threshold(
        self,
        searches: InMemorySearchRepository,
        price_history: InMemoryPriceHistoryRepository,
        alerts: InMemoryAlertRepository,
        scraper: StubFlightScraper,
        sample_search,
    ) -> None:
        """
        Historical avg = 500, current = 490, drop = 2 %, threshold = 10 %.
        Expect None — no alert created.
        """
        seed_price_history(price_history, sample_search.id, [500.0, 500.0, 500.0])

        use_case = make_use_case(searches, price_history, alerts, scraper)
        cmd = EvaluatePriceDropCommand(
            search_id=sample_search.id,
            current_price=490.0,
            currency_code="USD",
        )

        result = use_case.execute(cmd)

        assert result is None
        assert alerts.find_pending() == []

    def test_raises_when_history_insufficient(
        self,
        searches: InMemorySearchRepository,
        price_history: InMemoryPriceHistoryRepository,
        alerts: InMemoryAlertRepository,
        scraper: StubFlightScraper,
        sample_search,
    ) -> None:
        """
        Zero observations in the window → InsufficientPriceHistoryError.
        No alert should be created.
        """
        # No history seeded — the window returns None from get_average.
        use_case = make_use_case(searches, price_history, alerts, scraper)
        cmd = EvaluatePriceDropCommand(
            search_id=sample_search.id,
            current_price=450.0,
            currency_code="USD",
        )

        with pytest.raises(InsufficientPriceHistoryError):
            use_case.execute(cmd)

        assert alerts.find_pending() == []

    def test_raises_when_search_not_found(
        self,
        searches: InMemorySearchRepository,
        price_history: InMemoryPriceHistoryRepository,
        alerts: InMemoryAlertRepository,
        scraper: StubFlightScraper,
    ) -> None:
        """A search_id that does not exist raises SearchNotFoundError."""
        use_case = make_use_case(searches, price_history, alerts, scraper)
        cmd = EvaluatePriceDropCommand(
            search_id=uuid4(),
            current_price=450.0,
            currency_code="USD",
        )

        with pytest.raises(SearchNotFoundError):
            use_case.execute(cmd)
