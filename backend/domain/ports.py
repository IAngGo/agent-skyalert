"""
Abstract port definitions for SkyAlert.

Ports are interfaces (abstract base classes) that the application layer depends on.
Concrete implementations live in infrastructure/ and are injected at runtime.

Dependency rule: this file imports only from the Python standard library
and from domain.entities — never from infrastructure.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from backend.domain.entities import Alert, AlertStatus, Flight, PriceHistory, Search, User


# ---------------------------------------------------------------------------
# Repository ports  (persistence boundary)
# ---------------------------------------------------------------------------


class UserRepository(ABC):
    """Port for persisting and retrieving User entities."""

    @abstractmethod
    def save(self, user: User) -> User:
        """
        Persist a new User or update an existing one.

        Args:
            user: The User entity to persist.

        Returns:
            The saved User (may include DB-generated fields).
        """

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> User | None:
        """
        Retrieve a User by its primary key.

        Args:
            user_id: UUID of the target User.

        Returns:
            The User if found, None otherwise.
        """

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        """
        Retrieve a User by email address.

        Args:
            email: The email to look up.

        Returns:
            The User if found, None otherwise.
        """


class SearchRepository(ABC):
    """Port for persisting and retrieving Search configurations."""

    @abstractmethod
    def save(self, search: Search) -> Search:
        """
        Persist a new Search or update an existing one.

        Args:
            search: The Search entity to persist.

        Returns:
            The saved Search.
        """

    @abstractmethod
    def find_by_id(self, search_id: UUID) -> Search | None:
        """
        Retrieve a Search by its primary key.

        Args:
            search_id: UUID of the target Search.

        Returns:
            The Search if found, None otherwise.
        """

    @abstractmethod
    def find_active(self) -> list[Search]:
        """
        Retrieve all active Search configurations.

        Returns:
            List of Search entities with is_active == True.
        """

    @abstractmethod
    def find_by_user(self, user_id: UUID) -> list[Search]:
        """
        Retrieve all Searches owned by a given User.

        Args:
            user_id: UUID of the owning User.

        Returns:
            List of Search entities for that user.
        """


class PriceHistoryRepository(ABC):
    """Port for persisting and querying flight price history."""

    @abstractmethod
    def save(self, record: PriceHistory) -> PriceHistory:
        """
        Persist a new PriceHistory observation.

        Args:
            record: The PriceHistory entity to persist.

        Returns:
            The saved record.
        """

    @abstractmethod
    def get_average(self, search_id: UUID, since: datetime) -> float | None:
        """
        Compute the rolling average price for a Search since a given time.

        Args:
            search_id: UUID of the parent Search.
            since: Only consider observations at or after this UTC timestamp.

        Returns:
            Average price as a float, or None if there are no observations yet.
        """

    @abstractmethod
    def find_by_search(self, search_id: UUID, limit: int = 100) -> list[PriceHistory]:
        """
        Retrieve the most recent price observations for a Search.

        Args:
            search_id: UUID of the parent Search.
            limit: Maximum number of records to return (most recent first).

        Returns:
            List of PriceHistory entities ordered by scraped_at descending.
        """


class AlertRepository(ABC):
    """Port for persisting and retrieving Alert entities."""

    @abstractmethod
    def save(self, alert: Alert) -> Alert:
        """
        Persist a new Alert or update an existing one.

        Args:
            alert: The Alert entity to persist.

        Returns:
            The saved Alert.
        """

    @abstractmethod
    def find_by_id(self, alert_id: UUID) -> Alert | None:
        """
        Retrieve an Alert by its primary key.

        Args:
            alert_id: UUID of the target Alert.

        Returns:
            The Alert if found, None otherwise.
        """

    @abstractmethod
    def find_by_search(self, search_id: UUID) -> list[Alert]:
        """
        Retrieve all Alerts associated with a Search.

        Args:
            search_id: UUID of the parent Search.

        Returns:
            List of Alert entities.
        """

    @abstractmethod
    def find_pending(self) -> list[Alert]:
        """
        Retrieve all Alerts with PENDING status awaiting notification.

        Returns:
            List of Alert entities with status == AlertStatus.PENDING.
        """


# ---------------------------------------------------------------------------
# Service ports  (external system boundary)
# ---------------------------------------------------------------------------


class FlightScraper(ABC):
    """Port for scraping live flight prices from an external source."""

    @abstractmethod
    def scrape(self, search: Search) -> list[Flight]:
        """
        Scrape current flight options matching the given Search parameters.

        Args:
            search: The Search whose parameters define what to scrape.

        Returns:
            List of Flight snapshots found (may be empty if no results).
        """


class NotificationService(ABC):
    """Port for dispatching alert notifications to users."""

    @abstractmethod
    def send_alert(self, user: User, alert: Alert) -> bool:
        """
        Notify a user about a detected price drop.

        Args:
            user: The User to notify.
            alert: The Alert containing drop details and flight snapshot.

        Returns:
            True if the notification was dispatched successfully, False otherwise.
        """


class PurchaseService(ABC):
    """Port for triggering an automatic flight purchase on behalf of a user."""

    @abstractmethod
    def purchase(self, user: User, flight: Flight) -> bool:
        """
        Initiate a flight purchase for the given user and flight snapshot.

        Args:
            user: The User on whose behalf to purchase.
            flight: The Flight snapshot (contains the deep-link URL and details).

        Returns:
            True if the purchase was initiated successfully, False otherwise.
        """
