"""
PostgreSQL implementation of the SearchRepository port.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.entities import Search
from backend.domain.ports import SearchRepository
from backend.infrastructure.persistence.mappers import search_to_domain, search_to_model
from backend.infrastructure.persistence.models import SearchModel


class PostgresSearchRepository(SearchRepository):
    """
    Concrete SearchRepository backed by PostgreSQL via SQLAlchemy.

    Transaction management is the caller's responsibility.
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: An active SQLAlchemy Session.
        """
        self._session = session

    def save(self, search: Search) -> Search:
        """
        Persist a Search entity via upsert (merge by primary key).

        Args:
            search: The Search entity to persist.

        Returns:
            The saved Search entity.
        """
        model = search_to_model(search)
        merged = self._session.merge(model)
        self._session.flush()
        return search_to_domain(merged)

    def find_by_id(self, search_id: UUID) -> Search | None:
        """
        Retrieve a Search by primary key.

        Args:
            search_id: UUID of the target Search.

        Returns:
            The Search entity if found, None otherwise.
        """
        model = self._session.get(SearchModel, search_id)
        return search_to_domain(model) if model else None

    def find_active(self) -> list[Search]:
        """
        Retrieve all active Searches (is_active == True).

        Returns:
            List of active Search entities.
        """
        models = (
            self._session.query(SearchModel)
            .filter(SearchModel.is_active.is_(True))
            .all()
        )
        return [search_to_domain(m) for m in models]

    def find_by_user(self, user_id: UUID) -> list[Search]:
        """
        Retrieve all Searches owned by a given User.

        Args:
            user_id: UUID of the owning User.

        Returns:
            List of Search entities for that user.
        """
        models = (
            self._session.query(SearchModel)
            .filter(SearchModel.user_id == user_id)
            .order_by(SearchModel.created_at.desc())
            .all()
        )
        return [search_to_domain(m) for m in models]
