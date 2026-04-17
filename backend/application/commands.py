"""
Command objects for SkyAlert use cases.

A command is a plain dataclass that carries validated input into a use case's
execute() method. Commands are transport-agnostic — they contain no HTTP,
ORM, or framework references.

One command per use case. Fields use primitive types or domain enums only.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from backend.domain.entities import TripType


@dataclass(frozen=True)
class CreateUserCommand:
    """
    Input required to register a new SkyAlert user.

    Attributes:
        email: Valid email address for SendGrid notifications.
        phone: E.164-formatted phone number for Twilio WhatsApp.
        whatsapp_enabled: Whether the user opts into WhatsApp alerts.
    """

    email: str
    phone: str
    whatsapp_enabled: bool


@dataclass(frozen=True)
class CreateSearchCommand:
    """
    Input required to create a new flight price monitoring search.

    Attributes:
        user_id: UUID of the owning User.
        origin: Departure IATA airport code (e.g. "JFK").
        destination: Arrival IATA airport code (e.g. "LHR").
        departure_date: Outbound travel date.
        return_date: Return date; None for one-way trips.
        trip_type: ONE_WAY or ROUND_TRIP.
        threshold_pct: Minimum price drop percentage to trigger an alert.
        auto_purchase: Whether to trigger purchase automatically on confirmation.
    """

    user_id: UUID
    origin: str
    destination: str
    departure_date: date
    return_date: date | None
    trip_type: TripType
    threshold_pct: float
    auto_purchase: bool = False


@dataclass(frozen=True)
class RunPriceScrapeCommand:
    """
    Input required to run a price scrape for a specific Search.

    Attributes:
        search_id: UUID of the Search to scrape.
    """

    search_id: UUID


@dataclass(frozen=True)
class EvaluatePriceDropCommand:
    """
    Input required to evaluate whether a scraped price constitutes an alert.

    Attributes:
        search_id: UUID of the Search being evaluated.
        current_price: Most recently scraped price.
        currency_code: ISO 4217 currency code for the scraped price.
        history_window_days: How many days of history to include in the average.
    """

    search_id: UUID
    current_price: float
    currency_code: str
    history_window_days: int = 7


@dataclass(frozen=True)
class SendAlertNotificationCommand:
    """
    Input required to dispatch a notification for a triggered Alert.

    Attributes:
        alert_id: UUID of the Alert to notify about.
    """

    alert_id: UUID


@dataclass(frozen=True)
class RequestMagicLinkCommand:
    """
    Input required to request a magic-link login email.

    Attributes:
        email: The user's email address.
        base_url: Frontend base URL used to construct the verify link (e.g. "http://localhost:8000").
    """

    email: str
    base_url: str


@dataclass(frozen=True)
class VerifyMagicLinkCommand:
    """
    Input required to verify a magic-link token.

    Attributes:
        token: The signed JWT from the magic-link URL.
    """

    token: str


@dataclass(frozen=True)
class ConfirmAlertCommand:
    """
    Input required when a user acknowledges an alert (optionally triggering purchase).

    Attributes:
        alert_id: UUID of the Alert being confirmed.
        user_id: UUID of the User confirming the alert.
        trigger_purchase: Whether to initiate automatic purchase on confirmation.
    """

    alert_id: UUID
    user_id: UUID
    trigger_purchase: bool = False
