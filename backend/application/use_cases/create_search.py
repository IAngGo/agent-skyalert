"""
Use case: Create a new flight price monitoring search.

Triggered when a user submits the search form on the frontend.
Validates business rules, then persists the Search entity.
"""

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.commands import CreateSearchCommand
from backend.application.exceptions import (
    InvalidThresholdError,
    UserNotFoundError,
)
from backend.domain.entities import Search
from backend.domain.ports import SearchRepository, UserRepository


class CreateSearch:
    """
    Create and persist a new Search for a verified user.

    Business rules enforced:
    - The user must exist.
    - threshold_pct must be strictly between 0 and 100.
    - For round trips, return_date must be after departure_date.
    """

    def __init__(
        self,
        users: UserRepository,
        searches: SearchRepository,
    ) -> None:
        """
        Args:
            users: Port for retrieving User entities.
            searches: Port for persisting Search entities.
        """
        self._users = users
        self._searches = searches

    def execute(self, command: CreateSearchCommand) -> Search:
        """
        Validate and persist a new Search.

        Args:
            command: Validated input data for the new Search.

        Returns:
            The persisted Search entity.

        Raises:
            UserNotFoundError: If no User exists with command.user_id.
            InvalidThresholdError: If threshold_pct is not in (0, 100).
            ValueError: If return_date is not after departure_date for round trips.
        """
        user = self._users.find_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError(command.user_id)

        if not (0 < command.threshold_pct < 100):
            raise InvalidThresholdError(command.threshold_pct)

        if command.return_date is not None:
            if command.return_date <= command.departure_date:
                raise ValueError(
                    f"return_date ({command.return_date}) must be after "
                    f"departure_date ({command.departure_date})."
                )

        search = Search(
            id=uuid4(),
            user_id=command.user_id,
            origin=command.origin.upper().strip(),
            destination=command.destination.upper().strip(),
            departure_date=command.departure_date,
            return_date=command.return_date,
            trip_type=command.trip_type,
            threshold_pct=command.threshold_pct,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            auto_purchase=command.auto_purchase,
        )

        return self._searches.save(search)
