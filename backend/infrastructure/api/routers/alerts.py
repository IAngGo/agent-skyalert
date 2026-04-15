"""
FastAPI router for alert endpoints.

GET  /searches/{id}/alerts     — list alerts for a search
GET  /alerts/{id}              — get a single alert
POST /alerts/{id}/confirm      — confirm alert and optionally trigger purchase
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.application.commands import ConfirmAlertCommand
from backend.application.exceptions import AlertNotFoundError
from backend.application.use_cases.confirm_alert import ConfirmAlert
from backend.domain.entities import Flight
from backend.infrastructure.api.schemas import (
    AlertResponse,
    ConfirmAlertRequest,
    FlightSnapshot,
)
from backend.infrastructure.persistence.alert_repository import PostgresAlertRepository
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.search_repository import PostgresSearchRepository
from backend.infrastructure.persistence.user_repository import PostgresUserRepository
from backend.infrastructure.scraper.google_flights import GoogleFlightsScraper
from backend.infrastructure.notifications.composite_service import CompositeNotificationService
from backend.infrastructure.notifications.sendgrid_service import SendGridNotificationService
from backend.infrastructure.notifications.twilio_service import TwilioWhatsAppService
from backend.infrastructure.tasks.scrape_tasks import scrape_search

router = APIRouter(tags=["alerts"])


def _flight_to_schema(flight: Flight) -> FlightSnapshot:
    """
    Convert a Flight domain entity to a FlightSnapshot schema.

    Args:
        flight: The Flight entity.

    Returns:
        A FlightSnapshot Pydantic model.
    """
    return FlightSnapshot(
        origin=flight.origin,
        destination=flight.destination,
        departure_date=flight.departure_date,
        return_date=flight.return_date,
        price=flight.price,
        currency_code=flight.currency_code,
        airline=flight.airline,
        url=flight.url,
        duration_minutes=flight.duration_minutes,
        stops=flight.stops,
    )


@router.get("/searches/{search_id}/alerts", response_model=list[AlertResponse])
def list_search_alerts(
    search_id: UUID,
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    """
    List all alerts triggered for a given search.

    Args:
        search_id: UUID path parameter of the parent Search.
        db: SQLAlchemy session.

    Returns:
        List of AlertResponse objects, most recent first.
    """
    repo = PostgresAlertRepository(db)
    alerts = repo.find_by_search(search_id)
    return [
        AlertResponse(
            id=a.id,
            search_id=a.search_id,
            flight=_flight_to_schema(a.flight),
            historical_avg=a.historical_avg,
            current_price=a.current_price,
            drop_pct=a.drop_pct,
            status=a.status,
            triggered_at=a.triggered_at,
            notified_at=a.notified_at,
        )
        for a in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """
    Retrieve a single alert by UUID.

    Args:
        alert_id: UUID path parameter.
        db: SQLAlchemy session.

    Returns:
        The Alert as an AlertResponse.

    Raises:
        AlertNotFoundError: If no alert exists with the given ID (→ 404).
    """
    repo = PostgresAlertRepository(db)
    alert = repo.find_by_id(alert_id)
    if alert is None:
        raise AlertNotFoundError(alert_id)
    return AlertResponse(
        id=alert.id,
        search_id=alert.search_id,
        flight=_flight_to_schema(alert.flight),
        historical_avg=alert.historical_avg,
        current_price=alert.current_price,
        drop_pct=alert.drop_pct,
        status=alert.status,
        triggered_at=alert.triggered_at,
        notified_at=alert.notified_at,
    )


@router.post("/alerts/{alert_id}/confirm", response_model=AlertResponse)
def confirm_alert(
    alert_id: UUID,
    body: ConfirmAlertRequest,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """
    Confirm a price-drop alert and optionally trigger automatic purchase.

    Args:
        alert_id: UUID path parameter of the Alert to confirm.
        body: Contains user_id and trigger_purchase flag.
        db: SQLAlchemy session.

    Returns:
        The updated Alert as an AlertResponse.

    Raises:
        AlertNotFoundError: If no alert exists with the given ID (→ 404).
        ValueError: If alert is not in SENT status or user does not own it (→ 422).
    """
    from backend.infrastructure.purchases.stub_purchase import StubPurchaseService

    alerts = PostgresAlertRepository(db)
    searches = PostgresSearchRepository(db)
    users = PostgresUserRepository(db)
    purchase = StubPurchaseService()

    use_case = ConfirmAlert(
        alerts=alerts,
        searches=searches,
        users=users,
        purchase=purchase,
    )
    command = ConfirmAlertCommand(
        alert_id=alert_id,
        user_id=body.user_id,
        trigger_purchase=body.trigger_purchase,
    )
    alert = use_case.execute(command)
    db.commit()
    return AlertResponse(
        id=alert.id,
        search_id=alert.search_id,
        flight=_flight_to_schema(alert.flight),
        historical_avg=alert.historical_avg,
        current_price=alert.current_price,
        drop_pct=alert.drop_pct,
        status=alert.status,
        triggered_at=alert.triggered_at,
        notified_at=alert.notified_at,
    )
