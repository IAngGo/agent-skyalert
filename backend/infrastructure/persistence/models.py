"""
SQLAlchemy ORM models for SkyAlert.

These models map Python classes to PostgreSQL tables.
They are infrastructure objects — they must never appear in the domain
or application layers. Mappers translate between ORM rows and domain entities.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.infrastructure.persistence.database import Base


class UserModel(Base):
    """ORM model for the users table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    searches: Mapped[list["SearchModel"]] = relationship(
        "SearchModel", back_populates="user", cascade="all, delete-orphan"
    )


class SearchModel(Base):
    """ORM model for the searches table."""

    __tablename__ = "searches"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    trip_type: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auto_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="searches")
    price_history: Mapped[list["PriceHistoryModel"]] = relationship(
        "PriceHistoryModel", back_populates="search", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AlertModel"]] = relationship(
        "AlertModel", back_populates="search", cascade="all, delete-orphan"
    )


class PriceHistoryModel(Base):
    """ORM model for the price_history table."""

    __tablename__ = "price_history"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    search_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("searches.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    airline: Mapped[str] = mapped_column(String(100), nullable=False, default="Unknown")

    search: Mapped["SearchModel"] = relationship("SearchModel", back_populates="price_history")


class AlertModel(Base):
    """ORM model for the alerts table."""

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    search_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("searches.id", ondelete="CASCADE"), nullable=False
    )
    # Flight snapshot fields (denormalized — no FK, this is a point-in-time record)
    flight_origin: Mapped[str] = mapped_column(String(3), nullable=False)
    flight_destination: Mapped[str] = mapped_column(String(3), nullable=False)
    flight_departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    flight_return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    flight_price: Mapped[float] = mapped_column(Float, nullable=False)
    flight_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    flight_airline: Mapped[str] = mapped_column(String(100), nullable=False)
    flight_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    flight_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    flight_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    flight_stops: Mapped[int] = mapped_column(Integer, nullable=False)
    # Alert fields
    historical_avg: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    drop_pct: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    search: Mapped["SearchModel"] = relationship("SearchModel", back_populates="alerts")
