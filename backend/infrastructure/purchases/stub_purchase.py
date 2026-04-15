"""
Stub implementation of PurchaseService.

Satisfies the port until a real purchase integration is built.
Logs the attempt and always returns False to indicate no purchase was made.
"""

import logging

from backend.domain.entities import Flight, User
from backend.domain.ports import PurchaseService

logger = logging.getLogger(__name__)


class StubPurchaseService(PurchaseService):
    """
    No-op PurchaseService used until a real purchase adapter is implemented.

    Returns False so callers know purchase was not completed.
    """

    def purchase(self, user: User, flight: Flight) -> bool:
        """
        Log the purchase attempt and return False.

        Args:
            user: The User requesting the purchase.
            flight: The Flight snapshot to purchase.

        Returns:
            Always False — this is a stub.
        """
        logger.warning(
            "StubPurchaseService: purchase requested for user %s on flight %s → %s "
            "(not implemented). URL: %s",
            user.id,
            flight.origin,
            flight.destination,
            flight.url,
        )
        return False
