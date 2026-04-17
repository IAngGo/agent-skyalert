"""add airline to price_history

Revision ID: c3d4e5f6a7b8
Revises: b0828dd2b08a
Create Date: 2026-04-17

Adds an `airline` column to price_history so that price time series
can be broken down by carrier in the dashboard chart.
Column is nullable on creation to support existing rows; a default
of 'Unknown' is applied for any row without a value.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b0828dd2b08a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add airline column to price_history."""
    op.add_column(
        "price_history",
        sa.Column(
            "airline",
            sa.String(length=100),
            nullable=True,
        ),
    )
    # Backfill existing rows
    op.execute("UPDATE price_history SET airline = 'Unknown' WHERE airline IS NULL")
    # Make non-nullable now that all rows have a value
    op.alter_column("price_history", "airline", nullable=False)


def downgrade() -> None:
    """Remove airline column from price_history."""
    op.drop_column("price_history", "airline")
