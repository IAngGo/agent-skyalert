"""
PostgreSQL implementation of the UserRepository port.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.entities import User
from backend.domain.ports import UserRepository
from backend.infrastructure.persistence.mappers import user_to_domain, user_to_model
from backend.infrastructure.persistence.models import UserModel


class PostgresUserRepository(UserRepository):
    """
    Concrete UserRepository backed by PostgreSQL via SQLAlchemy.

    Each method receives a pre-scoped Session from the caller (use case or
    FastAPI dependency). This class never creates or commits sessions itself —
    transaction management is the caller's responsibility.
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: An active SQLAlchemy Session.
        """
        self._session = session

    def save(self, user: User) -> User:
        """
        Persist a User entity via upsert (merge by primary key).

        Args:
            user: The User entity to persist.

        Returns:
            The saved User entity.
        """
        model = user_to_model(user)
        merged = self._session.merge(model)
        self._session.flush()
        return user_to_domain(merged)

    def find_by_id(self, user_id: UUID) -> User | None:
        """
        Retrieve a User by primary key.

        Args:
            user_id: UUID of the target User.

        Returns:
            The User entity if found, None otherwise.
        """
        model = self._session.get(UserModel, user_id)
        return user_to_domain(model) if model else None

    def find_by_email(self, email: str) -> User | None:
        """
        Retrieve a User by email address.

        Args:
            email: The email to look up.

        Returns:
            The User entity if found, None otherwise.
        """
        model = (
            self._session.query(UserModel)
            .filter(UserModel.email == email)
            .first()
        )
        return user_to_domain(model) if model else None
