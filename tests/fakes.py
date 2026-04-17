"""
In-memory fake implementations of all SkyAlert domain ports.

These fakes replace real infrastructure (PostgreSQL, SendGrid, Playwright, etc.)
during unit tests. Each fake stores state in a plain Python dict so tests can
inspect or pre-populate it directly.

No database, no network, no external processes — tests run in milliseconds.
"""

from datetime import datetime, timezone
from uuid import UUID

from backend.domain.entities import Alert, AlertStatus, Flight, PriceHistory, Search, User
from backend.domain.ports import (
    AlertRepository,
    FlightScraper,
    NotificationService,
    PriceHistoryRepository,
    PurchaseService,
    SearchRepository,
    UserRepository,
)


class InMemoryUserRepository(UserRepository):
    """Stores User entities in a dict keyed by UUID."""

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._store: dict[UUID, User] = {}

    def save(self, user: User) -> User:
        """Persist the user and return it unchanged."""
        self._store[user.id] = user
        return user

    def find_by_id(self, user_id: UUID) -> User | None:
        """Return the User with the given id, or None."""
        return self._store.get(user_id)

    def find_by_email(self, email: str) -> User | None:
        """Return the first User whose email matches, or None."""
        for user in self._store.values():
            if user.email == email:
                return user
        return None


class InMemorySearchRepository(SearchRepository):
    """Stores Search entities in a dict keyed by UUID."""

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._store: dict[UUID, Search] = {}

    def save(self, search: Search) -> Search:
        """Persist the search and return it unchanged."""
        self._store[search.id] = search
        return search

    def find_by_id(self, search_id: UUID) -> Search | None:
        """Return the Search with the given id, or None."""
        return self._store.get(search_id)

    def find_active(self) -> list[Search]:
        """Return all searches where is_active is True."""
        return [s for s in self._store.values() if s.is_active]

    def find_by_user(self, user_id: UUID) -> list[Search]:
        """Return all searches owned by the given user."""
        return [s for s in self._store.values() if s.user_id == user_id]


class InMemoryPriceHistoryRepository(PriceHistoryRepository):
    """Stores PriceHistory records in a list."""

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._records: list[PriceHistory] = []

    def save(self, record: PriceHistory) -> PriceHistory:
        """Persist the record and return it unchanged."""
        self._records.append(record)
        return record

    def get_average(self, search_id: UUID, since: datetime) -> float | None:
        """
        Compute the average price for a search since the given timestamp.

        Returns None if there are no observations in the window.
        """
        observations = [
            r for r in self._records
            if r.search_id == search_id and r.scraped_at >= since
        ]
        if not observations:
            return None
        return sum(r.price for r in observations) / len(observations)

    def find_by_search(self, search_id: UUID, limit: int = 100) -> list[PriceHistory]:
        """Return the most recent observations for a search, up to limit."""
        matching = [r for r in self._records if r.search_id == search_id]
        matching.sort(key=lambda r: r.scraped_at, reverse=True)
        return matching[:limit]


class InMemoryAlertRepository(AlertRepository):
    """Stores Alert entities in a dict keyed by UUID."""

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._store: dict[UUID, Alert] = {}

    def save(self, alert: Alert) -> Alert:
        """Persist the alert (insert or update) and return it unchanged."""
        self._store[alert.id] = alert
        return alert

    def find_by_id(self, alert_id: UUID) -> Alert | None:
        """Return the Alert with the given id, or None."""
        return self._store.get(alert_id)

    def find_by_search(self, search_id: UUID) -> list[Alert]:
        """Return all alerts associated with a search."""
        return [a for a in self._store.values() if a.search_id == search_id]

    def find_pending(self) -> list[Alert]:
        """Return all alerts with PENDING status."""
        return [a for a in self._store.values() if a.status == AlertStatus.PENDING]


class StubFlightScraper(FlightScraper):
    """
    Returns a pre-configured list of Flight objects without touching Google Flights.

    Tests set `scraper.flights` before executing a use case to control what
    the scraper "finds".
    """

    def __init__(self, flights: list[Flight] | None = None) -> None:
        """
        Args:
            flights: The list of flights to return on every scrape call.
                     Defaults to an empty list.
        """
        self.flights: list[Flight] = flights or []

    def scrape(self, search: Search) -> list[Flight]:
        """Return the pre-configured flight list."""
        return self.flights


class StubNotificationService(NotificationService):
    """
    Records every send_alert call and returns a configurable success/failure flag.

    Tests can inspect `notifier.calls` to verify what was sent and to whom.
    """

    def __init__(self, should_succeed: bool = True) -> None:
        """
        Args:
            should_succeed: Return value of every send_alert call.
        """
        self.should_succeed = should_succeed
        self.calls: list[tuple[User, Alert]] = []

    def send_alert(self, user: User, alert: Alert) -> bool:
        """Record the call and return the configured success flag."""
        self.calls.append((user, alert))
        return self.should_succeed


class StubPurchaseService(PurchaseService):
    """
    Records purchase attempts and returns a configurable success/failure flag.
    """

    def __init__(self, should_succeed: bool = True) -> None:
        """
        Args:
            should_succeed: Return value of every purchase call.
        """
        self.should_succeed = should_succeed
        self.calls: list[tuple[User, Flight]] = []

    def purchase(self, user: User, flight: Flight) -> bool:
        """Record the call and return the configured success flag."""
        self.calls.append((user, flight))
        return self.should_succeed
