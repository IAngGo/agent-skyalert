"""add source to price_history

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-13

Adds a `source` column to price_history identifying which scraper
produced each observation (e.g. "google_flights", "kayak"), now that
SkyAlert aggregates prices from multiple sites via CompositeFlightScraper.
Column is nullable on creation to support existing rows; a default of
'google_flights' is applied for any row without a value.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source column to price_history."""
    op.add_column(
        "price_history",
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=True,
        ),
    )
    # Backfill existing rows — all prior observations came from Google Flights.
    op.execute("UPDATE price_history SET source = 'google_flights' WHERE source IS NULL")
    # Make non-nullable now that all rows have a value
    op.alter_column("price_history", "source", nullable=False)


def downgrade() -> None:
    """Remove source column from price_history."""
    op.drop_column("price_history", "source")
