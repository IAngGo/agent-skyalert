"""
Mapper functions that translate between SQLAlchemy ORM models and domain entities.

These mappers are the only place where infrastructure models touch domain entities.
They are pure functions — stateless, no side effects.

Import direction: mappers import from both models and domain. Nothing else should.
"""

from backend.domain.entities import (
    Alert,
    AlertStatus,
    Flight,
    PriceHistory,
    Search,
    TripType,
    User,
)
from backend.infrastructure.persistence.models import (
    AlertModel,
    PriceHistoryModel,
    SearchModel,
    UserModel,
)


def user_to_domain(model: UserModel) -> User:
    """
    Convert a UserModel ORM instance to a User domain entity.

    Args:
        model: The SQLAlchemy UserModel row.

    Returns:
        A pure User domain entity.
    """
    return User(
        id=model.id,
        email=model.email,
        phone=model.phone,
        whatsapp_enabled=model.whatsapp_enabled,
        created_at=model.created_at,
    )


def user_to_model(entity: User) -> UserModel:
    """
    Convert a User domain entity to a UserModel ORM instance.

    Args:
        entity: The User domain entity.

    Returns:
        A SQLAlchemy UserModel instance (not yet persisted).
    """
    return UserModel(
        id=entity.id,
        email=entity.email,
        phone=entity.phone,
        whatsapp_enabled=entity.whatsapp_enabled,
        created_at=entity.created_at,
    )


def search_to_domain(model: SearchModel) -> Search:
    """
    Convert a SearchModel ORM instance to a Search domain entity.

    Args:
        model: The SQLAlchemy SearchModel row.

    Returns:
        A pure Search domain entity.
    """
    return Search(
        id=model.id,
        user_id=model.user_id,
        origin=model.origin,
        destination=model.destination,
        departure_date=model.departure_date,
        return_date=model.return_date,
        trip_type=TripType(model.trip_type),
        threshold_pct=model.threshold_pct,
        is_active=model.is_active,
        created_at=model.created_at,
        auto_purchase=model.auto_purchase,
    )


def search_to_model(entity: Search) -> SearchModel:
    """
    Convert a Search domain entity to a SearchModel ORM instance.

    Args:
        entity: The Search domain entity.

    Returns:
        A SQLAlchemy SearchModel instance (not yet persisted).
    """
    return SearchModel(
        id=entity.id,
        user_id=entity.user_id,
        origin=entity.origin,
        destination=entity.destination,
        departure_date=entity.departure_date,
        return_date=entity.return_date,
        trip_type=entity.trip_type.value,
        threshold_pct=entity.threshold_pct,
        is_active=entity.is_active,
        created_at=entity.created_at,
        auto_purchase=entity.auto_purchase,
    )


def price_history_to_domain(model: PriceHistoryModel) -> PriceHistory:
    """
    Convert a PriceHistoryModel ORM instance to a PriceHistory domain entity.

    Args:
        model: The SQLAlchemy PriceHistoryModel row.

    Returns:
        A pure PriceHistory domain entity.
    """
    return PriceHistory(
        id=model.id,
        search_id=model.search_id,
        price=model.price,
        currency_code=model.currency_code,
        scraped_at=model.scraped_at,
        airline=model.airline,
    )


def price_history_to_model(entity: PriceHistory) -> PriceHistoryModel:
    """
    Convert a PriceHistory domain entity to a PriceHistoryModel ORM instance.

    Args:
        entity: The PriceHistory domain entity.

    Returns:
        A SQLAlchemy PriceHistoryModel instance (not yet persisted).
    """
    return PriceHistoryModel(
        id=entity.id,
        search_id=entity.search_id,
        price=entity.price,
        currency_code=entity.currency_code,
        scraped_at=entity.scraped_at,
        airline=entity.airline,
    )


def alert_to_domain(model: AlertModel) -> Alert:
    """
    Convert an AlertModel ORM instance to an Alert domain entity.

    The Flight snapshot is reconstructed from the denormalized alert columns.

    Args:
        model: The SQLAlchemy AlertModel row.

    Returns:
        A pure Alert domain entity with an embedded Flight snapshot.
    """
    flight = Flight(
        origin=model.flight_origin,
        destination=model.flight_destination,
        departure_date=model.flight_departure_date,
        return_date=model.flight_return_date,
        price=model.flight_price,
        currency_code=model.flight_currency_code,
        airline=model.flight_airline,
        url=model.flight_url,
        scraped_at=model.flight_scraped_at,
        duration_minutes=model.flight_duration_minutes,
        stops=model.flight_stops,
    )
    return Alert(
        id=model.id,
        search_id=model.search_id,
        flight=flight,
        historical_avg=model.historical_avg,
        current_price=model.current_price,
        drop_pct=model.drop_pct,
        status=AlertStatus(model.status),
        triggered_at=model.triggered_at,
        notified_at=model.notified_at,
    )


def alert_to_model(entity: Alert) -> AlertModel:
    """
    Convert an Alert domain entity to an AlertModel ORM instance.

    The embedded Flight snapshot is flattened into denormalized columns.

    Args:
        entity: The Alert domain entity.

    Returns:
        A SQLAlchemy AlertModel instance (not yet persisted).
    """
    return AlertModel(
        id=entity.id,
        search_id=entity.search_id,
        flight_origin=entity.flight.origin,
        flight_destination=entity.flight.destination,
        flight_departure_date=entity.flight.departure_date,
        flight_return_date=entity.flight.return_date,
        flight_price=entity.flight.price,
        flight_currency_code=entity.flight.currency_code,
        flight_airline=entity.flight.airline,
        flight_url=entity.flight.url,
        flight_scraped_at=entity.flight.scraped_at,
        flight_duration_minutes=entity.flight.duration_minutes,
        flight_stops=entity.flight.stops,
        historical_avg=entity.historical_avg,
        current_price=entity.current_price,
        drop_pct=entity.drop_pct,
        status=entity.status.value,
        triggered_at=entity.triggered_at,
        notified_at=entity.notified_at,
    )
