"""
Unit tests for the CreateSearch use case.

Business rules under test:
1. Happy path — valid input creates and persists a Search.
2. User does not exist → UserNotFoundError.
3. threshold_pct out of range → InvalidThresholdError.
4. return_date not after departure_date → ValueError.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from backend.application.commands import CreateSearchCommand
from backend.application.exceptions import InvalidThresholdError, UserNotFoundError
from backend.application.use_cases.create_search import CreateSearch
from backend.domain.entities import TripType
from tests.fakes import InMemorySearchRepository, InMemoryUserRepository


def make_use_case(
    users: InMemoryUserRepository,
    searches: InMemorySearchRepository,
) -> CreateSearch:
    """Construct CreateSearch with the given fakes."""
    return CreateSearch(users=users, searches=searches)


class TestCreateSearch:
    """Tests for CreateSearch.execute()."""

    def test_happy_path_creates_and_persists_search(
        self,
        users: InMemoryUserRepository,
        searches: InMemorySearchRepository,
        sample_user,
    ) -> None:
        """A valid command creates a Search stored in the repository."""
        use_case = make_use_case(users, searches)
        cmd = CreateSearchCommand(
            user_id=sample_user.id,
            origin="jfk",          # intentionally lowercase — use case should uppercase
            destination="lhr",
            departure_date=date(2026, 7, 1),
            return_date=date(2026, 7, 15),
            trip_type=TripType.ROUND_TRIP,
            threshold_pct=10.0,
        )

        result = use_case.execute(cmd)

        assert result.origin == "JFK"
        assert result.destination == "LHR"
        assert result.is_active is True
        assert result.user_id == sample_user.id
        # Verify it was actually saved
        assert searches.find_by_id(result.id) is not None

    def test_raises_when_user_not_found(
        self,
        users: InMemoryUserRepository,
        searches: InMemorySearchRepository,
    ) -> None:
        """A user_id that does not exist raises UserNotFoundError."""
        use_case = make_use_case(users, searches)
        cmd = CreateSearchCommand(
            user_id=uuid4(),  # nobody with this id
            origin="JFK",
            destination="LHR",
            departure_date=date(2026, 7, 1),
            return_date=None,
            trip_type=TripType.ONE_WAY,
            threshold_pct=10.0,
        )

        with pytest.raises(UserNotFoundError):
            use_case.execute(cmd)

    @pytest.mark.parametrize("threshold", [0.0, 100.0, -5.0, 150.0])
    def test_raises_on_invalid_threshold(
        self,
        users: InMemoryUserRepository,
        searches: InMemorySearchRepository,
        sample_user,
        threshold: float,
    ) -> None:
        """threshold_pct must be strictly between 0 and 100."""
        use_case = make_use_case(users, searches)
        cmd = CreateSearchCommand(
            user_id=sample_user.id,
            origin="JFK",
            destination="LHR",
            departure_date=date(2026, 7, 1),
            return_date=None,
            trip_type=TripType.ONE_WAY,
            threshold_pct=threshold,
        )

        with pytest.raises(InvalidThresholdError):
            use_case.execute(cmd)

    def test_raises_when_return_date_not_after_departure(
        self,
        users: InMemoryUserRepository,
        searches: InMemorySearchRepository,
        sample_user,
    ) -> None:
        """return_date equal to or before departure_date must raise ValueError."""
        use_case = make_use_case(users, searches)
        cmd = CreateSearchCommand(
            user_id=sample_user.id,
            origin="JFK",
            destination="LHR",
            departure_date=date(2026, 7, 15),
            return_date=date(2026, 7, 1),  # before departure
            trip_type=TripType.ROUND_TRIP,
            threshold_pct=10.0,
        )

        with pytest.raises(ValueError):
            use_case.execute(cmd)
