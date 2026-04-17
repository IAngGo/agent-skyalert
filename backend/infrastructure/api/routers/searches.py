"""
FastAPI router for flight search management endpoints.

POST /searches           — create a new monitored search
GET  /searches/{id}      — get a search by ID
GET  /users/{uid}/searches — list all searches for a user
DELETE /searches/{id}    — deactivate a search
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.application.commands import CreateSearchCommand
from backend.application.exceptions import SearchNotFoundError
from backend.application.use_cases.create_search import CreateSearch
from backend.infrastructure.api.schemas import (
    CreateSearchRequest,
    PriceHistoryPointResponse,
    SearchResponse,
)
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.price_history_repository import PostgresPriceHistoryRepository
from backend.infrastructure.persistence.search_repository import PostgresSearchRepository
from backend.infrastructure.persistence.user_repository import PostgresUserRepository

router = APIRouter(tags=["searches"])


def _get_repos(db: Session = Depends(get_db)) -> tuple[PostgresUserRepository, PostgresSearchRepository]:
    """
    FastAPI dependency that provides both repositories scoped to a session.

    Args:
        db: SQLAlchemy session from get_db().

    Returns:
        Tuple of (UserRepository, SearchRepository).
    """
    return PostgresUserRepository(db), PostgresSearchRepository(db)


@router.post("/searches", response_model=SearchResponse, status_code=201)
def create_search(
    body: CreateSearchRequest,
    db: Session = Depends(get_db),
    repos=Depends(_get_repos),
) -> SearchResponse:
    """
    Create a new flight price monitoring search.

    Args:
        body: Validated request body.
        db: SQLAlchemy session for committing.
        repos: Injected (UserRepository, SearchRepository) tuple.

    Returns:
        The created Search as a SearchResponse.
    """
    users, searches = repos
    use_case = CreateSearch(users=users, searches=searches)
    command = CreateSearchCommand(
        user_id=body.user_id,
        origin=body.origin,
        destination=body.destination,
        departure_date=body.departure_date,
        return_date=body.return_date,
        trip_type=body.trip_type,
        threshold_pct=body.threshold_pct,
        auto_purchase=body.auto_purchase,
    )
    search = use_case.execute(command)
    db.commit()
    return SearchResponse(
        id=search.id,
        user_id=search.user_id,
        origin=search.origin,
        destination=search.destination,
        departure_date=search.departure_date,
        return_date=search.return_date,
        trip_type=search.trip_type,
        threshold_pct=search.threshold_pct,
        is_active=search.is_active,
        created_at=search.created_at,
        auto_purchase=search.auto_purchase,
    )


@router.get("/searches/{search_id}", response_model=SearchResponse)
def get_search(
    search_id: UUID,
    repos=Depends(_get_repos),
) -> SearchResponse:
    """
    Retrieve a search by UUID.

    Args:
        search_id: UUID path parameter.
        repos: Injected repository tuple.

    Returns:
        The Search as a SearchResponse.

    Raises:
        SearchNotFoundError: If no search exists with the given ID (→ 404).
    """
    _, searches = repos
    search = searches.find_by_id(search_id)
    if search is None:
        raise SearchNotFoundError(search_id)
    return SearchResponse(
        id=search.id,
        user_id=search.user_id,
        origin=search.origin,
        destination=search.destination,
        departure_date=search.departure_date,
        return_date=search.return_date,
        trip_type=search.trip_type,
        threshold_pct=search.threshold_pct,
        is_active=search.is_active,
        created_at=search.created_at,
        auto_purchase=search.auto_purchase,
    )


@router.get("/users/{user_id}/searches", response_model=list[SearchResponse])
def list_user_searches(
    user_id: UUID,
    repos=Depends(_get_repos),
) -> list[SearchResponse]:
    """
    List all searches belonging to a user.

    Args:
        user_id: UUID path parameter of the owning user.
        repos: Injected repository tuple.

    Returns:
        List of SearchResponse objects.
    """
    _, searches = repos
    results = searches.find_by_user(user_id)
    return [
        SearchResponse(
            id=s.id,
            user_id=s.user_id,
            origin=s.origin,
            destination=s.destination,
            departure_date=s.departure_date,
            return_date=s.return_date,
            trip_type=s.trip_type,
            threshold_pct=s.threshold_pct,
            is_active=s.is_active,
            created_at=s.created_at,
            auto_purchase=s.auto_purchase,
        )
        for s in results
    ]


@router.get(
    "/searches/{search_id}/price-history",
    response_model=list[PriceHistoryPointResponse],
)
def get_price_history(
    search_id: UUID,
    days: int | None = Query(default=30, ge=1, description="Restrict to last N days. Omit for all-time."),
    db: Session = Depends(get_db),
    repos=Depends(_get_repos),
) -> list[PriceHistoryPointResponse]:
    """
    Return the price time series for a search, ordered oldest → newest.

    Args:
        search_id: UUID path parameter.
        days: If provided, only return observations within the last N days (default 30).
              Pass days=0 or omit to get all-time data.
        db: SQLAlchemy session.
        repos: Injected repository tuple.

    Returns:
        List of price observations suitable for Chart.js.

    Raises:
        SearchNotFoundError: If no search exists with the given ID.
    """
    _, searches = repos
    if searches.find_by_id(search_id) is None:
        raise SearchNotFoundError(search_id)

    since: datetime | None = None
    if days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=days)

    ph_repo = PostgresPriceHistoryRepository(db)
    records = ph_repo.find_by_search(search_id, limit=2000, since=since)
    # find_by_search returns newest-first; reverse for chronological chart order
    records = list(reversed(records))
    return [
        PriceHistoryPointResponse(
            scraped_at=r.scraped_at,
            price=r.price,
            currency_code=r.currency_code,
            airline=r.airline,
        )
        for r in records
    ]


@router.delete("/searches/{search_id}", status_code=204)
def deactivate_search(
    search_id: UUID,
    db: Session = Depends(get_db),
    repos=Depends(_get_repos),
) -> None:
    """
    Deactivate a search (soft delete — sets is_active to False).

    Args:
        search_id: UUID path parameter.
        db: SQLAlchemy session for committing.
        repos: Injected repository tuple.

    Raises:
        SearchNotFoundError: If no search exists with the given ID (→ 404).
    """
    _, searches = repos
    search = searches.find_by_id(search_id)
    if search is None:
        raise SearchNotFoundError(search_id)
    search.is_active = False
    searches.save(search)
    db.commit()
