"""
Core domain entities for SkyAlert.

These are pure Python dataclasses — no external dependencies, no ORM annotations,
no framework imports. They represent what the business deals with, not how data
is stored or transported.

Dependency rule: this file imports only from the Python standard library.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import UUID


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AlertStatus(str, Enum):
    """Lifecycle states of an Alert."""

    PENDING = "pending"       # Detected, not yet sent to the user.
    SENT = "sent"             # Notification dispatched successfully.
    CONFIRMED = "confirmed"   # User acknowledged / triggered purchase.
    EXPIRED = "expired"       # Price rebounded before user acted.
    FAILED = "failed"         # Notification delivery failed.


class TripType(str, Enum):
    """Whether the search covers a one-way or round trip."""

    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass
class User:
    """
    A registered SkyAlert user.

    Attributes:
        id: Unique identifier (UUID).
        email: Address used for SendGrid notifications.
        phone: E.164-formatted phone number used for Twilio WhatsApp.
        whatsapp_enabled: Whether the user opted into WhatsApp alerts.
        created_at: UTC timestamp of account creation.
    """

    id: UUID
    email: str
    phone: str
    whatsapp_enabled: bool
    created_at: datetime


@dataclass
class Flight:
    """
    A single flight option captured from a Google Flights scrape.

    This is a value snapshot — it reflects the price and details at the
    exact moment it was scraped.  It is not mutated after creation.

    Attributes:
        origin: IATA airport code (e.g. "JFK").
        destination: IATA airport code (e.g. "LHR").
        departure_date: Outbound travel date.
        return_date: Return date for round trips; None for one-way.
        price: Fare in the currency indicated by currency_code.
        currency_code: ISO 4217 code (e.g. "USD").
        airline: Marketing carrier name (e.g. "Delta").
        url: Deep-link to the offer on Google Flights.
        scraped_at: UTC timestamp of when this snapshot was taken.
        duration_minutes: Total flight duration in minutes (layovers included).
        stops: Number of layovers (0 = non-stop).
    """

    origin: str
    destination: str
    departure_date: date
    return_date: date | None
    price: float
    currency_code: str
    airline: str
    url: str
    scraped_at: datetime
    duration_minutes: int
    stops: int


@dataclass
class Search:
    """
    A saved flight-monitoring configuration created by a user.

    The search defines *what* to watch and *when* to fire an alert.
    The threshold_pct field controls sensitivity: a value of 10 means
    "alert me when the price drops more than 10 % below the rolling average."

    Attributes:
        id: Unique identifier (UUID).
        user_id: References the owning User.
        origin: Departure IATA code.
        destination: Arrival IATA code.
        departure_date: Target outbound date.
        return_date: Target return date; None for one-way trips.
        trip_type: ONE_WAY or ROUND_TRIP.
        threshold_pct: Minimum percentage drop required to trigger an alert.
        is_active: Whether this search is currently being monitored.
        created_at: UTC timestamp of creation.
        auto_purchase: If True, trigger purchase automatically on alert confirmation.
    """

    id: UUID
    user_id: UUID
    origin: str
    destination: str
    departure_date: date
    return_date: date | None
    trip_type: TripType
    threshold_pct: float
    is_active: bool
    created_at: datetime
    auto_purchase: bool = False


@dataclass
class PriceHistory:
    """
    A time-series record of scraped prices for a given Search.

    Used to compute the rolling average against which drops are measured.

    Attributes:
        id: Unique identifier (UUID).
        search_id: References the parent Search.
        price: Scraped fare value.
        currency_code: ISO 4217 code.
        scraped_at: UTC timestamp of the observation.
    """

    id: UUID
    search_id: UUID
    price: float
    currency_code: str
    scraped_at: datetime


@dataclass
class Alert:
    """
    A price-drop event detected for a specific Search.

    An Alert is created when a new scrape finds a price that has fallen
    below (historical_avg * (1 - threshold_pct / 100)).

    Attributes:
        id: Unique identifier (UUID).
        search_id: References the triggering Search.
        flight: Full snapshot of the flight that triggered the alert.
        historical_avg: Rolling average price at alert creation time.
        current_price: The price that triggered this alert.
        drop_pct: Actual percentage drop: (historical_avg - current_price) / historical_avg * 100.
        status: Current lifecycle state of the alert.
        triggered_at: UTC timestamp when the alert was created.
        notified_at: UTC timestamp when the notification was sent; None if not yet sent.
    """

    id: UUID
    search_id: UUID
    flight: Flight
    historical_avg: float
    current_price: float
    drop_pct: float
    status: AlertStatus
    triggered_at: datetime
    notified_at: datetime | None = None

    def is_significant(self, threshold_pct: float) -> bool:
        """
        Return True if the price drop meets or exceeds the given threshold.

        Args:
            threshold_pct: Minimum drop percentage to consider significant.

        Returns:
            True when drop_pct >= threshold_pct.
        """
        return self.drop_pct >= threshold_pct
