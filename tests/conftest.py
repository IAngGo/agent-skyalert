"""
Shared pytest fixtures for SkyAlert unit tests.

Each fixture returns a fresh fake repository or service so tests are
fully isolated — no state leaks between test functions.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from backend.domain.entities import (
    Alert,
    AlertStatus,
    Flight,
    PriceHistory,
    Search,
    TripType,
    User,
)
from tests.fakes import (
    InMemoryAlertRepository,
    InMemoryPriceHistoryRepository,
    InMemorySearchRepository,
    InMemoryUserRepository,
    StubFlightScraper,
    StubNotificationService,
    StubPurchaseService,
)


# ---------------------------------------------------------------------------
# Repository fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Fresh in-memory UserRepository."""
    return InMemoryUserRepository()


@pytest.fixture
def searches() -> InMemorySearchRepository:
    """Fresh in-memory SearchRepository."""
    return InMemorySearchRepository()


@pytest.fixture
def price_history() -> InMemoryPriceHistoryRepository:
    """Fresh in-memory PriceHistoryRepository."""
    return InMemoryPriceHistoryRepository()


@pytest.fixture
def alerts() -> InMemoryAlertRepository:
    """Fresh in-memory AlertRepository."""
    return InMemoryAlertRepository()


# ---------------------------------------------------------------------------
# Service fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper() -> StubFlightScraper:
    """Flight scraper stub that returns an empty list by default."""
    return StubFlightScraper()


@pytest.fixture
def notifier() -> StubNotificationService:
    """Notification stub that succeeds by default."""
    return StubNotificationService(should_succeed=True)


@pytest.fixture
def purchase() -> StubPurchaseService:
    """Purchase stub that succeeds by default."""
    return StubPurchaseService(should_succeed=True)


# ---------------------------------------------------------------------------
# Domain object factories
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_user(users: InMemoryUserRepository) -> User:
    """A persisted User ready for use in tests."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        phone="+12125551234",
        whatsapp_enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    users.save(user)
    return user


@pytest.fixture
def sample_search(searches: InMemorySearchRepository, sample_user: User) -> Search:
    """A persisted active Search owned by sample_user."""
    search = Search(
        id=uuid4(),
        user_id=sample_user.id,
        origin="JFK",
        destination="LHR",
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 15),
        trip_type=TripType.ROUND_TRIP,
        threshold_pct=10.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    searches.save(search)
    return search


@pytest.fixture
def sample_flight() -> Flight:
    """A Flight snapshot for use in alert tests."""
    return Flight(
        origin="JFK",
        destination="LHR",
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 15),
        price=450.00,
        currency_code="USD",
        airline="British Airways",
        url="https://flights.google.com/search?q=JFK-LHR",
        scraped_at=datetime.now(timezone.utc),
        duration_minutes=420,
        stops=0,
    )


@pytest.fixture
def sample_sent_alert(
    alerts: InMemoryAlertRepository,
    sample_search: Search,
    sample_flight: Flight,
) -> Alert:
    """A persisted Alert in SENT status, ready to be confirmed."""
    alert = Alert(
        id=uuid4(),
        search_id=sample_search.id,
        flight=sample_flight,
        historical_avg=550.00,
        current_price=450.00,
        drop_pct=18.18,
        status=AlertStatus.SENT,
        triggered_at=datetime.now(timezone.utc),
        notified_at=datetime.now(timezone.utc),
    )
    alerts.save(alert)
    return alert
