"""
Pydantic request and response schemas for the SkyAlert API.

Schemas live at the transport boundary — they validate HTTP input and
serialize domain entities to JSON. They are never passed into use cases;
use cases receive Command objects instead.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.domain.entities import AlertStatus, TripType


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    """Request body for POST /users."""

    email: EmailStr
    phone: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$", description="E.164 format, e.g. +12125551234")
    whatsapp_enabled: bool = False


class UserResponse(BaseModel):
    """Response body for user endpoints."""

    id: UUID
    email: str
    phone: str
    whatsapp_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Search schemas
# ---------------------------------------------------------------------------


class CreateSearchRequest(BaseModel):
    """Request body for POST /searches."""

    origin: str = Field(..., min_length=3, max_length=3, description="IATA code, e.g. JFK")
    destination: str = Field(..., min_length=3, max_length=3, description="IATA code, e.g. LHR")
    departure_date: date
    return_date: date | None = None
    trip_type: TripType
    threshold_pct: float = Field(..., gt=0, lt=100, description="Alert threshold percentage")
    auto_purchase: bool = False

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        """Normalize IATA codes to uppercase."""
        return v.upper().strip()


class SearchResponse(BaseModel):
    """Response body for search endpoints."""

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
    auto_purchase: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Alert schemas
# ---------------------------------------------------------------------------


class FlightSnapshot(BaseModel):
    """Embedded flight data within an AlertResponse."""

    origin: str
    destination: str
    departure_date: date
    return_date: date | None
    price: float
    currency_code: str
    airline: str
    url: str
    duration_minutes: int
    stops: int


class AlertResponse(BaseModel):
    """Response body for alert endpoints."""

    id: UUID
    search_id: UUID
    flight: FlightSnapshot
    historical_avg: float
    current_price: float
    drop_pct: float
    status: AlertStatus
    triggered_at: datetime
    notified_at: datetime | None

    model_config = {"from_attributes": True}


class ConfirmAlertRequest(BaseModel):
    """Request body for POST /alerts/{alert_id}/confirm."""

    trigger_purchase: bool = False


# ---------------------------------------------------------------------------
# Price history schemas
# ---------------------------------------------------------------------------


class PriceHistoryPointResponse(BaseModel):
    """One price observation for the time-series chart."""

    scraped_at: datetime
    price: float
    currency_code: str
    airline: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic response schemas
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error envelope returned on 4xx/5xx responses."""

    detail: str
