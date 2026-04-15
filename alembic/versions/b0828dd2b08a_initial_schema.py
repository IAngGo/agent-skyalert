"""initial schema

Revision ID: b0828dd2b08a
Revises:
Create Date: 2026-04-14

Creates the four core tables: users, searches, price_history, alerts.
Written manually to match backend.infrastructure.persistence.models exactly.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b0828dd2b08a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all SkyAlert tables."""

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ------------------------------------------------------------------
    # searches
    # ------------------------------------------------------------------
    op.create_table(
        "searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("origin", sa.String(3), nullable=False),
        sa.Column("destination", sa.String(3), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("trip_type", sa.String(20), nullable=False),
        sa.Column("threshold_pct", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auto_purchase", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_searches_user_id", "searches", ["user_id"])
    op.create_index("ix_searches_is_active", "searches", ["is_active"])

    # ------------------------------------------------------------------
    # price_history
    # ------------------------------------------------------------------
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_price_history_search_id", "price_history", ["search_id"])
    op.create_index("ix_price_history_scraped_at", "price_history", ["scraped_at"])

    # ------------------------------------------------------------------
    # alerts
    # ------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Flight snapshot (denormalized)
        sa.Column("flight_origin", sa.String(3), nullable=False),
        sa.Column("flight_destination", sa.String(3), nullable=False),
        sa.Column("flight_departure_date", sa.Date(), nullable=False),
        sa.Column("flight_return_date", sa.Date(), nullable=True),
        sa.Column("flight_price", sa.Float(), nullable=False),
        sa.Column("flight_currency_code", sa.String(3), nullable=False),
        sa.Column("flight_airline", sa.String(100), nullable=False),
        sa.Column("flight_url", sa.String(2048), nullable=False),
        sa.Column("flight_scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("flight_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("flight_stops", sa.Integer(), nullable=False),
        # Alert fields
        sa.Column("historical_avg", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=False),
        sa.Column("drop_pct", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerts_search_id", "alerts", ["search_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])


def downgrade() -> None:
    """Drop all SkyAlert tables in reverse dependency order."""
    op.drop_table("alerts")
    op.drop_table("price_history")
    op.drop_table("searches")
    op.drop_table("users")
